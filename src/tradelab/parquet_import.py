"""`tradelab import-parquet`: read 1-minute candle files that already are .parquet.

Two kinds of file are understood, told apart by the time column:
- times without a time zone: a US stock (HF Data Library), New York wall-clock time, 09:30 to 16:00
- times in UTC: a forex or CFD quote file; the four HistData markets (XAUUSD, ...) go to their own market
The market name is the file name up to the first underscore: `AAPL_clean_1min.parquet` is AAPL.
"""

import re
from pathlib import Path

import pandas as pd

from .histdata import SYMBOLS
from .markets import HISTDATA, MARKETS, Market, save_market, set_source, source_of
from .store import BASES, COLUMNS, load_base, resample, save_candles

NEW_YORK = "America/New_York"
STOCK_NOTE = (
    "US stock candles from the HF Data Library: trades on the IEX exchange only, regular hours "
    "(09:30 to 16:00 New York). Volume is only the IEX part of all trading and minutes without "
    "trades are missing. Adjusted for stock splits, not for dividends. The data terms allow academic "
    "and educational research only, not trading with real money. Source: HF Data Library "
    "(Ahmed Elkassabgi). Data provided for free by IEX.")
FOREX_NOTE = "Forex or CFD quotes from files, not exchange prices. No volume (always 0). Source: HistData.com."


def read(path: Path) -> tuple[pd.DataFrame, bool]:
    """The candles in tradelab form (UTC index `time`) and whether the file holds a US stock."""
    try:
        df = pd.read_parquet(path)
        df.columns = df.columns.str.lower()
        times = pd.DatetimeIndex(df.pop("datetime" if "datetime" in df else "time"), name="time")
        stock = times.tz is None
        if stock:
            times = times.tz_localize(NEW_YORK).tz_convert("UTC")
        df = df[COLUMNS].astype(float)
    except (KeyError, ValueError, TypeError, OSError) as error:
        raise ValueError(f"Cannot read {path.name} as a candle file ({type(error).__name__}).") from None
    df.index = times
    if df.empty or df.isna().any().any() or (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError(f"Cannot read {path.name}: empty, incomplete or bad prices.")
    return df[~df.index.duplicated(keep="last")].sort_index(), stock


def market_for(path: Path, stock: bool) -> Market:
    name = path.name.split("_")[0].upper()
    if not re.fullmatch(r"[A-Z0-9-]+", name):
        raise ValueError(f"Skipped {path.name}: no market name in front of the first underscore.")
    if not stock and name in SYMBOLS:
        key = SYMBOLS[name]
        if source_of(key) != "histdata" and any(not load_base(key, base).empty for base in BASES):
            raise ValueError(f"Skipped {path.name}: {key} holds Twelve Data candles. "
                             "Run 'tradelab import --replace' with HistData files to switch.")
        return HISTDATA[key]
    if stock:
        # a ticker can equal a built-in market name (GOLD is a stock too)
        key = f"{name}-US" if name in MARKETS else name
        return Market(key, name, f"{name} (US stock)", NEW_YORK, "09:30", STOCK_NOTE, "parquet")
    # the forex trading day starts at 17:00 New York, when the week opens on Sunday
    return Market(name, name, f"{name} (forex or CFD quotes)", NEW_YORK, "17:00", FOREX_NOTE, "parquet")


def import_parquet_folder(folder: str | Path, log=print) -> dict[str, int]:
    """Import every .parquet file under `folder`. Returns the number of candles per market.

    Files are big and independent, so a file that cannot be read is skipped and reported while
    the rest goes on. Run it again to merge newer files: stored minutes are never duplicated.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a folder.")
    paths = sorted(folder.rglob("*.parquet"))
    if not paths:
        raise ValueError(f"No .parquet files in {folder}.")

    counts, skipped = {}, 0
    for path in paths:
        try:
            minutes, stock = read(path)
            market = market_for(path, stock)
        except ValueError as error:
            log(str(error))
            skipped += 1
            continue
        save_candles(market.key, "1min", minutes)
        if market.source == "parquet":
            save_market(market)
        else:
            set_source(market.key, "histdata")
        # every other candle size is built from 5min, so 5min is rebuilt from all stored minutes
        save_candles(market.key, "5min", resample(load_base(market.key, "1min"), 5, market.timezone, market.session_start))
        counts[market.key] = len(minutes)
        log(f"{market.key}: {len(minutes)} one-minute candles, {minutes.index[0]:%Y-%m-%d} to {minutes.index[-1]:%Y-%m-%d}")
    log(f"Done: {len(counts)} markets imported, {skipped} files skipped.")
    return counts

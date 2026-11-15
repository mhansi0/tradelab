import os
from datetime import datetime

import numpy as np
import pandas as pd

from .markets import MARKETS, TIMEFRAMES, get_market, session_keys
from .paths import data_file

COLUMNS = ["open", "high", "low", "close", "volume"]
BASES = ("1min", "5min")  # downloaded as-is; every other timeframe is built from 5min


class DataMissingError(Exception):
    pass


def load_base(market: str, base: str) -> pd.DataFrame:
    path = data_file(market, base)
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame(
        columns=COLUMNS, index=pd.DatetimeIndex([], tz="UTC", name="time"), dtype=float)


def save_candles(market: str, base: str, df: pd.DataFrame) -> None:
    existing = load_base(market, base)
    merged = df[COLUMNS] if existing.empty else pd.concat([existing, df[COLUMNS]])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index().astype(float)
    merged.index.name = "time"
    path = data_file(market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    # write next to the file, then swap: an interrupted download never corrupts stored data
    tmp = path.with_suffix(".tmp")
    merged.to_parquet(tmp)
    os.replace(tmp, path)


def resample(df: pd.DataFrame, minutes: int, timezone: str, session_start: str) -> pd.DataFrame:
    """Build bigger candles. Blocks start at the session start; the last block of a day may be short."""
    keys = session_keys(df.index, timezone, session_start)
    grouped = df.groupby([keys["session"].to_numpy(), (keys["minute"] // minutes).to_numpy()])
    out = grouped.agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"))
    hours, mins = map(int, session_start.split(":"))
    sessions, blocks = out.index.get_level_values(0), out.index.get_level_values(1)
    local = pd.to_datetime(sessions) + pd.to_timedelta(hours * 60 + mins + blocks * minutes, unit="min")
    out.index = (
        pd.DatetimeIndex(local)
        .tz_localize(timezone, ambiguous=np.ones(len(local), dtype=bool), nonexistent="shift_forward")
        .tz_convert("UTC")
        .rename("time"))
    return out.sort_index()


def load_candles(
    market: str,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
    timezone: str | None = None,
    session_start: str | None = None,
) -> pd.DataFrame:
    """Candles for a timeframe, `start` inclusive and `end` exclusive."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unknown timeframe {timeframe!r}. Valid timeframes: {', '.join(TIMEFRAMES)}")
    m = get_market(market)
    df = load_base(market, "1min" if timeframe == "1min" else "5min")
    if df.empty:
        raise DataMissingError(f"No data for {market}. Run: uv run tradelab download")
    if timeframe not in BASES:
        df = resample(df, TIMEFRAMES[timeframe], timezone or m.timezone, session_start or m.session_start)
    if start is not None:
        df = df[df.index >= start]
    if end is not None:
        df = df[df.index < end]
    return df


def status(markets=None) -> list[dict]:
    """What is stored per market (default: the four built in). Reads only the time column."""
    rows = []
    for market in markets or MARKETS:
        for base in BASES:
            path = data_file(market, base)
            index = pd.read_parquet(path, columns=[]).index if path.exists() else []
            if len(index):
                rows.append({
                    "market": market, "base": base, "rows": len(index),
                    "first": index[0].isoformat(), "last": index[-1].isoformat()})
    return rows

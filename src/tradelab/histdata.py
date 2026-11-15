"""`tradelab import`: read 1-minute files downloaded by hand from HistData.com.

File format (their "Generic ASCII" M1): no header, semicolons,
`20120201 000000;open;high;low;close;volume`, times in EST without daylight saving.
"""

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from .markets import HISTDATA, set_source, source_of
from .paths import data_file
from .store import BASES, COLUMNS, load_base, resample, save_candles

SYMBOLS = {market.symbol: key for key, market in HISTDATA.items()}
NAME = re.compile(r"_([A-Z]{6})_M1_?\d{4,6}", re.IGNORECASE)
EST_TO_UTC = pd.Timedelta(hours=5)
MAX_FILE_BYTES = 300_000_000  # a year of minutes is about 25 MB; anything far larger is not theirs


def parse(text: str, name: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.StringIO(text), sep=";", header=None, names=["time", *COLUMNS],
                         dtype={"time": str})
        times = pd.to_datetime(df.pop("time"), format="%Y%m%d %H%M%S") + EST_TO_UTC
        df = df.astype(float)
        df.index = pd.DatetimeIndex(times, name="time").tz_localize("UTC")
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"Cannot read {name} as a HistData 1-minute file ({type(error).__name__}).") from None
    if df.empty or df.isna().any().any() or (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError(f"Cannot read {name} as a HistData 1-minute file: empty, incomplete or bad prices.")
    return df[~df.index.duplicated(keep="last")].sort_index()


def _read(path: Path) -> str:
    if path.suffix.lower() != ".zip":
        return path.read_text(encoding="utf-8", errors="replace")
    try:
        with zipfile.ZipFile(path) as archive:
            member = next((m for m in archive.infolist() if m.filename.lower().endswith(".csv")), None)
            if member is None or member.file_size > MAX_FILE_BYTES:
                raise ValueError(f"Cannot read {path.name}: no .csv inside, or it is far too large.")
            return archive.read(member).decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        raise ValueError(f"Cannot read {path.name}: it is not a zip file.") from None


def import_folder(folder: str | Path, replace: bool = False, log=print) -> dict[str, int]:
    """Import every HistData file in `folder`. Returns the number of imported candles per market."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a folder.")

    files: dict[str, list[Path]] = {}
    for path in sorted(folder.iterdir()):
        match = NAME.search(path.name) if path.suffix.lower() in (".zip", ".csv") else None
        if not match:
            continue
        symbol = match.group(1).upper()
        if symbol in SYMBOLS:
            files.setdefault(SYMBOLS[symbol], []).append(path)
        else:
            log(f"Skipped {path.name}: {symbol} is not one of {', '.join(SYMBOLS)}.")
    if not files:
        raise ValueError(
            f"No HistData files for {', '.join(SYMBOLS)} in {folder}. "
            "Expected names like HISTDATA_COM_ASCII_XAUUSD_M1_2024.zip")

    stored_elsewhere = [
        key for key in files
        if source_of(key) != "histdata" and any(not load_base(key, base).empty for base in BASES)]
    if stored_elsewhere and not replace:
        raise ValueError(
            f"{', '.join(stored_elsewhere)} already holds candles from Twelve Data. Prices of the two "
            "sources differ, so they cannot be mixed. Run again with --replace to delete those "
            "candles and use the HistData files instead.")

    # read everything first: a broken file stops the import before anything is stored
    parsed = {key: pd.concat([parse(_read(path), path.name) for path in paths])
              for key, paths in files.items()}

    counts = {}
    for key, minutes in parsed.items():
        minutes = minutes[~minutes.index.duplicated(keep="last")].sort_index()
        if source_of(key) != "histdata":
            for base in BASES:
                data_file(key, base).unlink(missing_ok=True)
        save_candles(key, "1min", minutes)
        set_source(key, "histdata")
        market = HISTDATA[key]
        # every other candle size is built from 5min, so 5min is rebuilt from all stored minutes
        save_candles(key, "5min", resample(load_base(key, "1min"), 5, market.timezone, market.session_start))
        counts[key] = len(minutes)
        log(f"{key}: {len(minutes)} one-minute candles imported, "
            f"{minutes.index[0]:%Y-%m-%d} to {minutes.index[-1]:%Y-%m-%d}")
    return counts

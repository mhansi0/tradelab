import json
import re
from dataclasses import asdict, dataclass

import pandas as pd

from .paths import data_file, home


@dataclass(frozen=True)
class Market:
    key: str
    symbol: str
    label: str
    timezone: str
    session_start: str
    note: str = ""
    source: str = "twelvedata"


# the definitions for candles downloaded from Twelve Data, and the default
MARKETS: dict[str, Market] = {
    m.key: m
    for m in (
        Market("SP500", "SPY", "S&P 500 (via the SPY fund)", "America/New_York", "09:30"),
        Market("NAS100", "QQQ", "Nasdaq 100 (via the QQQ fund)", "America/New_York", "09:30"),
        # metals reopen at 18:00 New York after the daily break; a midnight-UTC day would make
        # every Sunday evening a one-candle "day"
        Market("GOLD", "XAU/USD", "Gold (spot)", "America/New_York", "18:00"),
        Market(
            "SILVER", "SLV", "Silver (via the SLV fund)", "America/New_York", "09:30",
            "Proxy: SLV silver fund, US market hours only. Spot silver needs a paid data plan.",
        ),
    )
}

# timeframe name -> minutes
TIMEFRAMES: dict[str, int] = {
    "1min": 1, "5min": 5, "15min": 15, "30min": 30, "1h": 60, "4h": 240, "1day": 1440}


_HISTDATA_NOTE = "Prices from HistData.com files: bid quotes of one provider, no volume."
_INDEX_NOTE = _HISTDATA_NOTE + " This index price trades almost around the clock, unlike the fund."

# the definitions for candles imported from HistData.com files
HISTDATA: dict[str, Market] = {
    m.key: m
    for m in (
        Market("SP500", "SPXUSD", "S&P 500 (SPX/USD index price)", "America/New_York", "09:30",
               _INDEX_NOTE, "histdata"),
        Market("NAS100", "NSXUSD", "Nasdaq 100 (NSX/USD index price)", "America/New_York", "09:30",
               _INDEX_NOTE, "histdata"),
        Market("GOLD", "XAUUSD", "Gold (spot)", "America/New_York", "18:00", _HISTDATA_NOTE, "histdata"),
        Market("SILVER", "XAGUSD", "Silver (spot)", "America/New_York", "18:00", _HISTDATA_NOTE, "histdata"),
    )
}


def _source_file(key: str):
    return data_file(key, "source").with_suffix(".txt")


def source_of(key: str) -> str:
    """Where a market's stored candles came from. One source per market: prices differ per source."""
    file = _source_file(key)
    return file.read_text(encoding="utf-8").strip() if file.exists() else "twelvedata"


def set_source(key: str, source: str) -> None:
    file = _source_file(key)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


def _market_file(key: str):
    return data_file(key, "market").with_suffix(".json")


def save_market(market: Market) -> None:
    """Remember a market that is not one of the four built in (forex pairs, stocks from files)."""
    file = _market_file(market.key)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(asdict(market)), encoding="utf-8")


def imported_keys() -> list[str]:
    return sorted(file.parent.name for file in (home() / "data").glob("*/market.json"))


def get_market(key: str) -> Market:
    if key in MARKETS:
        return HISTDATA[key] if source_of(key) == "histdata" else MARKETS[key]
    # the pattern keeps a strategy's market name from pointing outside the data folder
    if re.fullmatch(r"[A-Z0-9-]+", key) and _market_file(key).exists():
        return Market(**json.loads(_market_file(key).read_text(encoding="utf-8")))
    raise ValueError(
        f"Unknown market {key!r}. Valid markets: {', '.join(MARKETS)}, and the {len(imported_keys())} "
        "imported ones (forex pairs, stocks): data_status with a search lists them")


def session_keys(index: pd.DatetimeIndex, timezone: str, session_start: str) -> pd.DataFrame:
    """Per bar: the trading day it belongs to and the minutes since that day's start."""
    hours, minutes = map(int, session_start.split(":"))
    # wall-clock arithmetic, so a daylight-saving switch does not move the session boundary
    shifted = index.tz_convert(timezone).tz_localize(None) - pd.Timedelta(hours=hours, minutes=minutes)
    return pd.DataFrame(
        {"session": shifted.date, "minute": shifted.hour * 60 + shifted.minute}, index=index)

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Market:
    key: str
    symbol: str
    label: str
    timezone: str
    session_start: str
    note: str = ""


MARKETS: dict[str, Market] = {
    m.key: m
    for m in (
        Market("SP500", "SPY", "S&P 500 (via the SPY fund)", "America/New_York", "09:30"),
        Market("NAS100", "QQQ", "Nasdaq 100 (via the QQQ fund)", "America/New_York", "09:30"),
        Market("GOLD", "XAU/USD", "Gold (spot)", "UTC", "00:00"),
        Market(
            "SILVER", "SLV", "Silver (via the SLV fund)", "America/New_York", "09:30",
            "Proxy: SLV silver fund, US market hours only. Spot silver needs a paid data plan.",
        ),
    )
}

# timeframe name -> minutes
TIMEFRAMES: dict[str, int] = {
    "1min": 1, "5min": 5, "15min": 15, "30min": 30, "1h": 60, "4h": 240, "1day": 1440}


def get_market(key: str) -> Market:
    if key not in MARKETS:
        raise ValueError(f"Unknown market {key!r}. Valid markets: {', '.join(MARKETS)}")
    return MARKETS[key]


def session_keys(index: pd.DatetimeIndex, timezone: str, session_start: str) -> pd.DataFrame:
    """Per bar: the trading day it belongs to and the minutes since that day's start."""
    hours, minutes = map(int, session_start.split(":"))
    # wall-clock arithmetic, so a daylight-saving switch does not move the session boundary
    shifted = index.tz_convert(timezone).tz_localize(None) - pd.Timedelta(hours=hours, minutes=minutes)
    return pd.DataFrame(
        {"session": shifted.date, "minute": shifted.hour * 60 + shifted.minute}, index=index)

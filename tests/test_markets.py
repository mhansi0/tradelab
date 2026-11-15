import pandas as pd
import pytest

from tradelab.markets import MARKETS, TIMEFRAMES, get_market, session_keys


def test_market_symbols():
    assert {k: m.symbol for k, m in MARKETS.items()} == {
        "SP500": "SPY", "NAS100": "QQQ", "GOLD": "XAU/USD", "SILVER": "SLV"}


def test_timeframes():
    assert TIMEFRAMES == {"1min": 1, "5min": 5, "15min": 15, "30min": 30,
                          "1h": 60, "4h": 240, "1day": 1440}


def test_get_market_unknown_lists_valid_keys():
    with pytest.raises(ValueError, match="GOLD"):
        get_market("BITCOIN")


def test_silver_is_flagged_as_proxy():
    assert "Proxy" in get_market("SILVER").note


def test_session_keys_new_york():
    idx = pd.DatetimeIndex(
        ["2025-01-02 14:30", "2025-01-02 14:35", "2025-01-03 14:30"], tz="UTC")
    k = session_keys(idx, "America/New_York", "09:30")
    assert list(k["minute"]) == [0, 5, 0]
    assert k["session"].nunique() == 2


def test_bar_before_session_start_belongs_to_previous_session():
    idx = pd.DatetimeIndex(["2025-01-02 23:55", "2025-01-03 00:00"], tz="UTC")
    k = session_keys(idx, "UTC", "00:00")
    assert k["session"].iloc[0] != k["session"].iloc[1]
    assert list(k["minute"]) == [1435, 0]

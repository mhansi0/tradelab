from datetime import datetime, timezone

import pandas as pd
import pytest
from conftest import make_candles

from tradelab.store import (
    DataMissingError, load_base, load_candles, resample, save_candles, status)


def test_save_merges_without_duplicates(home):
    a = make_candles("2025-01-02 00:00", 10, "5min")
    b = make_candles("2025-01-02 00:25", 10, "5min", price=200.0)
    save_candles("GOLD", "5min", a)
    save_candles("GOLD", "5min", b)
    out = load_base("GOLD", "5min")
    assert len(out) == 15 and out.index.is_monotonic_increasing
    assert out.loc["2025-01-02 00:25", "close"] == 200.0
    assert out.index.name == "time" and str(out.index.tz) == "UTC"


def test_load_base_missing_is_empty(home):
    out = load_base("GOLD", "5min")
    assert out.empty and list(out.columns) == ["open", "high", "low", "close", "volume"]


def test_resample_aggregates_ohlcv():
    df = make_candles("2025-01-02 00:00", 3, "5min")
    df["open"] = [1, 2, 3.0]
    df["high"] = [5, 9, 4.0]
    df["low"] = [0.5, 1, 2.0]
    df["close"] = [2, 3, 3.5]
    df["volume"] = [10, 20, 30.0]
    out = resample(df, 15, "UTC", "00:00")
    assert out.iloc[0].tolist() == [1.0, 9.0, 0.5, 3.5, 60.0]
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]


def test_4h_on_us_session_gives_two_bars():
    df = make_candles("2025-01-02 14:30", 78, "5min")  # 09:30 to 16:00 New York
    out = resample(df, 240, "America/New_York", "09:30")
    assert [t.strftime("%H:%M") for t in out.index] == ["14:30", "18:30"]


def test_1day_gives_one_bar_per_session():
    df = make_candles("2025-01-02 14:30", 78, "5min")
    assert len(resample(df, 1440, "America/New_York", "09:30")) == 1


def test_resample_survives_missing_first_bars():
    df = make_candles("2025-01-02 14:30", 78, "5min").iloc[7:]
    out = resample(df, 60, "America/New_York", "09:30")
    assert out.index[0].strftime("%H:%M") == "14:30" and not out.isna().any().any()


def test_resample_skips_weekend_gap():
    fri = make_candles("2025-01-03 14:30", 78, "5min")
    mon = make_candles("2025-01-06 14:30", 78, "5min")
    out = resample(pd.concat([fri, mon]), 1440, "America/New_York", "09:30")
    assert len(out) == 2


def test_load_candles_resamples_from_5min(home):
    save_candles("GOLD", "5min", make_candles("2025-01-02 00:00", 24, "5min"))
    assert len(load_candles("GOLD", "1h")) == 2


def test_load_candles_1min_reads_1min_file(home):
    save_candles("GOLD", "1min", make_candles("2025-01-02 00:00", 7, "1min"))
    save_candles("GOLD", "5min", make_candles("2025-01-02 00:00", 24, "5min"))
    assert len(load_candles("GOLD", "1min")) == 7
    assert len(load_candles("GOLD", "5min")) == 24


def test_load_candles_start_and_end(home):
    save_candles("GOLD", "5min", make_candles("2025-01-02 00:00", 48, "5min"))
    out = load_candles(
        "GOLD", "1h",
        start=datetime(2025, 1, 2, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 2, 3, tzinfo=timezone.utc))
    assert [t.strftime("%H:%M") for t in out.index] == ["01:00", "02:00"]


def test_load_candles_missing_data(home):
    with pytest.raises(DataMissingError, match="tradelab download"):
        load_candles("GOLD", "1h")


def test_load_candles_unknown_timeframe(home):
    with pytest.raises(ValueError, match="1h"):
        load_candles("GOLD", "2h")


def test_status_lists_what_is_stored(home):
    save_candles("GOLD", "5min", make_candles("2025-01-02 00:00", 24, "5min"))
    rows = status()
    assert rows == [{"market": "GOLD", "base": "5min", "rows": 24,
                     "first": "2025-01-02T00:00:00+00:00", "last": "2025-01-02T01:55:00+00:00"}]

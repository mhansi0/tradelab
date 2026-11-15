from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from conftest import make_candles

from tradelab.download import download, plan_ranges
from tradelab.store import load_base, save_candles
from tradelab.twelvedata import DataSourceError

NOW = datetime(2025, 1, 10, tzinfo=timezone.utc)
WANT = datetime(2024, 1, 10, tzinfo=timezone.utc)
FIRST = datetime(2024, 6, 1, tzinfo=timezone.utc)
LAST = datetime(2025, 1, 9, tzinfo=timezone.utc)
QUIET = lambda *_: None  # noqa: E731


def full_fetch(symbol, interval, start, end, **_):
    """Two pages, newest first, like the real source."""
    yield make_candles("2025-01-02 00:50", 10, "5min")
    yield make_candles("2025-01-02 00:00", 10, "5min")


def test_plan_ranges():
    assert plan_ranges(None, None, WANT, NOW) == [(WANT, NOW)]
    assert plan_ranges(FIRST, LAST, WANT, NOW) == [(LAST, NOW), (WANT, FIRST)]
    assert plan_ranges(WANT, LAST, WANT, NOW) == [(LAST, NOW)]


def test_download_stores_both_bases_under_the_market_key(home):
    asked = []

    def fetch(symbol, interval, start, end, **_):
        asked.append((symbol, interval, start, end))
        yield make_candles("2025-01-02 00:00", 10, interval)

    download(["GOLD"], years_5min=5, years_1min=1, fetch=fetch, now=NOW, log=QUIET)
    assert len(load_base("GOLD", "5min")) == 10 and len(load_base("GOLD", "1min")) == 10
    assert [(a[0], a[1]) for a in asked] == [("XAU/USD", "5min"), ("XAU/USD", "1min")]
    assert asked[0][2] == NOW - timedelta(days=365.25 * 5) and asked[1][2] == NOW - timedelta(days=365.25)


def test_download_resumes_without_duplicates(home):
    def flaky(symbol, interval, start, end, **_):
        yield make_candles("2025-01-02 00:50", 10, "5min")
        raise DataSourceError("network")

    with pytest.raises(DataSourceError):
        download(["GOLD"], fetch=flaky, now=NOW, log=QUIET)
    assert len(load_base("GOLD", "5min")) == 10  # the first page was saved

    download(["GOLD"], fetch=full_fetch, now=NOW, log=QUIET)
    stored = load_base("GOLD", "5min")
    assert stored.index.is_unique and len(stored) == 20


def test_interrupted_update_leaves_no_hole(home):
    save_candles("GOLD", "5min", make_candles("2024-12-01 00:00", 10, "5min"))
    save_candles("GOLD", "1min", make_candles("2024-12-01 00:00", 10, "1min"))

    def flaky_update(symbol, interval, start, end, **_):
        if end == NOW:  # the catch-up range: newest page arrives, then the connection drops
            yield make_candles("2025-01-09 00:00", 10, interval)
            raise DataSourceError("network")
        yield from ()

    with pytest.raises(DataSourceError):
        download(["GOLD"], fetch=flaky_update, now=NOW, log=QUIET)
    # nothing newer was stored, so the next run still asks for everything after the old last candle
    assert load_base("GOLD", "5min").index[-1] == pd.Timestamp("2024-12-01 00:45", tz="UTC")


def test_download_logs_progress_without_key(home, monkeypatch):
    monkeypatch.setenv("TWELVEDATA_API_KEY", "SECRET123")
    lines = []
    download(["GOLD"], fetch=full_fetch, now=NOW, log=lines.append)
    assert any(line.startswith("GOLD 5min") for line in lines)
    assert not any("SECRET123" in line for line in lines)


def test_download_skips_a_market_that_holds_imported_files(home):
    from tradelab.markets import set_source

    save_candles("GOLD", "5min", make_candles("2024-12-01 00:00", 10, "5min", price=2000.0))
    set_source("GOLD", "histdata")
    lines, asked = [], []

    def fetch(symbol, interval, start, end, **_):
        asked.append(symbol)
        yield make_candles("2025-01-02 00:00", 10, interval)

    download(["GOLD", "SP500"], fetch=fetch, now=NOW, log=lines.append)
    assert set(asked) == {"SPY"} and len(load_base("GOLD", "5min")) == 10
    assert any("GOLD" in line and "skipped" in line.lower() for line in lines)


def test_market_names_are_forgiving(home):
    download([" gold "], fetch=full_fetch, now=NOW, log=QUIET)
    assert not load_base("GOLD", "5min").empty


def test_unknown_market_fails_before_any_request(home):
    with pytest.raises(ValueError, match="BITCOIN"):
        download(["BITCOIN"], fetch=full_fetch, now=NOW, log=QUIET)

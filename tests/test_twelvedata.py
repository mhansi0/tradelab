from datetime import datetime, timezone

import httpx
import pandas as pd
import pytest

from tradelab.twelvedata import DataSourceError, api_key, fetch_page, fetch_range

START = datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc)
END = datetime(2025, 1, 2, 1, 15, tzinfo=timezone.utc)
KEY = "SECRET123"


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("TWELVEDATA_API_KEY", KEY)


def client_returning(payload):
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))


def paged_client():
    """15 five-minute candles from START. Each request returns the 5 candles before `end_date`."""
    all_times = pd.date_range(START, periods=15, freq="5min")
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        end = pd.Timestamp(request.url.params["end_date"], tz="UTC")
        times = [t for t in all_times if t < end][-5:]
        values = [{"datetime": t.strftime("%Y-%m-%d %H:%M:%S"), "open": "1", "high": "2",
                   "low": "0.5", "close": "1.5", "volume": "10"} for t in reversed(times)]
        return httpx.Response(200, json={"status": "ok", "values": values})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def test_fetch_page_parses_to_utc_floats():
    client = client_returning({"status": "ok", "values": [
        {"datetime": "2025-01-02 00:05:00", "open": "2", "high": "3", "low": "1", "close": "2.5"},
        {"datetime": "2025-01-02 00:00:00", "open": "1", "high": "2", "low": "0.5", "close": "2"}]})
    df = fetch_page("XAU/USD", "5min", None, client)
    assert str(df.index.tz) == "UTC" and df.index.is_monotonic_increasing and df.index.name == "time"
    assert df["close"].tolist() == [2.0, 2.5] and df["volume"].tolist() == [0.0, 0.0]
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_fetch_page_drops_rows_at_or_after_end():
    client = client_returning({"status": "ok", "values": [
        {"datetime": "2025-01-02 00:05:00", "open": "2", "high": "3", "low": "1", "close": "2.5"},
        {"datetime": "2025-01-02 00:00:00", "open": "1", "high": "2", "low": "0.5", "close": "2"}]})
    df = fetch_page("XAU/USD", "5min", datetime(2025, 1, 2, 0, 5, tzinfo=timezone.utc), client)
    assert len(df) == 1


def test_fetch_page_asks_for_utc_and_full_pages():
    client, calls = paged_client()
    fetch_page("SPY", "5min", END, client)
    assert calls[0]["timezone"] == "UTC" and calls[0]["outputsize"] == "5000"
    assert calls[0]["end_date"] == "2025-01-02T01:15:00" and calls[0]["symbol"] == "SPY"


def test_fetch_range_pages_back_until_start():
    client, calls = paged_client()
    slept = []
    frames = list(fetch_range("SPY", "5min", START, END, client=client, sleep=slept.append))
    assert len(frames) == 3 and len(calls) == 3
    assert slept == [8, 8]
    combined = pd.concat(frames)
    assert combined.index.is_unique and len(combined) == 15


def test_fetch_range_drops_rows_before_start():
    client, _ = paged_client()
    later = datetime(2025, 1, 2, 0, 10, tzinfo=timezone.utc)
    frames = list(fetch_range("SPY", "5min", later, END, client=client, sleep=lambda s: None))
    assert pd.concat(frames).index.min() == pd.Timestamp(later)


def test_fetch_range_stops_when_source_has_no_older_data():
    client, calls = paged_client()
    long_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
    frames = list(fetch_range("SPY", "5min", long_ago, END, client=client, sleep=lambda s: None))
    assert len(pd.concat(frames)) == 15 and len(calls) == 4


def test_404_means_no_older_data():
    client = client_returning({"status": "error", "code": 404, "message": "not found"})
    assert fetch_page("SPY", "5min", END, client).empty


def test_400_no_data_also_means_no_older_data():
    client = client_returning({"status": "error", "code": 400,
                               "message": "No data is available on the specified dates."})
    assert fetch_page("SPY", "5min", END, client).empty


def test_other_400_is_still_an_error():
    client = client_returning({"status": "error", "code": 400, "message": "Invalid interval"})
    with pytest.raises(DataSourceError, match="Invalid interval"):
        fetch_page("SPY", "5min", END, client)


def test_rate_limit_retries_then_fails():
    client = client_returning({"status": "error", "code": 429, "message": "limit"})
    slept = []
    with pytest.raises(DataSourceError, match="limit"):
        list(fetch_range("SPY", "5min", START, END, client=client, sleep=slept.append))
    assert slept.count(60) == 5


def test_api_error_message_hides_key():
    client = client_returning(
        {"status": "error", "code": 403, "message": f"plan upgrade needed for apikey {KEY}"})
    with pytest.raises(DataSourceError) as e:
        fetch_page("XAG/USD", "5min", None, client)
    assert "plan" in str(e.value) and KEY not in str(e.value)


def test_network_error_hides_key():
    def boom(request):
        raise httpx.ConnectError("cannot connect", request=request)

    client = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(DataSourceError) as e:
        fetch_page("SPY", "5min", None, client)
    assert KEY not in str(e.value) and KEY not in repr(e.value.__cause__)


def test_key_from_file(home, monkeypatch):
    monkeypatch.delenv("TWELVEDATA_API_KEY")
    (home / "twelvedata.key").write_text("  FROMFILE\n", encoding="utf-8")
    assert api_key() == "FROMFILE"


def test_missing_key_explains(home, monkeypatch):
    monkeypatch.delenv("TWELVEDATA_API_KEY")
    with pytest.raises(DataSourceError, match="TWELVEDATA_API_KEY"):
        api_key()

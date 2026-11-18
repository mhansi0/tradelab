import json

import httpx
import pandas as pd
import pytest

from tradelab.fetch import DEFAULT_SOURCE, SOURCE_ENV, available, fetch, write_index
from tradelab.markets import imported_keys
from tradelab.store import load_base
from tradelab.twelvedata import DataSourceError

SOURCE = "https://data.example.test/candles"


def parquet_bytes(tmp_path, times) -> bytes:
    path = tmp_path / "made.parquet"
    pd.DataFrame({"datetime": times, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10}).to_parquet(path)
    return path.read_bytes()


@pytest.fixture
def server(tmp_path):
    """A fake web folder with two stock files. `requests` records every path asked for."""
    body = parquet_bytes(tmp_path, pd.date_range("2024-07-01 09:30", periods=10, freq="1min"))
    files = {"AAPL_clean_1min.parquet": body, "MSFT_clean_1min.parquet": body}
    index = {"files": [*files, "../evil.parquet", 5]}
    requests = []

    def handler(request):
        name = request.url.path.removeprefix("/candles/")
        requests.append(name)
        if name == "index.json":
            return httpx.Response(200, json=index)
        return httpx.Response(200, content=files[name]) if name in files else httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def test_fetch_downloads_only_the_asked_markets_and_imports_them(home, server):
    client, requests = server
    assert fetch(["aapl"], SOURCE, client, log=lambda *_: None) == {"AAPL": 10}
    assert requests == ["index.json", "AAPL_clean_1min.parquet"]  # MSFT is never downloaded
    assert len(load_base("AAPL", "1min")) == 10 and imported_keys() == ["AAPL"]


def test_available_ignores_index_entries_that_are_not_plain_file_names(server):
    assert available(SOURCE, server[0]) == {"AAPL": "AAPL_clean_1min.parquet", "MSFT": "MSFT_clean_1min.parquet"}


def test_an_unknown_name_stops_before_anything_is_downloaded(home, server):
    client, requests = server
    with pytest.raises(DataSourceError, match="NOPE"):
        fetch(["AAPL", "nope"], SOURCE, client, log=lambda *_: None)
    assert requests == ["index.json"] and imported_keys() == []


def test_an_unusable_address_says_how_to_set_it(monkeypatch):
    monkeypatch.delenv(SOURCE_ENV, raising=False)
    for source in ("http://plain.example.test", "http://localhost.evil.test"):  # https only
        with pytest.raises(DataSourceError, match=SOURCE_ENV):
            available(source)


def test_without_an_address_the_shared_dataset_is_used(monkeypatch):
    monkeypatch.delenv(SOURCE_ENV, raising=False)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"files": ["AAPL_clean_1min.parquet"]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert set(available(None, client)) == {"AAPL"}
    assert seen == [f"{DEFAULT_SOURCE}/index.json"]


def test_plain_http_is_allowed_for_this_computer_only(server):
    assert set(available("http://localhost:8000/candles", server[0])) == {"AAPL", "MSFT"}


def test_the_address_can_come_from_the_environment(home, server, monkeypatch):
    monkeypatch.setenv(SOURCE_ENV, SOURCE + "/")
    assert set(available(client=server[0])) == {"AAPL", "MSFT"}


def test_a_failed_download_is_reported_without_the_address_details(home):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(DataSourceError, match="index.json"):
        available(SOURCE, client)


def test_write_index_lists_the_parquet_files(tmp_path):
    (tmp_path / "AAPL_clean_1min.parquet").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    assert json.loads(write_index(tmp_path).read_text(encoding="utf-8")) == {"files": ["AAPL_clean_1min.parquet"]}

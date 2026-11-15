import pandas as pd
import pytest

from tradelab import server
from tradelab.markets import get_market, imported_keys, source_of
from tradelab.parquet_import import import_parquet_folder
from tradelab.store import load_base, load_candles


def put(path, times, price=100.0, time_column="time", **names):
    """A parquet candle file; `names` renames columns, for example Open='Open'."""
    n = len(times)
    df = pd.DataFrame({"open": price, "high": price + 1, "low": price - 1, "close": price + 0.5,
                       "volume": 10}, index=range(n))
    df.insert(0, time_column, times)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.rename(columns=names).to_parquet(path)


def stock_times(day="2024-07-01", minutes=10):  # no time zone: New York wall clock
    return pd.date_range(f"{day} 09:30", periods=minutes, freq="1min")


def test_stock_times_are_new_york_and_the_market_is_remembered(home, tmp_path):
    put(tmp_path / "sub" / "AAPL_clean_1min.parquet", stock_times(), time_column="datetime",
        open="Open", high="High", low="Low", close="Close", volume="Volume")
    assert import_parquet_folder(tmp_path, log=lambda *_: None) == {"AAPL": 10}
    one = load_base("AAPL", "1min")
    assert one.index[0] == pd.Timestamp("2024-07-01 13:30", tz="UTC")  # 09:30 in summer is 13:30 UTC
    assert len(load_base("AAPL", "5min")) == 2 and len(load_candles("AAPL", "1h")) == 1
    market = get_market("AAPL")
    assert (market.session_start, market.source, "IEX" in market.note) == ("09:30", "parquet", True)
    assert imported_keys() == ["AAPL"]


def test_forex_files_keep_their_utc_times_and_start_the_day_at_17_00(home, tmp_path):
    times = pd.date_range("2024-01-07 22:00", periods=10, freq="1min", tz="UTC")
    put(tmp_path / "EURUSD_M1_2022-2026.parquet", times, price=1.1)
    import_parquet_folder(tmp_path, log=lambda *_: None)
    assert load_base("EURUSD", "1min").index[0] == times[0]
    assert get_market("EURUSD").session_start == "17:00"
    assert len(load_candles("EURUSD", "1day")) == 1  # Sunday 17:00 New York opens Monday's day


def test_a_histdata_symbol_goes_to_its_built_in_market(home, tmp_path):
    put(tmp_path / "XAUUSD_M1_2022-2026.parquet", pd.date_range("2024-01-02 23:00", periods=5, freq="1min", tz="UTC"))
    assert import_parquet_folder(tmp_path, log=lambda *_: None) == {"GOLD": 5}
    assert source_of("GOLD") == "histdata" and imported_keys() == []


def test_a_ticker_named_like_a_built_in_market_gets_a_suffix(home, tmp_path):
    put(tmp_path / "GOLD_clean_1min.parquet", stock_times(), time_column="datetime")
    assert import_parquet_folder(tmp_path, log=lambda *_: None) == {"GOLD-US": 10}


def test_a_broken_file_is_skipped_and_the_rest_is_imported(home, tmp_path):
    (tmp_path / "BAD_clean_1min.parquet").write_text("not parquet", encoding="utf-8")
    put(tmp_path / "AAPL_clean_1min.parquet", stock_times(), time_column="datetime")
    lines = []
    assert import_parquet_folder(tmp_path, log=lines.append) == {"AAPL": 10}
    assert any("BAD_clean_1min.parquet" in line for line in lines) and "1 files skipped" in lines[-1]


def test_importing_twice_does_not_duplicate_minutes(home, tmp_path):
    put(tmp_path / "AAPL_clean_1min.parquet", stock_times(), time_column="datetime")
    for _ in range(2):
        import_parquet_folder(tmp_path, log=lambda *_: None)
    assert len(load_base("AAPL", "1min")) == 10


def test_folder_without_parquet_files_is_an_error(home, tmp_path):
    with pytest.raises(ValueError, match="No .parquet files"):
        import_parquet_folder(tmp_path)


def test_unknown_market_names_stay_inside_the_data_folder(home):
    for key in ("../x", "AAPL", "aapl"):
        with pytest.raises(ValueError, match="Unknown market"):
            get_market(key)


def test_data_status_lists_imported_markets_only_when_searched(home, tmp_path):
    for name in ("AAPL", "AAL", "MSFT"):
        put(tmp_path / f"{name}_clean_1min.parquet", stock_times(), time_column="datetime")
    import_parquet_folder(tmp_path, log=lambda *_: None)
    assert {r["market"] for r in server.data_status()} == {"SP500", "NAS100", "GOLD", "SILVER"}
    found = {r["market"]: r for r in server.data_status(search="aa")}
    assert set(found) == {"AAPL", "AAL"} and found["AAPL"]["data"][0]["rows"] == 10
    assert {r["market"] for r in server.data_status(search="us stock")} == {"AAPL", "AAL", "MSFT"}

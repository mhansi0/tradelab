import zipfile

import pandas as pd
import pytest
from conftest import make_candles

from tradelab.histdata import import_folder, parse
from tradelab.markets import get_market, source_of
from tradelab.store import load_base, load_candles, save_candles


def rows(start: str, minutes: int, price: float = 2000.0) -> str:
    """HistData M1 lines: EST timestamps, semicolons, volume 0."""
    times = pd.date_range(start, periods=minutes, freq="1min")
    return "".join(
        f"{t:%Y%m%d %H%M%S};{price + i:.3f};{price + i + 1:.3f};{price + i - 1:.3f};{price + i + 0.5:.3f};0\n"
        for i, t in enumerate(times))


def put_zip(folder, symbol: str, period: str, text: str):
    path = folder / f"HISTDATA_COM_ASCII_{symbol}_M1_{period}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"DAT_ASCII_{symbol}_M1_{period}.csv", text)
        archive.writestr(f"DAT_ASCII_{symbol}_M1_{period}.txt", "status report")
    return path


def test_parse_converts_est_to_utc():
    df = parse(rows("2024-01-02 18:00", 2), "file.csv")
    assert df.index[0] == pd.Timestamp("2024-01-02 23:00", tz="UTC") and df.index.name == "time"
    assert df.iloc[0].tolist() == [2000.0, 2001.0, 1999.0, 2000.5, 0.0]
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


@pytest.mark.parametrize("bad", ["not;a;candle\n", "20240102 180000;1;2\n", "", "20240102 180000;5;6;4;-1;0\n"])
def test_parse_names_the_file_when_it_cannot_read_it(bad):
    with pytest.raises(ValueError, match="broken.csv"):
        parse(bad, "broken.csv")


def test_import_stores_candles_and_marks_the_source(home, tmp_path):
    folder = tmp_path / "in"
    folder.mkdir()
    put_zip(folder, "XAUUSD", "2024", rows("2024-01-02 18:00", 12))
    lines = []
    counts = import_folder(folder, log=lines.append)
    assert counts == {"GOLD": 12}
    assert len(load_base("GOLD", "1min")) == 12 and len(load_base("GOLD", "5min")) == 3
    assert source_of("GOLD") == "histdata"
    gold = get_market("GOLD")
    assert (gold.symbol, gold.source) == ("XAUUSD", "histdata") and "HistData" in gold.note
    assert len(load_candles("GOLD", "1h")) == 1
    assert any("GOLD" in line for line in lines)


def test_five_minute_candles_are_built_from_the_minutes(home, tmp_path):
    put_zip(tmp_path, "XAUUSD", "2024", rows("2024-01-02 18:00", 5))
    import_folder(tmp_path, log=lambda *_: None)
    five = load_base("GOLD", "5min").iloc[0]
    assert five.tolist() == [2000.0, 2005.0, 1999.0, 2004.5, 0.0]


def test_plain_csv_and_all_four_markets(home, tmp_path):
    for symbol in ("XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD"):
        (tmp_path / f"DAT_ASCII_{symbol}_M1_202401.csv").write_text(rows("2024-01-02 10:00", 5), encoding="utf-8")
    assert import_folder(tmp_path, log=lambda *_: None) == {"GOLD": 5, "SILVER": 5, "SP500": 5, "NAS100": 5}
    assert "Proxy" not in get_market("SILVER").note and get_market("SP500").symbol == "SPXUSD"


def test_markets_without_import_keep_the_twelve_data_definition(home, tmp_path):
    put_zip(tmp_path, "XAUUSD", "2024", rows("2024-01-02 18:00", 5))
    import_folder(tmp_path, log=lambda *_: None)
    assert (get_market("SP500").symbol, get_market("SP500").source) == ("SPY", "twelvedata")
    assert source_of("SILVER") == "twelvedata"


def test_second_import_merges_without_duplicates(home, tmp_path):
    put_zip(tmp_path, "XAUUSD", "2023", rows("2023-12-29 16:55", 5))
    import_folder(tmp_path, log=lambda *_: None)
    put_zip(tmp_path, "XAUUSD", "2024", rows("2023-12-29 16:58", 7))  # overlaps two minutes
    import_folder(tmp_path, log=lambda *_: None)
    one = load_base("GOLD", "1min")
    assert one.index.is_unique and len(one) == 10
    assert len(load_base("GOLD", "5min")) == 2 and load_base("GOLD", "5min")["high"].iloc[1] == one["high"].iloc[5:].max()


def test_import_refuses_to_mix_with_twelve_data(home, tmp_path):
    save_candles("GOLD", "5min", make_candles("2024-01-02 00:00", 10, "5min", price=200.0))
    put_zip(tmp_path, "XAUUSD", "2024", rows("2024-01-02 18:00", 5))
    with pytest.raises(ValueError, match="--replace"):
        import_folder(tmp_path, log=lambda *_: None)
    assert load_base("GOLD", "1min").empty and source_of("GOLD") == "twelvedata"

    import_folder(tmp_path, replace=True, log=lambda *_: None)
    assert source_of("GOLD") == "histdata"
    assert load_base("GOLD", "5min")["close"].min() > 1000  # the old 200.0 candles are gone


def test_other_files_are_skipped_and_reported(home, tmp_path):
    put_zip(tmp_path, "XAUUSD", "2024", rows("2024-01-02 18:00", 5))
    put_zip(tmp_path, "EURUSD", "2024", rows("2024-01-02 18:00", 5, price=1.1))
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    lines = []
    assert import_folder(tmp_path, log=lines.append) == {"GOLD": 5}
    assert any("EURUSD" in line and "skipped" in line.lower() for line in lines)


def test_folder_without_histdata_files(home, tmp_path):
    with pytest.raises(ValueError, match="No HistData files"):
        import_folder(tmp_path, log=lambda *_: None)
    with pytest.raises(ValueError, match="not a folder"):
        import_folder(tmp_path / "missing", log=lambda *_: None)


def test_broken_file_stops_before_anything_is_stored(home, tmp_path):
    put_zip(tmp_path, "XAUUSD", "2023", rows("2023-06-01 10:00", 5))
    put_zip(tmp_path, "XAUUSD", "2024", "garbage\n")
    with pytest.raises(ValueError, match="XAUUSD_M1_2024"):
        import_folder(tmp_path, log=lambda *_: None)
    assert load_base("GOLD", "1min").empty and source_of("GOLD") == "twelvedata"


def test_command_line(home, tmp_path, capsys):
    from tradelab.download import main

    put_zip(tmp_path, "XAUUSD", "2024", rows("2024-01-02 18:00", 5))
    main(["import", str(tmp_path)])
    assert "GOLD" in capsys.readouterr().out and len(load_base("GOLD", "1min")) == 5
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit, match="No HistData files"):
        main(["import", str(tmp_path / "empty")])

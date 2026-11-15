import pytest

from tradelab import paths


def test_home_uses_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    assert paths.home() == tmp_path


def test_data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    assert paths.data_file("GOLD", "5min") == tmp_path / "data" / "GOLD" / "5min.parquet"


def test_slugify():
    assert paths.slugify("Goud Eerste Candle!") == "goud-eerste-candle"


def test_slugify_rejects_traversal():
    with pytest.raises(ValueError):
        paths.slugify("../..")


def test_strategy_dir_stays_inside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    assert paths.strategy_dir("a/../../b").parent == tmp_path / "strategies"

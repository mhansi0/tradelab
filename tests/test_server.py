import json
from pathlib import Path

import pytest

from tradelab import server
from tradelab.report import DISCLAIMER

NAME = "goud-eerste-candle-short"


def test_full_flow(home, example, gold_data):
    assert server.validate_strategy(example) == {
        "ok": True, "errors": [], "strategy": server.validate_strategy(example)["strategy"]}
    saved = server.save_strategy(example)
    assert saved["name"] == NAME and Path(saved["path"]).exists()

    out = server.run_backtest(NAME)
    assert out["summary"]["trades"] == 19 and out["summary"]["wins"] == 9
    assert [e["kind"] for e in out["examples"]] == ["loss", "win", "long"]
    assert out["examples"][0]["conditions"][0]["expr"] == "bar_of_day == 2"
    assert all(c["passed"] for e in out["examples"] for c in e["conditions"])
    assert out["examples"][1]["trade"]["outcome"] == "tp" and out["examples"][1]["trade"]["r"] == 4.0
    assert out["data_range"] == ["2025-01-06", "2025-01-25"]
    json.dumps(out)  # everything a tool returns must be plain JSON

    path = server.build_report(NAME, "Looks fine.")["path"]
    html = Path(path).read_text(encoding="utf-8")
    assert html.count(DISCLAIMER) == 1 and "<p>Looks fine.</p>" in html
    assert html.count('class="plotly-graph-div"') == 6

    got = server.get_strategy(NAME)
    assert got["summary"]["trades"] == 19 and got["report_path"] == path
    assert got["strategy"]["setups"][0]["stop"] == "first.high"
    assert server.list_strategies() == [
        {"name": NAME, "market": "GOLD", "timeframe": "1h", "has_backtest": True}]


def test_validate_reports_errors_without_raising(home, example):
    example["setups"][0]["entry_when"] = ["foo > 1"]
    out = server.validate_strategy(example)
    assert out["ok"] is False and out["strategy"] is None and "foo > 1" in out["errors"][0]


def test_invalid_strategy_is_not_saved(home, example):
    example["setups"][0]["entry_when"] = ["foo > 1"]
    with pytest.raises(ValueError, match="foo > 1"):
        server.save_strategy(example)
    assert server.list_strategies() == []


def test_existing_strategy_needs_overwrite(home, example):
    server.save_strategy(example)
    with pytest.raises(FileExistsError):
        server.save_strategy(example)
    server.save_strategy(example, overwrite=True)


def test_get_strategy_before_any_backtest(home, example):
    server.save_strategy(example)
    got = server.get_strategy(NAME)
    assert got["summary"] is None and got["report_path"] is None


def test_backtest_without_data_says_how_to_download(home, example):
    server.save_strategy(example)
    with pytest.raises(Exception, match="tradelab download"):
        server.run_backtest(NAME)


def test_unknown_strategy_lists_names(home):
    with pytest.raises(ValueError, match="No strategy named"):
        server.get_strategy("nope")
    with pytest.raises(ValueError, match="No strategy named"):
        server.run_backtest("nope")


def test_report_needs_a_backtest_first(home, example, gold_data):
    server.save_strategy(example)
    with pytest.raises(ValueError, match="run_backtest"):
        server.build_report(NAME, "")


def test_zero_trades_flow(home, never_triggers, gold_data):
    server.save_strategy(never_triggers)
    out = server.run_backtest("never")
    assert out["summary"]["trades"] == 0 and out["examples"] == []
    html = Path(server.build_report("never", "")["path"]).read_text(encoding="utf-8")
    assert "No trades" in html


def test_period_longer_than_data_warns(home, example, gold_data):
    server.save_strategy(example)
    out = server.run_backtest(NAME, start="2000-01-01")
    assert any("starts" in w for w in out["warnings"]) and out["data_range"][0] > "2000-01-01"


def test_period_limits_the_backtest(home, example, gold_data):
    server.save_strategy(example)
    out = server.run_backtest(NAME, start="2025-01-10", end="2025-01-15")
    assert out["data_range"] == ["2025-01-10", "2025-01-14"] and 0 < out["summary"]["trades"] < 19
    assert json.loads((home / "strategies" / NAME / "backtest.json").read_text(encoding="utf-8"))["start"] == "2025-01-10"


def test_period_without_any_candles(home, example, gold_data):
    server.save_strategy(example)
    out = server.run_backtest(NAME, start="2030-01-01")
    assert out["summary"]["trades"] == 0 and out["examples"] == [] and out["data_range"] == []
    assert any("no candles" in w for w in out["warnings"])
    html = Path(server.build_report(NAME, "")["path"]).read_text(encoding="utf-8")
    assert "No trades" in html


def test_bad_date_is_explained(home, example, gold_data):
    server.save_strategy(example)
    with pytest.raises(ValueError, match="date"):
        server.run_backtest(NAME, start="yesterday-ish")


def test_few_trades_warns(home, example, gold_data):
    server.save_strategy(example)
    assert any("too few" in w for w in server.run_backtest(NAME)["warnings"])


def test_seed_changes_examples_but_not_summary(home, example, gold_data):
    server.save_strategy(example)
    runs = [server.run_backtest(NAME, seed=seed) for seed in range(6)]
    assert all(r["summary"] == runs[0]["summary"] for r in runs)
    assert len({r["examples"][0]["trade"]["entry_time"] for r in runs}) > 1


def test_report_uses_the_seed_of_the_last_backtest(home, example, gold_data):
    server.save_strategy(example)
    out = server.run_backtest(NAME, seed=3)
    html = Path(server.build_report(NAME, "")["path"]).read_text(encoding="utf-8")
    assert out["examples"][0]["trade"]["entry_time"][:16].replace("T", " ") in html


def test_data_status_lists_all_markets(home, gold_data):
    rows = {r["market"]: r for r in server.data_status()}
    assert set(rows) == {"SP500", "NAS100", "GOLD", "SILVER"}
    assert rows["GOLD"]["data"][0]["base"] == "5min" and rows["SP500"]["data"] == []
    assert "Proxy" in rows["SILVER"]["note"]


def test_data_status_and_warnings_follow_the_source_of_the_data(home, example, gold_data):
    from tradelab.markets import set_source

    set_source("GOLD", "histdata")
    gold = {r["market"]: r for r in server.data_status()}["GOLD"]
    assert gold["source"] == "histdata" and "HistData" in gold["note"]
    server.save_strategy(example)
    assert any("HistData" in w for w in server.run_backtest(NAME)["warnings"])


def test_tools_are_registered():
    import asyncio

    names = {tool.name for tool in asyncio.run(server.server.list_tools())}
    assert names == {"data_status", "validate_strategy", "save_strategy", "list_strategies",
                     "get_strategy", "run_backtest", "build_report"}

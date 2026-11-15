import pandas as pd

from tradelab.engine import BacktestResult, Trade
from tradelab.stats import pick_examples, summarize

START = pd.Timestamp("2025-01-01", tz="UTC")
END = pd.Timestamp("2025-03-01", tz="UTC")


def trade(r, bars=1, day="2025-01-02"):
    when = pd.Timestamp(day, tz="UTC")
    if r is None:
        return Trade("s", "long", when, when, 100.0, 99.0, 102.0, None, None, "open", None, bars)
    outcome = "tp" if r > 0 else "sl"
    return Trade("s", "long", when, when, 100.0, 99.0, 102.0, when, 100.0 + r, outcome, float(r), bars)


def result(trades, skipped=()):
    return BacktestResult(list(trades), list(skipped), START, END, 100)


def test_summarize_known_trades():
    days = ["2025-01-02", "2025-01-03", "2025-02-03", "2025-02-04"]
    s = summarize(result(trade(r, bars, d) for r, bars, d in zip([2, -1, -1, 4], [1, 2, 3, 6], days)))
    assert (s["trades"], s["wins"], s["losses"], s["win_rate"], s["total_r"]) == (4, 2, 2, 0.5, 4.0)
    assert (s["avg_r"], s["profit_factor"], s["max_drawdown_r"], s["avg_bars_held"]) == (1.0, 3.0, 2.0, 3.0)
    assert [p["r_cum"] for p in s["equity"]] == [2.0, 1.0, 0.0, 4.0]
    assert s["equity"][0]["time"] == "2025-01-02T00:00:00+00:00"
    assert s["monthly"] == [{"month": "2025-01", "r": 1.0}, {"month": "2025-02", "r": 3.0}]


def test_summarize_zero_trades():
    s = summarize(result([]))
    assert (s["trades"], s["win_rate"], s["total_r"], s["avg_r"], s["profit_factor"]) == (0, 0.0, 0.0, 0.0, None)
    assert (s["max_drawdown_r"], s["avg_bars_held"]) == (0.0, 0.0)
    assert s["equity"] == [] and s["monthly"] == []


def test_open_trades_do_not_count():
    s = summarize(result([trade(2), trade(None)]))
    assert (s["trades"], s["open_trades"], s["total_r"]) == (1, 1, 2.0)


def test_only_winners_has_no_profit_factor():
    assert summarize(result([trade(2), trade(1)]))["profit_factor"] is None


def test_skipped_are_counted():
    assert summarize(result([], skipped=["a", "b"]))["skipped"] == 2


def test_pick_examples_three_different_trades():
    trades = [trade(2, 1), trade(-1, 2), trade(-1, 3), trade(4, 9), trade(1, 2)]
    ex = pick_examples(trades, seed=1)
    assert ex["loss"].r < 0 and ex["win"].r > 0
    assert ex["long"].bars_held == 9
    assert len({id(t) for t in ex.values()}) == 3


def test_pick_examples_seed_is_repeatable_and_changes_the_pick():
    trades = [trade(r, i + 1) for i, r in enumerate([1, -1] * 20)]
    assert pick_examples(trades, 5) == pick_examples(trades, 5)
    picks = {id(pick_examples(trades, seed)["win"]) for seed in range(10)}
    assert len(picks) > 1


def test_pick_examples_ignores_open_trades():
    ex = pick_examples([trade(None, 50), trade(1, 2), trade(-1, 3)], 0)
    assert ex["long"].bars_held == 3 and ex["loss"] is None and ex["win"].r == 1


def test_pick_examples_empty():
    assert pick_examples([], 0) == {"loss": None, "win": None, "long": None}

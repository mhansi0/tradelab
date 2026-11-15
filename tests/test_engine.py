import pandas as pd
from conftest import make_candles

from tradelab.engine import run
from tradelab.strategy import validate

FLAT = (100, 100.5, 99.5, 100)  # open, high, low, close: touches neither stop 99 nor target 102


def candles(rows, signals=(0,)):
    """Hourly gold candles from (open, high, low, close) rows. `signals` marks bars with volume 1."""
    df = make_candles("2025-01-02 00:00", len(rows), "1h")
    df[["open", "high", "low", "close"]] = [[float(v) for v in row] for row in rows]
    df["volume"] = 0.0
    for bar, mark in (signals.items() if isinstance(signals, dict) else {s: 1 for s in signals}.items()):
        df.iloc[bar, df.columns.get_loc("volume")] = float(mark)
    return df


def strat(direction="long", stop="99", tp_r=2, entry_when=("volume == 1",), **extra):
    setup = {"name": "s", "direction": direction, "entry_when": list(entry_when), "stop": stop,
             "take_profit_r": tp_r, **extra}
    if "take_profit" in extra:
        del setup["take_profit_r"]
    strategy, errors = validate({"name": "t", "market": "GOLD", "timeframe": "1h", "setups": [setup]})
    assert errors == []
    return strategy


def only_trade(result):
    assert len(result.trades) == 1, result
    return result.trades[0]


def test_tp_gives_plus_r():
    t = only_trade(run(strat(), candles([FLAT, FLAT, (100, 102.5, 99.5, 102)])))
    assert (t.outcome, t.r, t.exit, t.bars_held) == ("tp", 2.0, 102.0, 2)
    assert (t.entry, t.stop, t.take_profit, t.direction, t.setup) == (100.0, 99.0, 102.0, "long", "s")
    assert t.signal_time == pd.Timestamp("2025-01-02 00:00", tz="UTC")
    assert t.entry_time == pd.Timestamp("2025-01-02 01:00", tz="UTC")
    assert t.exit_time == pd.Timestamp("2025-01-02 02:00", tz="UTC")


def test_sl_wins_when_both_hit_in_one_bar():
    t = only_trade(run(strat(), candles([FLAT, FLAT, (100, 103, 98.5, 100)])))
    assert (t.outcome, t.r, t.exit) == ("sl", -1.0, 99.0)


def test_gap_through_stop_exits_at_open():
    t = only_trade(run(strat(), candles([FLAT, FLAT, (97, 97.5, 96, 97)])))
    assert (t.outcome, t.exit, t.r) == ("sl", 97.0, -3.0)


def test_gap_through_target_exits_at_open():
    t = only_trade(run(strat(), candles([FLAT, FLAT, (104, 104.5, 103, 104)])))
    assert (t.outcome, t.exit, t.r) == ("tp", 104.0, 4.0)


def test_stop_can_be_hit_on_the_entry_bar():
    t = only_trade(run(strat(), candles([FLAT, (100, 100.5, 98, 99)])))
    assert (t.outcome, t.r, t.bars_held) == ("sl", -1.0, 1)


def test_entry_is_next_bar_open_no_lookahead():
    rows = [FLAT, (100.2, 100.5, 99.5, 100), FLAT, (100, 102.5, 99.5, 102)]
    a = run(strat(), candles(rows))
    later_changed = candles(rows)
    later_changed.iloc[2:, :4] *= 1.5
    b = run(strat(), later_changed)
    assert a.trades[0].entry == b.trades[0].entry == 100.2
    assert a.trades[0].entry_time == b.trades[0].entry_time


def test_signal_during_open_trade_is_ignored():
    result = run(strat(), candles([FLAT, FLAT, FLAT, (100, 102.5, 99.5, 102)], signals=(0, 1)))
    assert len(result.trades) == 1 and result.skipped == []


def test_signal_on_the_exit_bar_is_ignored():
    result = run(strat(), candles([FLAT, FLAT, (100, 102.5, 99.5, 102), FLAT, FLAT], signals=(0, 2)))
    assert len(result.trades) == 1


def test_signal_after_the_exit_opens_a_new_trade():
    rows = [FLAT, FLAT, (100, 102.5, 99.5, 102), FLAT, FLAT, FLAT]
    result = run(strat(), candles(rows, signals=(0, 3)))
    assert [t.outcome for t in result.trades] == ["tp", "open"]
    assert result.trades[1].entry_time == pd.Timestamp("2025-01-02 04:00", tz="UTC")


def test_entry_beyond_stop_is_skipped():
    result = run(strat(stop="101"), candles([FLAT, FLAT, FLAT]))
    assert result.trades == []
    assert [(s.setup, s.reason) for s in result.skipped] == [("s", "entry beyond stop")]
    assert result.skipped[0].signal_time == pd.Timestamp("2025-01-02 00:00", tz="UTC")


def test_stop_without_value_is_skipped():
    result = run(strat(stop="prev_day.low"), candles([FLAT, FLAT, FLAT]))
    assert result.trades == [] and result.skipped[0].reason == "stop not computable"


def test_signal_on_last_bar_is_ignored():
    result = run(strat(), candles([FLAT, FLAT], signals=(1,)))
    assert result.trades == [] and result.skipped == []


def test_trade_open_at_end():
    t = only_trade(run(strat(), candles([FLAT, FLAT, FLAT])))
    assert (t.outcome, t.r, t.exit, t.exit_time, t.bars_held) == ("open", None, None, None, 2)


def test_exit_when_closes_at_next_open():
    rows = [FLAT, FLAT, (100, 100.2, 99.6, 99.7), (99.9, 100, 99.5, 99.8), FLAT]
    t = only_trade(run(strat(exit_when=["close < 99.75"]), candles(rows)))
    assert (t.outcome, t.exit, t.bars_held) == ("exit", 99.9, 3)
    assert t.exit_time == pd.Timestamp("2025-01-02 03:00", tz="UTC")
    assert abs(t.r - (-0.1)) < 1e-9


def test_short_mirrors_long():
    t = only_trade(run(strat("short", stop="101"), candles([FLAT, FLAT, (100, 100.5, 97.5, 98)])))
    assert (t.outcome, t.r, t.exit, t.take_profit) == ("tp", 2.0, 98.0, 98.0)


def test_short_stop_and_gap():
    t = only_trade(run(strat("short", stop="101"), candles([FLAT, FLAT, (103, 104, 102, 103)])))
    assert (t.outcome, t.exit, t.r) == ("sl", 103.0, -3.0)


def test_take_profit_formula_and_entry_name():
    s = strat(stop="entry - 2", take_profit="entry + 3")
    t = only_trade(run(s, candles([FLAT, FLAT, (100, 103.5, 99.5, 103)])))
    assert (t.stop, t.take_profit, t.outcome, t.r) == (98.0, 103.0, "tp", 1.5)


def test_take_profit_on_the_wrong_side_is_skipped():
    result = run(strat(take_profit="entry - 1"), candles([FLAT, FLAT, FLAT]))
    assert result.trades == [] and result.skipped[0].reason == "take profit beyond entry"


def test_two_setups_long_and_short():
    long_setup = {"name": "up", "direction": "long", "entry_when": ["volume == 1"], "stop": "99",
                  "take_profit_r": 2}
    short_setup = {"name": "down", "direction": "short", "entry_when": ["volume == 2"], "stop": "101",
                   "take_profit_r": 2}
    strategy, errors = validate({"name": "t", "market": "GOLD", "timeframe": "1h",
                                 "setups": [long_setup, short_setup]})
    assert errors == []
    rows = [FLAT, FLAT, (100, 102.5, 99.5, 102), FLAT, FLAT, (100, 100.5, 97.5, 98)]
    result = run(strategy, candles(rows, signals={0: 1, 3: 2}))
    assert [(t.setup, t.direction, t.outcome) for t in result.trades] == [
        ("up", "long", "tp"), ("down", "short", "tp")]


def test_result_reports_the_data_it_used():
    data = candles([FLAT, FLAT, FLAT])
    result = run(strat(), data)
    assert (result.start, result.end, result.bars) == (data.index[0], data.index[-1], 3)


def test_no_candles_gives_an_empty_result():
    result = run(strat(), candles([FLAT]).iloc[:0])
    assert result.trades == [] and result.bars == 0 and result.start is None

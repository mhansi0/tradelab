import numpy as np
import pandas as pd
import pytest
from conftest import make_candles

from tradelab.strategy import build_env, explain, list_names, load, save, validate


def ramp(start: str, periods: int, freq: str):
    """Candles whose prices rise by 1 per bar, so every bar is different."""
    df = make_candles(start, periods, freq)
    step = np.arange(periods, dtype=float)
    df["open"] += step
    df["close"] += step + 0.5
    df["high"] += step + 1
    df["low"] += step - 1
    return df


def test_example_is_valid(example):
    s, errors = validate(example)
    assert errors == [] and s.setups[0].take_profit_r == 4


def test_unknown_name_is_reported(example):
    example["setups"][0]["entry_when"].append("foo > 1")
    s, errors = validate(example)
    assert s is None and any("foo > 1" in e for e in errors)


def test_attack_is_reported_not_run(example):
    example["setups"][0]["stop"] = "__import__('os').system('x')"
    _, errors = validate(example)
    assert len(errors) == 1


def test_needs_exactly_one_take_profit(example):
    example["setups"][0]["take_profit"] = "prev_day.low"
    assert validate(example)[1]
    del example["setups"][0]["take_profit_r"]
    assert validate(example)[1] == []
    del example["setups"][0]["take_profit"]
    assert validate(example)[1]


def test_indicator_may_not_shadow_reserved_name(example):
    example["indicators"]["close"] = {"type": "sma", "length": 5}
    assert validate(example)[1]


def test_entry_name_only_in_stop_and_take_profit(example):
    example["setups"][0]["entry_when"].append("entry > 0")
    assert validate(example)[1]
    example["setups"][0]["entry_when"].pop()
    example["setups"][0]["stop"] = "entry * 1.003"
    assert validate(example)[1] == []


def test_condition_must_be_true_or_false(example):
    example["setups"][0]["entry_when"].append("close")
    assert any("true or false" in e for e in validate(example)[1])


def test_stop_must_be_a_price(example):
    example["setups"][0]["stop"] = "close > open"
    assert any("price" in e for e in validate(example)[1])


def test_unknown_field_market_and_timezone_are_reported(example):
    example["market"] = "BITCOIN"
    assert validate(example)[1]
    example["market"] = "GOLD"
    example["timezone"] = "Mars/Olympus"
    assert validate(example)[1]
    example["timezone"] = "America/New_York"
    example["typo_field"] = 1
    assert validate(example)[1]


def test_sma_needs_a_length(example):
    example["indicators"]["slow"] = {"type": "sma"}
    assert validate(example)[1]


def test_name_must_have_letters(example):
    example["name"] = "../.."
    assert validate(example)[1]


def test_env_session_names(example):
    s, _ = validate(example)
    candles = ramp("2025-01-01 23:00", 48, "1h")
    env = build_env(s, candles)
    assert env["bar_of_day"].tolist()[:3] == [1, 2, 3] and env["bar_of_day"].iloc[24] == 1
    assert (env["first"]["high"].iloc[:24] == candles["high"].iloc[0]).all()
    assert (env["first"]["high"].iloc[24:] == candles["high"].iloc[24]).all()
    assert env["prev_day"]["close"].iloc[:24].isna().all()
    assert (env["prev_day"]["close"].iloc[24:] == candles["close"].iloc[23]).all()
    assert (env["prev_day"]["high"].iloc[24:] == candles["high"].iloc[:24].max()).all()
    assert env["rsi"].index.equals(candles.index)


def test_env_respects_session_override(example):
    example["timezone"], example["session_start"] = "UTC", "06:00"
    s, _ = validate(example)
    env = build_env(s, ramp("2025-01-01 23:00", 48, "1h"))
    assert env["bar_of_day"].iloc[7] == 1  # the 06:00 UTC candle


def test_gold_day_starts_at_18_new_york_so_sunday_is_part_of_monday(example):
    s, _ = validate(example)
    friday = ramp("2025-01-03 00:00", 22, "1h")       # until the Friday close, 17:00 New York
    monday = ramp("2025-01-05 23:00", 10, "1h")       # from the Sunday open, 18:00 New York
    candles = pd.concat([friday, monday])
    env = build_env(s, candles)
    assert env["bar_of_day"].iloc[22:25].tolist() == [1, 2, 3]
    assert (env["prev_day"]["close"].iloc[22:] == friday["close"].iloc[-1]).all()


def test_gold_day_follows_new_york_summer_time(example):
    s, _ = validate(example)
    env = build_env(s, ramp("2025-07-01 20:00", 6, "1h"))  # 18:00 New York is 22:00 UTC in summer
    assert env["bar_of_day"].tolist() == [1, 2, 1, 2, 3, 4]


def test_env_namespaces_for_macd_and_bollinger(example):
    example["indicators"]["macd"] = {"type": "macd"}
    example["indicators"]["bb"] = {"type": "bollinger", "length": 5}
    example["setups"][0]["entry_when"] = ["macd.hist > 0", "close > bb.upper"]
    s, errors = validate(example)
    assert errors == []
    env = build_env(s, ramp("2025-01-01 23:00", 48, "1h"))
    assert set(env["macd"]) == {"line", "signal", "hist"} and set(env["bb"]) == {"upper", "mid", "lower"}


def test_first_uses_first_available_bar(example):
    s, _ = validate(example)
    candles = ramp("2025-01-01 23:00", 24, "1h").iloc[3:]
    env = build_env(s, candles)
    assert (env["first"]["open"] == candles["open"].iloc[0]).all()
    assert env["bar_of_day"].iloc[0] == 1


def test_explain_lists_each_condition(example):
    s, _ = validate(example)
    env = build_env(s, ramp("2025-01-01 23:00", 48, "1h"))
    rows = explain(s.setups[0], env, env["close"].index[25])
    assert [r["expr"] for r in rows] == s.setups[0].entry_when
    assert rows[0] == {"expr": "bar_of_day == 2", "passed": True, "values": {"bar_of_day": 2}}
    assert rows[2]["passed"] is True and set(rows[2]["values"]) == {"close", "open"}
    assert set(rows[3]["values"]) == {"close", "first.high", "first.low"}
    assert all(isinstance(r["passed"], bool) for r in rows)


def test_explain_gives_none_for_missing_values(example):
    s, _ = validate(example)
    env = build_env(s, ramp("2025-01-01 23:00", 48, "1h"))
    rows = explain(s.setups[0], env, env["close"].index[1])
    assert rows[4] == {"expr": "rsi < 30", "passed": False, "values": {"rsi": None}}


def test_save_load_and_no_silent_overwrite(home, example):
    s, _ = validate(example)
    path = save(s)
    assert path == home / "strategies" / "goud-eerste-candle-short" / "strategy.json"
    assert load("goud-eerste-candle-short") == s
    assert load("Goud Eerste Candle Short") == s
    assert list_names() == ["goud-eerste-candle-short"]
    with pytest.raises(FileExistsError):
        save(s)
    save(s, overwrite=True)


def test_load_unknown_lists_existing(home, example):
    save(validate(example)[0])
    with pytest.raises(ValueError, match="No strategy named 'nope'.*goud-eerste-candle-short"):
        load("nope")

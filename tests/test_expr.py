import pandas as pd
import pytest

from tradelab.expr import ExprError, Namespace, evaluate, names_in

NAN = float("nan")
ENV = {
    "close": pd.Series([1.0, 3.0, 2.0]),
    "open": pd.Series([2.0, 2.0, 2.0]),
    "rsi": pd.Series([NAN, 25.0, 40.0]),
    "first": Namespace(high=pd.Series([5.0, 5.0, 5.0])),
}


def test_and_comparison():
    assert evaluate("close > open and rsi < 30", ENV).tolist() == [False, True, False]


def test_or_and_not():
    assert evaluate("close > open or not rsi < 30", ENV).tolist() == [True, True, True]


def test_arithmetic_and_namespace():
    assert evaluate("(first.high - close) / 2", ENV).tolist() == [2.0, 1.0, 1.5]


def test_unary_minus_and_numbers():
    assert evaluate("-close + 1.5", ENV).tolist() == [0.5, -1.5, -0.5]
    assert evaluate("2 * 3", ENV) == 6


def test_chained_comparison():
    assert evaluate("1.5 < close < 2.5", ENV).tolist() == [False, False, True]


def test_prev_and_crossover():
    assert evaluate("prev(close)", ENV).tolist()[1:] == [1.0, 3.0]
    assert evaluate("crossover(close, open)", ENV).tolist() == [False, True, False]
    assert evaluate("crossunder(close, open)", ENV).tolist() == [False, False, False]


def test_highest_and_lowest_include_current_bar():
    assert evaluate("highest(close, 2)", ENV).tolist()[1:] == [3.0, 3.0]
    assert evaluate("lowest(close, 2)", ENV).tolist()[1:] == [1.0, 2.0]


def test_min_max_abs_work_on_series():
    assert evaluate("max(close, open)", ENV).tolist() == [2.0, 3.0, 2.0]
    assert evaluate("min(close, open)", ENV).tolist() == [1.0, 2.0, 2.0]
    assert evaluate("abs(close - open)", ENV).tolist() == [1.0, 1.0, 0.0]


def test_nan_comparison_is_false():
    assert not evaluate("rsi < 30", ENV).iloc[0]
    assert not evaluate("rsi >= 30", ENV).iloc[0]
    assert evaluate("not rsi < 30", ENV).iloc[0]  # "not" of a false comparison is true, by design


def test_names_in():
    assert names_in("prev(close) > first.high and rsi < 30") == {"close", "first", "rsi"}


@pytest.mark.parametrize("bad", [
    "__import__('os').system('x')",
    "close.__class__",
    "close.values",
    "open('f')",
    "[c for c in close]",
    "lambda: 1",
    "close if rsi else open",
    "foo > 1",
    "close ** 2",
    "first.nope",
    "'text'",
    "close[0]",
    "prev(close, n=1, __x=2)",
    "close >",
    "",
])
def test_rejects_everything_else(bad):
    with pytest.raises(ExprError) as e:
        evaluate(bad, ENV)
    assert bad in str(e.value)


def test_names_in_rejects_bad_syntax():
    with pytest.raises(ExprError):
        names_in("close >")

import pandas as pd
import pytest

from tradelab.indicators import atr, bollinger, ema, macd, rsi, sma


def alternating(extra=()):
    closes = [100.0]
    for i in range(14):
        closes.append(closes[-1] + (1 if i % 2 == 0 else -1))
    for step in extra:
        closes.append(closes[-1] + step)
    return pd.Series(closes)


def test_sma():
    out = sma(pd.Series([1, 2, 3, 4, 5.0]), 3)
    assert out.tolist()[2:] == [2.0, 3.0, 4.0] and out[:2].isna().all()


def test_ema_matches_recursive_definition():
    out = ema(pd.Series([1.0, 2.0, 3.0]), 3)  # alpha = 0.5
    assert out.tolist() == [1.0, 1.5, 2.25]


def test_rsi_balanced_is_50():
    assert rsi(alternating(), 14).iloc[14] == pytest.approx(50.0)


def test_rsi_wilder_step():
    assert rsi(alternating(extra=[1]), 14).iloc[15] == pytest.approx(53.5714, abs=1e-3)


def test_rsi_only_gains_is_100():
    assert rsi(pd.Series(range(1, 30), dtype=float), 14).iloc[-1] == 100.0


def test_rsi_first_values_are_nan():
    assert rsi(pd.Series(range(1, 30), dtype=float), 14).iloc[:14].isna().all()


def test_rsi_short_length_by_hand():
    # changes -5, -12, +3 -> seed loss 8.5, then gain 1.5 / loss 4.25
    out = rsi(pd.Series([2005.0, 2000.0, 1988.0, 1991.0]), 2)
    assert out.iloc[2] == 0.0
    assert out.iloc[3] == pytest.approx(26.087, abs=1e-3)


def test_macd_hist_is_line_minus_signal():
    m = macd(pd.Series(range(1, 80), dtype=float))
    assert list(m.columns) == ["line", "signal", "hist"]
    assert ((m["line"] - m["signal"]) - m["hist"]).abs().max() < 1e-9


def test_bollinger_flat_series_has_zero_width():
    b = bollinger(pd.Series([5.0] * 30))
    assert b["upper"].iloc[-1] == b["lower"].iloc[-1] == b["mid"].iloc[-1] == 5.0


def test_atr_constant_range():
    df = pd.DataFrame({"high": [11.0] * 30, "low": [9.0] * 30, "close": [10.0] * 30})
    assert atr(df, 14).iloc[-1] == pytest.approx(2.0)

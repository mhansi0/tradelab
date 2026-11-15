import numpy as np
import pandas as pd


def sma(s: pd.Series, length: int) -> pd.Series:
    return s.rolling(length).mean()


def ema(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(span=length, adjust=False).mean()


def _wilder(values: pd.Series, length: int) -> pd.Series:
    """Wilder average: seeded with the plain mean of the first `length` values."""
    v = values.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    valid = np.flatnonzero(~np.isnan(v))
    if len(valid) and len(v) - valid[0] >= length:
        i = valid[0] + length - 1
        out[i] = v[valid[0]:i + 1].mean()
        for j in range(i + 1, len(v)):
            out[j] = (out[j - 1] * (length - 1) + v[j]) / length
    return pd.Series(out, index=values.index)


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = _wilder(delta.clip(lower=0), length)
    loss = _wilder(-delta.clip(upper=0), length)
    out = 100 * gain / (gain + loss)
    return out.mask((loss == 0) & gain.notna(), 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"line": line, "signal": sig, "hist": line - sig})


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift()
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return _wilder(true_range, length)


def bollinger(close: pd.Series, length: int = 20, mult: float = 2.0) -> pd.DataFrame:
    mid = sma(close, length)
    width = mult * close.rolling(length).std(ddof=0)
    return pd.DataFrame({"upper": mid + width, "mid": mid, "lower": mid - width})

import numpy as np
import pandas as pd
import pytest


def make_candles(start: str, periods: int, freq: str, price: float = 100.0) -> pd.DataFrame:
    """Flat candles at `price`, UTC index named `time`."""
    index = pd.date_range(start, periods=periods, freq=freq, tz="UTC", name="time")
    data = {c: np.full(periods, float(price)) for c in ("open", "high", "low", "close")}
    data["volume"] = np.full(periods, 1.0)
    return pd.DataFrame(data, index=index)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    return tmp_path

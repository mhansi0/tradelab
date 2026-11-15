import json
from pathlib import Path

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
def example() -> dict:
    """The maker's example strategy, a fresh copy per test."""
    path = Path(__file__).parent / "fixtures" / "gold_first_candle.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def chart_case(example):
    """(strategy, candles, env, trade): a closed short on 200 wavy hourly gold candles."""
    from tradelab.engine import Trade
    from tradelab.strategy import build_env, validate

    strategy, _ = validate(example)
    candles = make_candles("2025-01-02 00:00", 200, "1h")
    wave = 10 * np.sin(np.arange(200) / 9)
    candles["open"] += wave
    candles["close"] += wave + 0.5
    candles["high"] += wave + 1.5
    candles["low"] += wave - 1.0
    t = candles.index
    entry = float(candles["open"].iloc[101])
    trade = Trade("short-na-daling", "short", t[100], t[101], entry, entry + 2, entry - 8,
                  t[105], entry - 8, "tp", 4.0, 5)
    return strategy, candles, build_env(strategy, candles), trade


@pytest.fixture
def gold_data(home):
    """20 days of stored 5-minute gold candles on which the maker's example trades once a day.

    Every day opens with a 1% drop and a small bounce (the setup). On even days the price keeps
    falling (target hit), on odd days it jumps above the first candle (stop hit).
    """
    from tradelab.store import save_candles

    win_day = [0.99, 1.002] + [0.99] * 6 + [0.999] * 16
    loss_day = [0.99, 1.002, 1.012] + [0.998] * 21
    price, opens, closes = 2000.0, [], []
    for day in range(20):
        for factor in (win_day if day % 2 == 0 else loss_day):
            steps = np.linspace(price, price * factor, 13)  # 12 five-minute candles per hour
            opens.extend(steps[:-1])
            closes.extend(steps[1:])
            price *= factor
    candles = make_candles("2025-01-05 23:00", len(opens), "5min")  # Sunday 18:00 New York
    candles["open"], candles["close"] = opens, closes
    candles["high"] = candles[["open", "close"]].max(axis=1)
    candles["low"] = candles[["open", "close"]].min(axis=1)
    save_candles("GOLD", "5min", candles)
    return candles


@pytest.fixture
def never_triggers(example) -> dict:
    example["name"] = "never"
    example["setups"][0]["entry_when"] = ["close < 0"]
    return example


@pytest.fixture(autouse=True)  # every test gets its own storage, never the real ~/.tradelab
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADELAB_HOME", str(tmp_path))
    return tmp_path

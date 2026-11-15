"""The maker's example, worked out by hand and checked against the engine.

RSI(2) on the closes 2005, 2000, 1988, 1991: changes -5, -12, +3.
Seed after two changes: average gain 0, average loss 8.5. Then gain (0 + 3) / 2 = 1.5 and
loss (8.5 + 0) / 2 = 4.25, so RSI = 100 * 1.5 / 5.75 = 26.09.
Entry 1991 (short), stop 2001 (high of the first candle), R = 10, target 1991 - 4 * 10 = 1951.
"""

import pandas as pd

from tradelab.engine import run
from tradelab.strategy import validate

# The gold day starts at 18:00 New York, which is 23:00 UTC in winter.
ROWS = [("2025-01-02 21:00", 2010, 2011, 2004, 2005),
        ("2025-01-02 22:00", 2005, 2006, 1999, 2000),
        ("2025-01-02 23:00", 2000, 2001, 1986, 1988),   # first candle of the day: -0.6%
        ("2025-01-03 00:00", 1988, 1992, 1987, 1991),   # signal: closes higher, below the middle
        ("2025-01-03 01:00", 1991, 1992, 1985, 1986),   # entry at the open
        ("2025-01-03 02:00", 1986, 1987, 1960, 1962),
        ("2025-01-03 03:00", 1962, 1963, 1950, 1952)]   # target 1951 is hit


def test_paper_example(example):
    example["indicators"]["rsi"]["length"] = 2
    strategy, errors = validate(example)
    assert errors == []
    candles = pd.DataFrame(
        [row[1:] for row in ROWS], columns=["open", "high", "low", "close"], dtype=float,
        index=pd.DatetimeIndex([row[0] for row in ROWS], tz="UTC", name="time"))
    candles["volume"] = 0.0

    result = run(strategy, candles)

    assert result.skipped == []
    t, = result.trades
    assert t.signal_time == pd.Timestamp("2025-01-03 00:00", tz="UTC")
    assert t.entry_time == pd.Timestamp("2025-01-03 01:00", tz="UTC")
    assert (t.entry, t.stop, t.take_profit) == (1991.0, 2001.0, 1951.0)
    assert (t.outcome, t.exit, t.r, t.bars_held) == ("tp", 1951.0, 4.0, 3)
    assert t.exit_time == pd.Timestamp("2025-01-03 03:00", tz="UTC")

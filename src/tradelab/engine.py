"""The backtest. The simulation rules are listed in docs/strategy-format.md."""

from dataclasses import dataclass
from functools import reduce

import numpy as np
import pandas as pd

from .expr import evaluate
from .strategy import Setup, Strategy, build_env


@dataclass
class Trade:
    setup: str
    direction: str
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry: float
    stop: float
    take_profit: float
    exit_time: pd.Timestamp | None
    exit: float | None
    outcome: str  # tp | sl | exit | open
    r: float | None
    bars_held: int


@dataclass
class Skipped:
    setup: str
    signal_time: pd.Timestamp
    reason: str


@dataclass
class BacktestResult:
    trades: list[Trade]
    skipped: list[Skipped]
    start: pd.Timestamp | None
    end: pd.Timestamp | None
    bars: int


def _flags(formulas: list[str], env: dict, n: int) -> np.ndarray:
    """One true/false per candle: are all formulas true there."""
    if not formulas:
        return np.zeros(n, dtype=bool)
    parts = []
    for formula in formulas:
        value = evaluate(formula, env)
        value = value.fillna(False).to_numpy(dtype=bool) if isinstance(value, pd.Series) else bool(value)
        parts.append(np.broadcast_to(value, n))
    return reduce(np.logical_and, parts)


def _prices(formula: str, env: dict, n: int) -> np.ndarray:
    value = evaluate(formula, env)
    value = value.to_numpy(dtype=float) if isinstance(value, pd.Series) else float(value)
    return np.broadcast_to(value, n)


def run(strategy: Strategy, candles: pd.DataFrame, env: dict | None = None) -> BacktestResult:
    n = len(candles)
    if n == 0:
        return BacktestResult([], [], None, None, 0)
    env = env or build_env(strategy, candles)
    times = candles.index
    open_, high, low = (candles[c].to_numpy(dtype=float) for c in ("open", "high", "low"))

    # "entry" is the next candle's open. It is only handed to stop and take-profit formulas,
    # which are used at that open, so entry conditions cannot look ahead.
    price_env = {**env, "entry": candles["open"].shift(-1)}
    prepared: list[tuple[Setup, np.ndarray, np.ndarray, np.ndarray | None, np.ndarray]] = [
        (setup,
         _flags(setup.entry_when, env, n),
         _prices(setup.stop, price_env, n),
         _prices(setup.take_profit, price_env, n) if setup.take_profit else None,
         np.zeros(n, dtype=bool) if not setup.exit_when else reduce(
             np.logical_or, [_flags([formula], env, n) for formula in setup.exit_when]))
        for setup in strategy.setups]

    trades: list[Trade] = []
    skipped: list[Skipped] = []
    i = 0
    while i < n - 1:  # a signal on the last candle has no next open
        hit = next((p for p in prepared if p[1][i]), None)
        if hit is None:
            i += 1
            continue
        setup, _, stops, targets, exits = hit
        side = 1 if setup.direction == "long" else -1
        e = i + 1
        entry, stop = open_[e], stops[i]

        reason = None
        if np.isnan(stop):
            reason = "stop not computable"
        elif (entry - stop) * side <= 0:
            reason = "entry beyond stop"
        else:
            risk = abs(entry - stop)
            target = entry + side * setup.take_profit_r * risk if targets is None else targets[i]
            if np.isnan(target):
                reason = "take profit not computable"
            elif (target - entry) * side <= 0:
                reason = "take profit beyond entry"
        if reason:
            skipped.append(Skipped(setup.name, times[i], reason))
            i += 1
            continue

        outcome, exit_price, x = "open", None, n - 1
        for j in range(e, n):
            # worst and best price of the candle from the trade's point of view
            worst, best = (low[j], high[j]) if side == 1 else (high[j], low[j])
            if j > e and (open_[j] - stop) * side <= 0:
                outcome, exit_price, x = "sl", open_[j], j
            elif j > e and (open_[j] - target) * side >= 0:
                outcome, exit_price, x = "tp", open_[j], j
            elif (worst - stop) * side <= 0:  # checked before the target: the stop wins a tie
                outcome, exit_price, x = "sl", stop, j
            elif (best - target) * side >= 0:
                outcome, exit_price, x = "tp", target, j
            elif exits[j] and j + 1 < n:
                outcome, exit_price, x = "exit", open_[j + 1], j + 1
            else:
                continue
            break

        closed = outcome != "open"
        trades.append(Trade(
            setup=setup.name, direction=setup.direction,
            signal_time=times[i], entry_time=times[e],
            entry=float(entry), stop=float(stop), take_profit=float(target),
            exit_time=times[x] if closed else None,
            exit=float(exit_price) if closed else None,
            outcome=outcome,
            r=float((exit_price - entry) * side / risk) if closed else None,
            bars_held=x - e + 1))
        if not closed:
            break
        i = x + 1  # one position at a time: signals up to the exit candle are ignored
    return BacktestResult(trades, skipped, times[0], times[-1], n)

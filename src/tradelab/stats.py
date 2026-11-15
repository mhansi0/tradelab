import random

from .engine import BacktestResult, Trade


def summarize(result: BacktestResult) -> dict:
    """The numbers of a backtest. Only closed trades count."""
    closed = [t for t in result.trades if t.outcome != "open"]
    rs = [t.r for t in closed]
    gains = sum(r for r in rs if r > 0)
    losses = -sum(r for r in rs if r < 0)

    equity, monthly, total, peak, drawdown = [], {}, 0.0, 0.0, 0.0
    for t in closed:
        total += t.r
        peak = max(peak, total)
        drawdown = max(drawdown, peak - total)
        equity.append({"time": t.exit_time.isoformat(), "r_cum": round(total, 4)})
        month = t.exit_time.strftime("%Y-%m")
        monthly[month] = monthly.get(month, 0.0) + t.r

    n = len(closed)
    return {
        "trades": n,
        "wins": sum(r > 0 for r in rs),
        "losses": sum(r < 0 for r in rs),
        "win_rate": round(sum(r > 0 for r in rs) / n, 4) if n else 0.0,
        "total_r": round(total, 4),
        "avg_r": round(total / n, 4) if n else 0.0,
        "profit_factor": round(gains / losses, 4) if losses else None,
        "max_drawdown_r": round(drawdown, 4),
        "avg_bars_held": round(sum(t.bars_held for t in closed) / n, 2) if n else 0.0,
        "open_trades": len(result.trades) - n,
        "skipped": len(result.skipped),
        "equity": equity,
        "monthly": [{"month": month, "r": round(r, 4)} for month, r in monthly.items()],
    }


def pick_examples(trades: list[Trade], seed: int = 0) -> dict[str, Trade | None]:
    """Three different closed trades: the longest one, then a random loser and a random winner."""
    closed = [t for t in trades if t.outcome != "open"]
    longest = max(closed, key=lambda t: t.bars_held, default=None)
    rest = [t for t in closed if t is not longest]
    rng = random.Random(seed)
    losers, winners = [t for t in rest if t.r < 0], [t for t in rest if t.r > 0]
    return {
        "loss": rng.choice(losers) if losers else None,
        "win": rng.choice(winners) if winners else None,
        "long": longest,
    }

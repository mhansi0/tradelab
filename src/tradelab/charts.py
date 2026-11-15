"""Plotly figures for the report."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import indicators as ind
from .engine import Trade
from .strategy import Strategy

LABEL = "%Y-%m-%d %H:%M"
GREEN, RED, GREY = "#1a9d6c", "#d64545", "#7a8594"
LAYOUT = dict(template="plotly_white", margin=dict(l=50, r=20, t=50, b=40),
              font=dict(family="system-ui, sans-serif", size=13))


def equity_figure(summary: dict) -> go.Figure:
    points = summary["equity"]
    fig = go.Figure(go.Scatter(
        x=[p["time"] for p in points], y=[p["r_cum"] for p in points],
        mode="lines", line=dict(color="#2f6fde", width=2), name="Result"))
    return fig.update_layout(title="Result over time (R, added up)", height=380, **LAYOUT)


def monthly_figure(summary: dict) -> go.Figure:
    months = summary["monthly"]
    fig = go.Figure(go.Bar(
        x=[m["month"] for m in months], y=[m["r"] for m in months],
        marker_color=[GREEN if m["r"] >= 0 else RED for m in months], name="R per month"))
    return fig.update_layout(title="Result per month (R)", height=380, xaxis_type="category", **LAYOUT)


def distribution_figure(trades: list[Trade]) -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=[t.r for t in trades if t.r is not None], marker_color=GREY, name="Trades"))
    return fig.update_layout(title="How trades ended (R per trade)", height=380, **LAYOUT)


def trade_figure(
    strategy: Strategy,
    candles: pd.DataFrame,
    env: dict,
    trade: Trade,
    bars_before: int = 60,
    bars_after: int = 20,
) -> go.Figure:
    """One trade as on a trading screen: candles, setup, entry, stop and target zones, indicators."""
    signal_at = candles.index.get_loc(trade.signal_time)
    last_at = candles.index.get_loc(trade.exit_time) if trade.exit_time is not None else len(candles) - 1
    window = slice(max(0, signal_at - bars_before), min(len(candles), last_at + bars_after + 1))
    shown = candles.iloc[window]
    x = [t.strftime(LABEL) for t in shown.index]  # labels, not dates: nights and weekends leave no gap

    def line(series: pd.Series, name: str, row: int, **style):
        fig.add_trace(go.Scatter(x=x, y=series.reindex(shown.index), name=name, mode="lines",
                                 line=dict(width=1.3, **style)), row=row, col=1)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(
        x=x, open=shown["open"], high=shown["high"], low=shown["low"], close=shown["close"],
        name="Price", increasing_line_color=GREEN, decreasing_line_color=RED), row=1, col=1)

    close = candles["close"]
    line(ind.ema(close, 50), "EMA 50", 1, color="#e09f3e")
    line(ind.ema(close, 200), "EMA 200", 1, color="#7b5ea7")
    line(ind.rsi(close, 14), "RSI 14", 2, color="#2f6fde")
    macd = ind.macd(close)
    fig.add_trace(go.Bar(x=x, y=macd["hist"].reindex(shown.index), name="MACD hist",
                         marker_color=GREY), row=3, col=1)
    line(macd["line"], "MACD", 3, color="#2f6fde")
    line(macd["signal"], "MACD signal", 3, color="#e09f3e")

    # the strategy's own indicators, unless they are exactly the standard ones above
    for name, spec in strategy.indicators.items():
        if spec.type in ("sma", "ema") and (spec.type, spec.length) not in (("ema", 50), ("ema", 200)):
            line(env[name], f"{name} ({spec.type.upper()} {spec.length})", 1, dash="dot")
        elif spec.type == "bollinger":
            for band in ("upper", "mid", "lower"):
                line(env[name][band], f"{name} {band}", 1, dash="dot", color=GREY)
        elif spec.type == "rsi" and (spec.length or 14) != 14:
            line(env[name], f"{name} (RSI {spec.length})", 2, dash="dot")
        elif spec.type == "macd" and (spec.fast, spec.slow, spec.signal) != (12, 26, 9):
            line(env[name]["line"], f"{name} line", 3, dash="dot")
            line(env[name]["signal"], f"{name} signal", 3, dash="dot")

    entry_x = trade.entry_time.strftime(LABEL)
    end_x = trade.exit_time.strftime(LABEL) if trade.exit_time is not None else x[-1]
    for level, color in ((trade.stop, RED), (trade.take_profit, GREEN)):
        fig.add_shape(type="rect", x0=entry_x, x1=end_x, y0=trade.entry, y1=level, row=1, col=1,
                      fillcolor=color, opacity=0.18, line_width=0)

    def mark(text: str, at: pd.Timestamp, price: float):
        fig.add_annotation(x=at.strftime(LABEL), y=price, text=text, row=1, col=1, showarrow=True,
                           arrowhead=2, ax=0, ay=-34, bgcolor="white", bordercolor=GREY)

    signal_bar = candles.loc[trade.signal_time]
    mark("Setup", trade.signal_time, signal_bar["high"])
    mark("Entry", trade.entry_time, trade.entry)
    if trade.exit_time is not None:
        mark("Exit", trade.exit_time, trade.exit)

    fig.update_xaxes(type="category", nticks=8, rangeslider_visible=False)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    return fig.update_layout(height=760, legend=dict(orientation="h", y=1.06), **LAYOUT)

from dataclasses import replace

import pandas as pd
import plotly.graph_objects as go

from tradelab.charts import distribution_figure, equity_figure, monthly_figure, trade_figure
from tradelab.engine import BacktestResult
from tradelab.stats import summarize

EMPTY = BacktestResult([], [], None, None, 0)


def test_trade_figure_marks_setup_entry_and_zones(chart_case):
    strategy, candles, env, trade = chart_case
    fig = trade_figure(strategy, candles, env, trade)
    assert isinstance(fig.data[0], go.Candlestick)
    texts = [a.text for a in fig.layout.annotations]
    assert "Setup" in texts and "Entry" in texts and "Exit" in texts
    assert len(fig.layout.shapes) == 2
    names = {t.name for t in fig.data}
    assert {"EMA 50", "EMA 200", "RSI 14", "MACD"} <= names


def test_zones_run_from_entry_to_exit_between_entry_and_stop_or_target(chart_case):
    strategy, candles, env, trade = chart_case
    risk, reward = trade_figure(strategy, candles, env, trade).layout.shapes
    label = "%Y-%m-%d %H:%M"
    assert (risk.x0, risk.x1) == (trade.entry_time.strftime(label), trade.exit_time.strftime(label))
    assert {risk.y0, risk.y1} == {trade.entry, trade.stop}
    assert {reward.y0, reward.y1} == {trade.entry, trade.take_profit}


def test_trade_figure_window(chart_case):
    strategy, candles, env, trade = chart_case
    fig = trade_figure(strategy, candles, env, trade, bars_before=10, bars_after=5)
    assert len(fig.data[0].x) == 10 + 1 + trade.bars_held + 5
    assert fig.data[0].x[10] == trade.signal_time.strftime("%Y-%m-%d %H:%M")


def test_trade_figure_window_is_clipped_at_the_data_edges(chart_case):
    strategy, candles, env, trade = chart_case
    fig = trade_figure(strategy, candles.iloc[95:107], {k: v for k, v in env.items()}, trade)
    assert len(fig.data[0].x) == 12


def test_open_trade_has_no_exit_mark(chart_case):
    strategy, candles, env, trade = chart_case
    still_open = replace(trade, outcome="open", exit=None, exit_time=None, r=None)
    fig = trade_figure(strategy, candles, env, still_open)
    assert "Exit" not in [a.text for a in fig.layout.annotations]


def test_strategy_indicators_with_other_settings_are_drawn(chart_case, example):
    from tradelab.strategy import build_env, validate

    example["indicators"] = {"rsi": {"type": "rsi", "length": 7}, "fast": {"type": "ema", "length": 9},
                             "bb": {"type": "bollinger"}}
    strategy, errors = validate(example)
    assert errors == []
    _, candles, _, trade = chart_case
    names = {t.name for t in trade_figure(strategy, candles, build_env(strategy, candles), trade).data}
    assert {"rsi (RSI 7)", "fast (EMA 9)", "bb upper", "bb lower"} <= names


def test_summary_figures(chart_case):
    _, _, _, trade = chart_case
    summary = summarize(BacktestResult([trade], [], None, None, 200))
    assert list(equity_figure(summary).data[0].y) == [4.0]
    assert list(monthly_figure(summary).data[0].x) == ["2025-01"]
    assert list(distribution_figure([trade]).data[0].x) == [4.0]


def test_summary_figures_handle_zero_trades():
    summary = summarize(EMPTY)
    for fig in (equity_figure(summary), monthly_figure(summary), distribution_figure([])):
        assert isinstance(fig, go.Figure)


def test_times_are_labels_so_weekends_leave_no_gap(chart_case):
    strategy, candles, env, trade = chart_case
    fig = trade_figure(strategy, candles, env, trade)
    assert fig.layout.xaxis.type == "category"
    assert isinstance(fig.data[0].x[0], str) and pd.Timestamp(fig.data[0].x[0])

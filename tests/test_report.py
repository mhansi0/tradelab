import pytest

from tradelab.charts import distribution_figure, equity_figure, monthly_figure, trade_figure
from tradelab.engine import BacktestResult
from tradelab.report import DISCLAIMER, build, write
from tradelab.stats import summarize
from tradelab.strategy import explain

RANGE = ("2021-01-01", "2025-12-31")


@pytest.fixture
def parts(chart_case):
    strategy, candles, env, trade = chart_case
    summary = summarize(BacktestResult([trade], [], None, None, 200))
    figures = {"equity": equity_figure(summary), "monthly": monthly_figure(summary),
               "distribution": distribution_figure([trade])}
    trade_dict = {
        "setup": trade.setup, "direction": trade.direction,
        "signal_time": trade.signal_time.isoformat(), "entry_time": trade.entry_time.isoformat(),
        "entry": trade.entry, "stop": trade.stop, "take_profit": trade.take_profit,
        "exit_time": trade.exit_time.isoformat(), "exit": trade.exit, "outcome": "tp", "r": 4.0,
        "bars_held": 5}
    examples = [{"kind": "win", "trade": trade_dict,
                 "conditions": explain(strategy.setups[0], env, trade.signal_time),
                 "figure": trade_figure(strategy, candles, env, trade)}]
    return strategy, summary, examples, figures


def test_report_contains_everything(parts):
    strategy, summary, examples, figures = parts
    html = build(strategy, summary, examples, figures, "Why it lost.\n\nWhy it won.", RANGE)
    assert html.count(DISCLAIMER) == 1 and DISCLAIMER.startswith("Not financial advice.")
    assert html.count("cdnjs.cloudflare.com/ajax/libs/plotly.js") == 1
    assert "bar_of_day == 2" in html and "<p>Why it won.</p>" in html
    assert "goud-eerste-candle-short" in html and "A winning trade" in html
    assert "2021-01-01" in html and "2025-12-31" in html
    assert html.count('class="plotly-graph-div"') == 4
    assert 'name="viewport"' in html and html.lstrip().lower().startswith("<!doctype html>")


def test_report_shows_the_numbers_and_condition_values(parts):
    strategy, summary, examples, figures = parts
    html = build(strategy, summary, examples, figures, "", RANGE)
    assert "100%" in html  # win rate of the single winning trade
    assert "+4.00R" in html
    assert "first.high" in html and "rsi &lt; 30" in html


def test_report_escapes_commentary_and_strategy_text(parts):
    strategy, summary, examples, figures = parts
    nasty = strategy.model_copy(update={"description": "<img src=x onerror=alert(2)>"})
    html = build(nasty, summary, examples, figures, "<script>alert(1)</script>", RANGE)
    assert "<script>alert(1)</script>" not in html and "<img src=x" not in html


def test_report_without_trades(parts):
    strategy, _, _, _ = parts
    summary = summarize(BacktestResult([], [], None, None, 0))
    figures = {"equity": equity_figure(summary), "monthly": monthly_figure(summary),
               "distribution": distribution_figure([])}
    html = build(strategy, summary, [], figures, "", RANGE)
    assert "No trades" in html and "plotly-graph-div" not in html


def test_report_mentions_the_silver_proxy(parts):
    strategy, summary, examples, figures = parts
    silver = strategy.model_copy(update={"market": "SILVER"})
    assert "Proxy" in build(silver, summary, examples, figures, "", RANGE)
    assert "Proxy" not in build(strategy, summary, examples, figures, "", RANGE)


def test_write_puts_report_in_strategy_dir(home):
    path = write("Goud Eerste Candle Short", "<html></html>")
    assert path == home / "strategies" / "goud-eerste-candle-short" / "report.html"
    assert path.read_text(encoding="utf-8") == "<html></html>"

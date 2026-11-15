"""The backtest report: one HTML file with numbers, charts, three example trades and an explanation."""

from html import escape
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs_version

from .markets import get_market
from .paths import strategy_dir
from .strategy import Strategy

DISCLAIMER = ("Not financial advice. This tool explains backtests and past trades for learning "
              "purposes. It does not tell you what to buy or sell.")
KIND_TITLES = {"loss": "A losing trade", "win": "A winning trade", "long": "The longest trade"}
OUTCOMES = {"tp": "take profit hit", "sl": "stop loss hit", "exit": "closed by the exit rule",
            "open": "still open at the end of the data"}

CSS = """
:root { color-scheme: light; }
body { margin: 0; background: #f6f7f9; color: #1c2330; font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { margin: 0 0 4px; font-size: 1.7rem; } h2 { margin: 40px 0 12px; font-size: 1.25rem; }
h3 { margin: 28px 0 8px; font-size: 1.05rem; }
.muted { color: #5b6675; } .note { background: #fff7e0; border-radius: 8px; padding: 10px 14px; }
.card { background: #fff; border: 1px solid #e1e5ea; border-radius: 10px; padding: 16px; margin: 12px 0;
        overflow-x: auto; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.tile { background: #fff; border: 1px solid #e1e5ea; border-radius: 10px; padding: 12px 14px; }
.tile b { display: block; font-size: 1.35rem; } .tile span { color: #5b6675; font-size: .85rem; }
table { border-collapse: collapse; width: 100%; font-size: .93rem; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #e9ecf0; vertical-align: top; }
code { font: .9em ui-monospace, Consolas, monospace; background: #eef1f4; padding: 1px 5px; border-radius: 4px; }
.yes { color: #1a7f58; font-weight: 600; } .no { color: #c0392b; font-weight: 600; }
ul { padding-left: 20px; margin: 6px 0; }
"""


def _r(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.2f}R"


def _number(value) -> str:
    if value is None:
        return "not available yet"
    return f"{value:,.4f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def _chart(fig: go.Figure) -> str:
    inner = fig.to_html(full_html=False, include_plotlyjs=False,
                        config={"responsive": True, "displaylogo": False})
    return f'<div class="card">{inner}</div>'


def _rules(strategy: Strategy) -> str:
    parts = []
    for setup in strategy.setups:
        target = f"{setup.take_profit_r:g}R" if setup.take_profit is None else f"<code>{escape(setup.take_profit)}</code>"
        conditions = "".join(f"<li><code>{escape(c)}</code></li>" for c in setup.entry_when)
        exits = "".join(f"<li><code>{escape(c)}</code></li>" for c in setup.exit_when)
        parts.append(
            f"<h3>{escape(setup.name)} ({setup.direction})</h3>"
            f"<p>Enter at the next open when all of these are true:</p><ul>{conditions}</ul>"
            f"<p>Stop loss: <code>{escape(setup.stop)}</code>. Take profit: {target}.</p>"
            + (f"<p>Close early when one of these is true:</p><ul>{exits}</ul>" if exits else ""))
    return "".join(parts)


def _tiles(summary: dict) -> str:
    factor = summary["profit_factor"]
    tiles = [
        (summary["trades"], "closed trades"),
        (f"{summary['win_rate']:.0%}", "win rate"),
        (_r(summary["total_r"]), "total result"),
        (_r(summary["avg_r"]), "average per trade"),
        ("n/a" if factor is None else f"{factor:.2f}", "profit factor"),
        (f"-{summary['max_drawdown_r']:.2f}R", "largest drawdown"),
        (f"{summary['avg_bars_held']:g}", "average candles in a trade"),
        (f"{summary['skipped']} / {summary['open_trades']}", "skipped signals / still open"),
    ]
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><b>{escape(str(value))}</b><span>{label}</span></div>'
        for value, label in tiles) + "</div>"


def _example(example: dict) -> str:
    trade = example["trade"]
    rows = "".join(
        "<tr><td><code>{}</code></td><td class=\"{}\">{}</td><td>{}</td></tr>".format(
            escape(c["expr"]), "yes" if c["passed"] else "no", "Yes" if c["passed"] else "No",
            escape(", ".join(f"{name} = {_number(value)}" for name, value in c["values"].items())))
        for c in example["conditions"])
    exit_text = (f"{_number(trade['exit'])} at {escape(trade['exit_time'][:16].replace('T', ' '))}"
                 if trade["exit_time"] else "not yet")
    facts = [
        ("Setup", f"{escape(trade['setup'])} ({trade['direction']})"),
        ("Signal candle", escape(trade["signal_time"][:16].replace("T", " ")) + " UTC"),
        ("Entry", f"{_number(trade['entry'])} at {escape(trade['entry_time'][:16].replace('T', ' '))}"),
        ("Stop loss", _number(trade["stop"])),
        ("Take profit", _number(trade["take_profit"])),
        ("Exit", exit_text),
        ("Outcome", f"{OUTCOMES[trade['outcome']]}, {_r(trade['r'])}"),
        ("Candles in the trade", trade["bars_held"]),
    ]
    facts_html = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in facts)
    return (
        f"<h3>{KIND_TITLES[example['kind']]}</h3>{_chart(example['figure'])}"
        f'<div class="card"><table>{facts_html}</table></div>'
        '<div class="card"><table><tr><th>Entry condition on the signal candle</th><th>True?</th>'
        f"<th>Values</th></tr>{rows}</table></div>")


def build(
    strategy: Strategy,
    summary: dict,
    examples: list[dict],
    figures: dict[str, go.Figure],
    commentary: str,
    data_range: tuple[str, str],
) -> str:
    market = get_market(strategy.market)
    has_trades = summary["trades"] > 0
    note = f'<p class="note">{escape(market.note)}</p>' if market.note else ""
    paragraphs = "".join(f"<p>{escape(p.strip())}</p>" for p in commentary.split("\n\n") if p.strip())

    if has_trades:
        results = (_tiles(summary) + _chart(figures["equity"]) + _chart(figures["monthly"])
                   + _chart(figures["distribution"]))
    else:
        results = (_tiles(summary) + '<p class="note">No trades. The entry conditions were never all '
                   "true on the same candle in this period.</p>")
    script = (f'<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/{get_plotlyjs_version()}'
              '/plotly.min.js"></script>') if has_trades else ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(strategy.name)} backtest</title>
<style>{CSS}</style>
{script}
</head>
<body><main>
<h1>{escape(strategy.name)}</h1>
<p class="muted">{escape(market.label)}, {strategy.timeframe} candles, {escape(data_range[0])} to {escape(data_range[1])} (UTC)</p>
<p class="note">{DISCLAIMER}</p>
{note}
<h2>The strategy</h2>
<div class="card"><p>{escape(strategy.description) or "No description."}</p>{_rules(strategy)}</div>
<h2>Results</h2>
<p class="muted">R is the risk of one trade: the distance between entry and stop loss. +2R means the
trade made twice what it risked. No costs or slippage are included.</p>
{results}
{"<h2>Three example trades</h2>" + "".join(_example(e) for e in examples) if examples else ""}
{"<h2>Explanation</h2><div class='card'>" + paragraphs + "</div>" if paragraphs else ""}
</main></body>
</html>
"""


def write(name: str, html: str) -> Path:
    path = strategy_dir(name) / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path

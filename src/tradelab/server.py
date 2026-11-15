"""The MCP server: what Claude can call. The tools are thin, the work is in the other modules."""

import json

import pandas as pd
from mcp.server.mcpserver import MCPServer

from . import charts, report, store
from . import strategy as strategies
from .engine import run
from .markets import MARKETS, get_market
from .paths import slugify, strategy_dir
from .stats import pick_examples, summarize

server = MCPServer(
    "tradelab",
    instructions=(
        "Backtest trading strategies on locally stored candles. Translate the user's words into the "
        "strategy format, validate, show the translation, save, backtest, then build the report. "
        "Explain results, never advise what to buy or sell."))

FEW_TRADES = 30


def _when(text: str | None) -> pd.Timestamp | None:
    if text is None:
        return None
    try:
        stamp = pd.Timestamp(text)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot read the date '{text}'. Use a date like 2024-01-31.") from None
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def _backtest(strategy: strategies.Strategy, start: str | None, end: str | None, seed: int) -> dict:
    """Run the backtest and gather everything the tools and the report need."""
    timezone, session_start = strategy.session()
    from_, until = _when(start), _when(end)
    candles = store.load_candles(strategy.market, strategy.timeframe, from_, until, timezone, session_start)
    env = strategies.build_env(strategy, candles)
    result = run(strategy, candles, env)
    summary = summarize(result)

    warnings = []
    if candles.empty:
        warnings.append("There are no candles in this period.")
    else:
        if from_ is not None and candles.index[0] - from_ > pd.Timedelta(days=5):
            warnings.append(f"The stored data starts at {candles.index[0].date()}, later than the requested start.")
        if until is not None and until - candles.index[-1] > pd.Timedelta(days=5):
            warnings.append(f"The stored data ends at {candles.index[-1].date()}, earlier than the requested end.")
    if 0 < summary["trades"] < FEW_TRADES:
        warnings.append(f"Only {summary['trades']} trades: too few to draw firm conclusions.")
    note = get_market(strategy.market).note
    if note:
        warnings.append(note)

    examples = []
    for kind, trade in pick_examples(result.trades, seed).items():
        if trade is not None:
            setup = next(s for s in strategy.setups if s.name == trade.setup)
            examples.append({"kind": kind, "trade": trade,
                             "conditions": strategies.explain(setup, env, trade.signal_time)})
    data_range = [] if candles.empty else [str(candles.index[0].date()), str(candles.index[-1].date())]
    return {"candles": candles, "env": env, "result": result, "summary": summary,
            "examples": examples, "warnings": warnings, "data_range": data_range}


@server.tool()
def data_status() -> list[dict]:
    """Which markets exist and which candles are stored locally (per market: 1min and 5min files with
    first and last time). Empty `data` means the user still has to run `uv run tradelab download`."""
    stored = store.status()
    return [{"market": key, "label": m.label, "note": m.note,
             "data": [row for row in stored if row["market"] == key]} for key, m in MARKETS.items()]


@server.tool()
def validate_strategy(strategy: dict) -> dict:
    """Check a strategy in the tradelab format without saving it. Returns ok, a list of errors
    (each names the field and the formula) and the normalized strategy."""
    checked, errors = strategies.validate(strategy)
    return {"ok": not errors, "errors": errors,
            "strategy": checked.model_dump() if checked else None}


@server.tool()
def save_strategy(strategy: dict, overwrite: bool = False) -> dict:
    """Validate and store a strategy under its name. Refuses to replace an existing strategy unless
    overwrite is true. Ask the user before overwriting."""
    checked, errors = strategies.validate(strategy)
    if errors:
        raise ValueError("Invalid strategy:\n- " + "\n- ".join(errors))
    path = strategies.save(checked, overwrite)
    return {"name": path.parent.name, "path": str(path)}


@server.tool()
def list_strategies() -> list[dict]:
    """All stored strategies with their market, timeframe and whether a backtest exists."""
    rows = []
    for name in strategies.list_names():
        s = strategies.load(name)
        rows.append({"name": name, "market": s.market, "timeframe": s.timeframe,
                     "has_backtest": (strategy_dir(name) / "backtest.json").exists()})
    return rows


@server.tool()
def get_strategy(name: str) -> dict:
    """A stored strategy with the numbers of its last backtest and the path of its report
    (both null when there is none yet)."""
    s = strategies.load(name)
    folder = strategy_dir(name)
    backtest, report_file = folder / "backtest.json", folder / "report.html"
    return {
        "strategy": s.model_dump(),
        "summary": json.loads(backtest.read_text(encoding="utf-8"))["summary"] if backtest.exists() else None,
        "report_path": str(report_file) if report_file.exists() else None,
    }


@server.tool()
def run_backtest(name: str, start: str | None = None, end: str | None = None, seed: int = 0) -> dict:
    """Backtest a stored strategy on the local candles. start and end are dates like 2024-01-31
    (end is exclusive), left out means all stored data. Returns the numbers (in R, the risk per
    trade), up to three example trades (a loss, a win, the longest) with every entry condition and
    its values on the signal candle, and warnings. Another seed picks other example trades."""
    s = strategies.load(name)
    run_ = _backtest(s, start, end, seed)
    examples = [{**e, "trade": e["trade"].as_dict()} for e in run_["examples"]]
    out = {"summary": run_["summary"], "examples": examples, "data_range": run_["data_range"],
           "warnings": run_["warnings"]}
    saved = {**out, "trades": [t.as_dict() for t in run_["result"].trades],
             "seed": seed, "start": start, "end": end}
    (strategy_dir(name) / "backtest.json").write_text(json.dumps(saved, indent=1), encoding="utf-8")
    return out


@server.tool()
def build_report(name: str, commentary: str) -> dict:
    """Write the HTML report for the last backtest of a strategy: numbers, charts, the example
    trades on a chart, and your explanation. `commentary` is plain text, paragraphs separated by an
    empty line. Returns the path of report.html."""
    s = strategies.load(name)
    backtest = strategy_dir(name) / "backtest.json"
    if not backtest.exists():
        raise ValueError(f"No backtest for '{slugify(name)}' yet. Call run_backtest first.")
    last = json.loads(backtest.read_text(encoding="utf-8"))
    run_ = _backtest(s, last["start"], last["end"], last["seed"])
    examples = [{**e, "trade": e["trade"].as_dict(),
                 "figure": charts.trade_figure(s, run_["candles"], run_["env"], e["trade"])}
                for e in run_["examples"]]
    figures = {"equity": charts.equity_figure(run_["summary"]),
               "monthly": charts.monthly_figure(run_["summary"]),
               "distribution": charts.distribution_figure(run_["result"].trades)}
    data_range = tuple(run_["data_range"]) or ("no data", "no data")
    html = report.build(s, run_["summary"], examples, figures, commentary, data_range)
    return {"path": str(report.write(name, html))}


def main() -> None:
    server.run()

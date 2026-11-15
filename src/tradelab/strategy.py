"""A strategy as fixed rules. The format is described in docs/strategy-format.md."""

from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import indicators as ind
from .expr import FUNCTIONS, ExprError, Namespace, evaluate, names_in, refs_in
from .markets import TIMEFRAMES, get_market, session_keys
from .paths import home, slugify, strategy_dir

OHLC = ("open", "high", "low", "close")
RESERVED = {*OHLC, "volume", "bar_of_day", "first", "prev_day", "entry", *FUNCTIONS}
DEFAULT_LENGTH = {"rsi": 14, "atr": 14, "bollinger": 20}


class IndicatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["sma", "ema", "rsi", "macd", "atr", "bollinger"]
    length: int | None = Field(None, ge=1, le=5000)
    source: Literal["open", "high", "low", "close"] = "close"
    fast: int = Field(12, ge=1, le=5000)
    slow: int = Field(26, ge=1, le=5000)
    signal: int = Field(9, ge=1, le=5000)
    mult: float = Field(2.0, gt=0)

    @model_validator(mode="after")
    def _length_where_needed(self):
        if self.type in ("sma", "ema") and self.length is None:
            raise ValueError(f"indicator type '{self.type}' needs a length")
        return self


class Setup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    direction: Literal["long", "short"]
    entry_when: list[str] = Field(min_length=1)
    stop: str
    take_profit_r: float | None = Field(None, gt=0)
    take_profit: str | None = None
    exit_when: list[str] = []

    @model_validator(mode="after")
    def _one_take_profit(self):
        if (self.take_profit_r is None) == (self.take_profit is None):
            raise ValueError("give exactly one of take_profit_r and take_profit")
        return self


class Strategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    market: Literal["SP500", "NAS100", "GOLD", "SILVER"]
    timeframe: Literal["1min", "5min", "15min", "30min", "1h", "4h", "1day"]
    timezone: str | None = None
    session_start: str | None = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    indicators: dict[str, IndicatorSpec] = {}
    setups: list[Setup] = Field(min_length=1)

    def session(self) -> tuple[str, str]:
        """(timezone, session_start), the strategy's own or else the market's."""
        market = get_market(self.market)
        return self.timezone or market.timezone, self.session_start or market.session_start


def build_env(strategy: Strategy, candles: pd.DataFrame) -> dict[str, Any]:
    """Every name a formula may use, as series aligned to the candles."""
    env: dict[str, Any] = {column: candles[column] for column in (*OHLC, "volume")}
    session = session_keys(candles.index, *strategy.session())["session"].to_numpy()
    by_day = candles.groupby(session)
    env["bar_of_day"] = by_day.cumcount() + 1
    # known from the close of the day's first bar on, so no formula can look ahead with it
    env["first"] = Namespace({c: by_day[c].transform("first") for c in OHLC})
    daily = by_day.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                       close=("close", "last")).shift(1)
    env["prev_day"] = Namespace(
        {c: pd.Series(daily[c].reindex(session).to_numpy(), index=candles.index) for c in OHLC})

    for name, spec in strategy.indicators.items():
        source = candles[spec.source]
        length = spec.length or DEFAULT_LENGTH.get(spec.type)
        if spec.type == "sma":
            env[name] = ind.sma(source, length)
        elif spec.type == "ema":
            env[name] = ind.ema(source, length)
        elif spec.type == "rsi":
            env[name] = ind.rsi(source, length)
        elif spec.type == "atr":
            env[name] = ind.atr(candles, length)
        elif spec.type == "macd":
            env[name] = Namespace(ind.macd(source, spec.fast, spec.slow, spec.signal).to_dict("series"))
        elif spec.type == "bollinger":
            env[name] = Namespace(ind.bollinger(source, length, spec.mult).to_dict("series"))
    return env


def _sample_candles(strategy: Strategy) -> pd.DataFrame:
    """60 made-up candles, only to check that every formula can be calculated."""
    index = pd.date_range("2024-01-02", periods=60, freq=f"{TIMEFRAMES[strategy.timeframe]}min",
                          tz="UTC", name="time")
    close = 100 + 5 * np.sin(np.arange(60) / 7)
    return pd.DataFrame({"open": close - 0.2, "high": close + 1, "low": close - 1, "close": close,
                         "volume": 1.0}, index=index)


def _is_bool(value: Any) -> bool:
    return value.dtype == bool if isinstance(value, pd.Series) else isinstance(value, (bool, np.bool_))


def validate(raw: dict) -> tuple[Strategy | None, list[str]]:
    """Check shape, names and every formula. Returns (strategy, []) or (None, errors)."""
    try:
        strategy = Strategy.model_validate(raw)
    except ValidationError as error:
        return None, [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]

    errors: list[str] = []
    try:
        slugify(strategy.name)
    except ValueError as error:
        errors.append(f"name: {error}")
    if strategy.timezone:
        try:
            ZoneInfo(strategy.timezone)
        except (KeyError, ValueError):
            errors.append(f"timezone: unknown time zone '{strategy.timezone}'")
    for name in strategy.indicators:
        if not name.isidentifier() or name.startswith("_") or name in RESERVED:
            errors.append(f"indicators.{name}: this name is reserved or not a plain word")
    if errors:
        return None, errors

    env = build_env(strategy, _sample_candles(strategy))
    price_env = {**env, "entry": env["close"]}
    for setup in strategy.setups:
        where = f"setups.{setup.name}"
        for field, formulas in (("entry_when", setup.entry_when), ("exit_when", setup.exit_when)):
            for formula in formulas:
                try:
                    if "entry" in names_in(formula):
                        raise ExprError(f"'entry' only exists in stop and take_profit, not in: {formula}")
                    if not _is_bool(evaluate(formula, env)):
                        raise ExprError(f"A condition must be true or false, this is a number: {formula}")
                except ExprError as error:
                    errors.append(f"{where}.{field}: {error}")
        for field, formula in (("stop", setup.stop), ("take_profit", setup.take_profit)):
            if formula is None:
                continue
            try:
                if _is_bool(evaluate(formula, price_env)):
                    raise ExprError(f"This must be a price, not true or false: {formula}")
            except ExprError as error:
                errors.append(f"{where}.{field}: {error}")
    return (None, errors) if errors else (strategy, [])


def _value_at(env: dict, ref: str, at: pd.Timestamp):
    group, _, field = ref.partition(".")
    series = env[group][field] if field else env[group]
    value = series.loc[at]
    return None if pd.isna(value) else value.item()


def explain(setup: Setup, env: dict, at: pd.Timestamp) -> list[dict]:
    """Per entry condition at one candle: did it hold, and with which values."""
    rows = []
    for formula in setup.entry_when:
        result = evaluate(formula, env)
        passed = result.loc[at] if isinstance(result, pd.Series) else result
        rows.append({
            "expr": formula,
            "passed": bool(passed),
            "values": {ref: _value_at(env, ref, at) for ref in sorted(refs_in(formula))},
        })
    return rows


def _file(name: str) -> Path:
    return strategy_dir(name) / "strategy.json"


def list_names() -> list[str]:
    root = home() / "strategies"
    return sorted(p.parent.name for p in root.glob("*/strategy.json"))


def save(strategy: Strategy, overwrite: bool = False) -> Path:
    path = _file(strategy.name)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"A strategy named '{path.parent.name}' already exists. Pick another name or overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(strategy.model_dump_json(indent=2), encoding="utf-8")
    return path


def load(name: str) -> Strategy:
    path = _file(name)
    if not path.exists():
        existing = ", ".join(list_names()) or "none yet"
        raise ValueError(f"No strategy named '{name}'. Existing strategies: {existing}")
    return Strategy.model_validate_json(path.read_text(encoding="utf-8"))

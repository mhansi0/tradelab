# Strategy format

A strategy is a JSON object with fixed fields. Conditions and prices are short formulas. tradelab never runs code from a strategy: a formula can only use the names and functions listed here.

## Example

"If the first 1-hour candle of the day on gold drops more than 0.5% and the next candle closes higher but below the middle of the first candle, with RSI below 30, go short. Stop above the first candle, take profit at 4R."

```json
{
  "name": "goud-eerste-candle-short",
  "description": "The user's own words go here, unchanged.",
  "market": "GOLD",
  "timeframe": "1h",
  "indicators": {"rsi": {"type": "rsi", "length": 14}},
  "setups": [{
    "name": "short-na-daling",
    "direction": "short",
    "entry_when": [
      "bar_of_day == 2",
      "(first.close - first.open) / first.open < -0.005",
      "close > open",
      "close < (first.high + first.low) / 2",
      "rsi < 30"
    ],
    "stop": "first.high",
    "take_profit_r": 4
  }]
}
```

## Fields

| Field | Meaning |
|---|---|
| `name` | Name to find the strategy again. Letters, digits and dashes are kept. |
| `description` | The user's original text. |
| `market` | `SP500`, `NAS100`, `GOLD` or `SILVER`. |
| `timeframe` | `1min`, `5min`, `15min`, `30min`, `1h`, `4h` or `1day`. |
| `timezone`, `session_start` | Optional. When the trading day starts, for example `"America/New_York"` and `"09:30"`. Left out: the market's own (`GOLD`: 00:00 UTC, the others: 09:30 New York). |
| `indicators` | Named indicators, see below. The name is what formulas use. |
| `setups` | One or more setups. Use two setups for a strategy that trades long and short. |

### A setup

| Field | Meaning |
|---|---|
| `name` | Short name of the setup. |
| `direction` | `long` or `short`. |
| `entry_when` | List of conditions. All must be true on the same candle. That candle is the signal. |
| `stop` | Formula for the stop-loss price, calculated on the signal candle. |
| `take_profit_r` | Take profit as a multiple of R. R is the distance between entry and stop. |
| `take_profit` | Or: a formula for the take-profit price. Give exactly one of the two. |
| `exit_when` | Optional list of conditions. If one is true at a candle's close, the trade closes at the next open. |

### Indicators

| `type` | Settings (defaults) | Use in a formula |
|---|---|---|
| `sma` | `length` (required), `source` (`close`) | `name` |
| `ema` | `length` (required), `source` (`close`) | `name` |
| `rsi` | `length` (14), `source` (`close`) | `name` |
| `atr` | `length` (14) | `name` |
| `macd` | `fast` (12), `slow` (26), `signal` (9) | `name.line`, `name.signal`, `name.hist` |
| `bollinger` | `length` (20), `mult` (2.0) | `name.upper`, `name.mid`, `name.lower` |

`source` is `open`, `high`, `low` or `close`. Indicators are calculated on the strategy's own timeframe.

## Formulas

### Names

| Name | Meaning |
|---|---|
| `open`, `high`, `low`, `close`, `volume` | The current candle. |
| `bar_of_day` | 1 for the first candle of the trading day, 2 for the second, and so on. |
| `first.open`, `first.high`, `first.low`, `first.close` | The first candle of the trading day. |
| `prev_day.open`, `prev_day.high`, `prev_day.low`, `prev_day.close` | The previous trading day as one candle. |
| every indicator name | Its value on the current candle. |
| `entry` | The entry price. Only in `stop` and `take_profit`. |

### Functions

| Function | Meaning |
|---|---|
| `prev(x)`, `prev(x, n)` | The value 1 or `n` candles ago. |
| `highest(x, n)`, `lowest(x, n)` | Highest or lowest value of the last `n` candles, the current one included. |
| `crossover(a, b)` | `a` is above `b` now and was not on the previous candle. |
| `crossunder(a, b)` | `a` is below `b` now and was not on the previous candle. |
| `abs(x)`, `min(a, b)`, `max(a, b)` | As usual. |

### Operators

`+ - * /`, `< <= > >= == !=`, `and`, `or`, `not`, brackets and numbers. A comparison with a value that does not exist yet (an indicator in its first candles) is false.

Not possible: text, lists, anything with `[` `]`, powers, `if`, and any other function.

## How a trade is simulated

1. All `entry_when` conditions are true on a candle. That is the signal.
2. The trade opens at the open of the next candle. A signal on the last candle is ignored.
3. The stop and the take profit are fixed at that moment.
4. A trade is skipped when the entry is already at or beyond the stop.
5. Each candle is checked in this order: opens beyond the stop (exit at the open), opens beyond the take profit (exit at the open), touches the stop (exit at the stop, also when the take profit is touched in the same candle), touches the take profit.
6. One trade at a time. Signals while a trade is open are ignored.
7. Results are in R, without costs or slippage.

## What cannot be expressed yet

- An indicator on another timeframe than the strategy's.
- Moving the stop during a trade (trailing stop, break-even).
- More than one trade at the same time, or scaling in and out.
- Orders that wait for a price (limit and stop orders). Entries are always at the next open.

A strategy that needs one of these is not supported. Say so instead of approximating it silently.

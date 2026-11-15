# tradelab

Explain a trading strategy to Claude in plain words. tradelab backtests it on candles stored on your own computer and gives you a report: the numbers, a few large charts, and three example trades drawn like on a trading screen.

Not financial advice. This tool explains backtests and past trades for learning purposes. It does not tell you what to buy or sell.

## Why

A strategy can look great in a backtest and still fail when you trade it, because you skip setups or trade outside your own rules. tradelab first shows you what your rules really do: every example trade lists each rule and the values it had at that moment. A trading journal that checks your real trades against the same rules is planned (see Roadmap).

## What you need

- [Claude Code](https://claude.com/claude-code) (terminal or desktop app)
- [uv](https://docs.astral.sh/uv/) (it installs Python and the packages for you)
- A free [Twelve Data](https://twelvedata.com) API key, for the one-time download of candles

## Install

1. Add this repository as a plugin marketplace and install the plugin. Replace `<owner>` with the GitHub account that hosts this repository.

   ```
   claude plugin marketplace add <owner>/tradelab
   claude plugin install tradelab@tradelab
   ```

   On Claude Code 2.1.275 or later this also works in one step, inside a session:

   ```
   /plugin install tradelab --marketplace <owner>/tradelab
   ```

2. Save your Twelve Data key in the file `~/.tradelab/twelvedata.key` (one line, only the key). On Windows that is `C:\Users\<you>\.tradelab\twelvedata.key`. The environment variable `TWELVEDATA_API_KEY` works too. Never paste the key in a chat.

3. Download the candles. Ask Claude "which tradelab data do I have?" and it gives you the exact command for your computer. It takes about 35 minutes for all four markets because the free plan allows 8 requests per minute. You can stop it and run it again: it continues where it stopped.

The first start after installing can take a few minutes while uv downloads Python and the packages. If the tradelab tools do not show up, wait a moment and restart the session.

## Your first backtest

Start a session and type:

```
/tradelab:backtest
```

Or just say that you want to test a strategy. For example:

> If the first 1-hour candle of the day on gold drops more than 0.5% and the next candle closes higher but below the middle of the first candle, with RSI below 30, go short. Stop loss above the first candle, take profit at 4R.

Claude then:

1. translates your words into fixed rules and shows them to you, formula by formula
2. waits until you say the translation is right
3. runs the backtest and explains the numbers
4. shows three trades on a chart: a loss, a win, and the one that took longest, with the setup, the entry, the stop and target zones, and the indicators
5. writes everything to a report you can open in your browser

To continue later, in any session:

```
/tradelab:strategy <the name you gave it>
```

## Markets and candle sizes

| Market | Data used | Note |
|---|---|---|
| S&P 500 | `SPY` | The fund that tracks the index |
| Nasdaq 100 | `QQQ` | The fund that tracks the index |
| Gold | `XAU/USD` | Spot price |
| Silver | `SLV` | A stand-in: the silver fund, US market hours only. Spot silver needs a paid Twelve Data plan |

Candle sizes: 1min, 5min, 15min, 30min, 1h, 4h and 1day. Only 1-minute candles (1 year) and 5-minute candles (5 years) are downloaded. The other sizes are built from the 5-minute candles on your computer.

Indicators are never downloaded. They are calculated from the candles: SMA, EMA, RSI, MACD, ATR and Bollinger Bands.

## What it does not do

- No costs, spread or slippage. Results are in R: the risk of one trade.
- Entries are always at the open of the next candle. No limit or stop orders.
- One trade at a time. No trailing stops, no scaling in or out.
- No indicator on another timeframe than the strategy's own.
- Free intraday data starts in 2020.
- Pine Script is not run. Claude translates it to the rule format and tells you what it could not translate.

The full rule format is in [docs/strategy-format.md](docs/strategy-format.md). What the data source gives is in [docs/data-sources.md](docs/data-sources.md).

## How it works

- `tradelab download` fetches candles from Twelve Data once and stores them as files in `~/.tradelab/data`.
- An MCP server gives Claude seven tools: check the data, validate, save, list and load strategies, run a backtest, build the report.
- Two skills tell Claude how to lead the conversation: `backtest` and `strategy`.
- Claude writes the rules and the explanation. The calculations are done by tested Python code, not by the model.
- Formulas in a strategy are never executed as code. They are parsed and only a fixed list of names, operators and functions is allowed.
- Your strategies, results and reports stay on your computer, in `~/.tradelab/strategies`.

## Development

```
uv sync
uv run pytest
```

To try the plugin from a local copy:

```
claude plugin validate .
claude --plugin-dir .
```

## Roadmap

A trading journal: a small program watches the positions panel of your trading screen and saves a screenshot per trade. Claude reads the screenshots, fetches the candles and indicators of that moment, checks the trade against your saved strategy and explains why it worked or not.

## License

MIT

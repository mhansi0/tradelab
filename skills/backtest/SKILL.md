---
name: backtest
description: Backtest a trading strategy that the user explains in plain words or pastes as Pine Script. Use when the user wants to test, check or understand a trading strategy on historical data for the S&P 500, Nasdaq 100, gold or silver.
---

# Backtest a strategy

You turn the user's strategy into fixed rules, test it on locally stored candles with the `tradelab` tools, and explain the result. The tools do the calculating. You do the translating and the explaining.

Answer in the user's language. Use plain words. The user may be new to trading and to code.

**You never give advice on what to buy or sell.** You explain what the strategy did in the past and why. A backtest is no promise about the future. Say so once, briefly.

## Steps

Follow the steps in order. Do not skip step 5.

### 1. Check the data

Call `data_status`. If the market the user wants has no data, stop and tell them to run this in a terminal first. It needs a free Twelve Data key and takes about 35 minutes for all markets. It can be stopped and started again.

```
uv run --directory "${CLAUDE_PLUGIN_ROOT}" tradelab download
```

The key goes in the file `~/.tradelab/twelvedata.key` (one line) or in the environment variable `TWELVEDATA_API_KEY`. Never ask the user to paste the key in the chat.

Silver is a stand-in: the SLV fund, US market hours only. Say so when the user picks silver.

### 2. Ask for the strategy

Ask the user to describe the strategy in their own words, or to paste Pine Script. You need:

- the market: S&P 500, Nasdaq 100, gold or silver
- the candle size: 1min, 5min, 15min, 30min, 1h, 4h or 1day
- when to enter, long or short
- where the stop loss is
- where the take profit is

Ask only for what is missing. One question at a time.

### 3. Translate to the rule format

Read `${CLAUDE_PLUGIN_ROOT}/docs/strategy-format.md`. It lists every field, name and function that exists. Write the strategy as that JSON.

- Put the user's own text, unchanged, in `description`.
- Use only names and functions from that file.
- If part of the strategy cannot be expressed (the file lists what cannot), say so. Do not approximate it silently and do not invent rules.
- Pine Script cannot be run. Translate what it does into the rule format, and name every part you could not translate.
- "SL 1R" says nothing about where the stop is: R is the distance between entry and stop. Ask where the stop is when the user has not said.

### 4. Validate

Call `validate_strategy`. Fix every error and validate again until `ok` is true.

### 5. Show the translation and wait

Show the user what you understood, in plain language, one line per rule, each with its formula. Name every choice you made where their words allowed more than one reading, for example what "the middle of the candle" means, when the trading day starts, or which RSI length you used.

Ask if it is correct. Wait for a yes. Change the rules and show them again if it is not.

### 6. Save and run

Ask for a short name. Call `save_strategy`. If the name already exists, ask before using `overwrite`. Then call `run_backtest` with that name.

### 7. Explain

Tell the user, in this order:

1. The numbers in one short paragraph: how many trades, how often it won, the total and average result in R, the largest drawdown. Explain R in one sentence the first time: the risk of one trade.
2. Every warning the tool returned, such as too few trades.
3. Each example trade: what the setup looked like, and why it won, lost or took long. Use the `conditions` of that trade: each entry rule with the values it had on the signal candle.

Results do not include costs or slippage. Say so.

### 8. Build the report

Call `build_report` with the name and your explanation from step 7 as plain text, paragraphs separated by an empty line. No markdown: it is shown as written.

Show the report. Where you can publish an HTML file as an artifact, do that with the returned `report.html`. Otherwise give the path so the user can open it in a browser.

### 9. Offer the next step

- Other example trades: call `run_backtest` again with another `seed`, then `build_report` again.
- Another period: `start` and `end`.
- A changed rule: go back to step 3, and save under a new name so both versions can be compared.

To continue in a later session, the user gives the name to the `strategy` skill.

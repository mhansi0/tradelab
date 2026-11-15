---
name: strategy
description: Reopen a trading strategy that was saved earlier with tradelab, by its name, to see its rules and last backtest, test it again, change it or show its report. Use when the user names a saved strategy or asks which strategies they have.
---

# Reopen a saved strategy

The user gives a strategy name, for example `/tradelab:strategy goud-eerste-candle-short`. The strategy, its last backtest and its report are stored on the user's computer. You load them with the `tradelab` tools and continue from there.

Answer in the user's language. Use plain words. **You never give advice on what to buy or sell.**

## Steps

1. **No name, or an unknown name:** call `list_strategies` and show the names with their market and candle size. Ask which one.
2. **Load it:** call `get_strategy` with the name.
3. **Summarize:** the user's own description, the rules in plain language (one line per rule), and the numbers of the last backtest when there is one. If there is no backtest yet, say so.
4. **Ask what they want to do.** The usual choices:
   - **Test again**, also on another period (`start`, `end`) or with other example trades (`seed`): call `run_backtest`, explain the result as in the `backtest` skill (numbers, warnings, each example trade with its conditions), then call `build_report`.
   - **Change a rule:** read `${CLAUDE_PLUGIN_ROOT}/docs/strategy-format.md`, change the JSON, call `validate_strategy`, show the changed rules in plain language and wait for a yes. Save under a new name so both versions can be compared. Use `overwrite` only when the user asks to replace the old one.
   - **Show the report:** use `report_path` from `get_strategy`. Publish it as an artifact where you can, otherwise give the path.

A changed strategy has no backtest until you run one. Never present old numbers as the result of new rules.

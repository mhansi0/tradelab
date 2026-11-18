# Data sources

tradelab stores candles locally and backtests read only those files. Indicators are never downloaded. They are always calculated from the stored candles.

There are two ways to fill the storage: files from HistData.com (`tradelab import`) and the Twelve Data API (`tradelab download`). A market holds candles from one source only, because prices differ per source. The file `~/.tradelab/data/<MARKET>/source.txt` records which one.

## HistData.com files (checked 15 November 2026)

Free 1-minute files, downloaded by hand in a browser, one zip per year. No account, no key, no request limit.

| Market | Their name | 1-minute history starts |
|---|---|---|
| S&P 500 | `SPX/USD` | November 2010 |
| Nasdaq 100 | `NSX/USD` | November 2010 |
| Gold | `XAU/USD` | March 2009 |
| Silver | `XAG/USD` | May 2009 |

File format ("Generic ASCII" M1), from their specification: no header, semicolons, one candle per line.

```
20120201 000000;1.306600;1.306600;1.306560;1.306560;0
```

The fields are time, open, high, low, close and volume. What matters:

- Times are Eastern Standard Time without daylight saving. tradelab adds 5 hours to get UTC.
- Prices are bid quotes of one provider, not exchange prices.
- Volume is always 0.
- The two index prices trade almost around the clock. The trading day for strategies still starts at 09:30 New York, unless the strategy sets its own `session_start`.
- Gold and silver stop every day from 17:00 to 18:00 New York. Their trading day starts at 18:00 New York. A day that starts at midnight UTC would turn every Sunday evening into a "day" of one candle: on the 2024 gold file that happened 52 times.

How tradelab uses the files:

- `tradelab import <folder>` reads every `.zip` and `.csv` in the folder whose name holds one of the four names, for example `HISTDATA_COM_ASCII_XAUUSD_M1_2024.zip`. Other files are skipped and reported.
- All files are read before anything is stored. One unreadable file stops the import and nothing changes.
- The minutes are stored, and the 5-minute candles are rebuilt from all stored minutes.
- It refuses to import into a market that holds Twelve Data candles, unless `--replace` is given. That deletes those candles first.

Not checked: the quality of the files (gaps, bad ticks) and how the current year is offered. Their terms of use are not on the download page. A third party describes them as free for personal and educational use with limits on redistribution, so do not publish the files.

## Parquet files (`tradelab import-parquet`)

Besides the four markets above, any number of markets can be imported from `.parquet` files with 1-minute candles. Checked on 15 November 2026 with 1253 US stocks and 60 forex or CFD files.

| Kind | How it is recognized | Trading day starts | Notes |
|---|---|---|---|
| US stock | times without time zone | 09:30 New York | HF Data Library: IEX trades only, regular hours, minutes without trades are missing, 303 million candles in 1253 files, March 2022 to November 2026 |
| Forex or CFD | times in UTC | 17:00 New York | volume always 0; the week opens Sunday 22:00 UTC (21:00 in summer), which is 17:00 New York |

- The naive stock times are New York wall-clock time: on all 1253 files the first candle is 09:30 and the last 15:59, summer and winter. The conversion to UTC follows daylight saving.
- The market name is the file name up to the first underscore. A ticker equal to a built-in market name gets `-US` (stock `GOLD` is stored as `GOLD-US`). `XAUUSD`, `XAGUSD`, `SPXUSD` and `NSXUSD` are stored in the built-in markets: the 2024 gold candles of this file were identical to the HistData ones.
- Every other market gets a `market.json` next to its candles in `~/.tradelab/data/<NAME>/`: label, time zone, day start and note.
- Files are imported one by one. A file that cannot be read is skipped and reported, the rest goes on. Running it again merges: stored minutes are never duplicated.
- The tool `data_status` lists these markets only when given a `search`, because there are more than a thousand.

What was checked on 15 November 2026:

- **Splits and dividends (stocks):** prices are adjusted for stock splits and not for dividends. The HF Data Library says so itself, and the files agree: AMZN, GOOGL, TSLA, NVDA, AVGO, CMG, WMT and LRCX show no jump of 1:3 to 1:50 at their splits, and the AAPL closes on three dates match the real closes to a few cents (the real closes are from memory). The library says files downloaded before 6 October 2026 hold a dividend adjustment for part of the period. Do not mix those with newer files: a second import merges by time stamp and would join two different price series. These files were downloaded on 15 November 2026.
- **Gaps (forex):** every pair has the daily break of about one hour. Outside the weekend a typical pair has 13 gaps over 3 hours in almost five years, and the longest ones sit on holidays (EURUSD: Good Friday 2023 with 69 hours, New Year with 24 hours). No unexplained holes were seen, but not every gap was looked at. Five files trade only part of the day (BCOUSD, EURHUF, FRXEUR, HKXHKD, UDXUSD) and have a gap every night.

## Terms of the stock data

- The HF Data Library is licensed CC BY 4.0 for the compilation. The bars come from IEX, so IEX's terms apply too: when you share the data you keep "Data provided for free by IEX." with a link to https://www.iex.io/legal/hist-data-terms, and you tell the receiver about both terms.
- Their terms of use (https://hfdatalibrary.com/pages/terms) allow academic and educational research only. They forbid trading and investing with the data, including "building strategies or signals used with real money", and any use where a data error could cause a financial loss. Commercial use is not listed as permitted.
- tradelab backtests are for learning how a strategy behaved. Do not trade on them. Whoever uses the stock files is responsible for reading those terms.
- Each person can also download the files from hfdatalibrary.com themselves: single tickers in the browser without an account, or through their API with a free key (100 downloads per minute, key valid 30 days).
- The files carry `citation` and `iex_attribution` in their metadata. tradelab's own stored copies do not keep it, so share the original files, not tradelab's stored copies.

## Sharing the files

The maker asked both providers by email (HF Data Library for the stocks, HistData.com for the forex or CFD files, which are HistData candles converted to parquet). Both answered that sharing is fine as long as the source is named. That is the maker's report: the emails are not in this repository, so keep them. The terms of use above still apply to whoever uses the data, so the stock files stay for academic and educational research.

The text that goes with every shared copy is in [hosting-the-data.md](hosting-the-data.md), which also describes how the files are put on Hugging Face for `tradelab fetch`. The notes that `data_status` and every backtest show carry the same source names.

## Twelve Data, what the free plan gives (checked 15 November 2026)

| Market | Symbol used | Intraday history starts | Note |
|---|---|---|---|
| S&P 500 | `SPY` | February 2020 | Fund that tracks the index. The index itself is not available. |
| Nasdaq 100 | `QQQ` | February 2020 | Fund that tracks the index. |
| Gold | `XAU/USD` | March 2020 | Spot price, trades almost around the clock. |
| Silver | `SLV` | February 2020 | Proxy. `XAG/USD` needs the Grow or Venture plan. SLV trades during US market hours only. |

- 800 requests per day and 8 per minute.
- One request returns at most 5000 candles.
- A full download (5 years of 5-minute candles and 1 year of 1-minute candles for all four markets) is about 270 requests, so about 35 minutes.

## The `time_series` endpoint (from the Twelve Data docs)

`GET https://api.twelvedata.com/time_series`

| Parameter | Value tradelab sends |
|---|---|
| `symbol` | for example `XAU/USD` |
| `interval` | `1min` or `5min` |
| `end_date` | `2006-01-02T15:04:05`, in UTC |
| `outputsize` | `5000` (the maximum) |
| `timezone` | `UTC` (the default is the exchange time zone) |
| `apikey` | the user's key |

Values come back newest first (`order` defaults to `desc`). Numbers are strings. `volume` is only present for instruments that have it.

A good answer has `"status": "ok"` and a `values` list with `datetime`, `open`, `high`, `low`, `close` and sometimes `volume`.

An error answer is `{"code": 400, "message": "...", "status": "error"}`. Codes: 400 bad parameter, 401 bad key, 403 plan upgrade needed, 404 no data found, 429 request limit reached, 500 server problem.

## How tradelab uses it

- It pages backwards in time: each request asks for the 5000 candles before the oldest one it already has.
- It waits 8 seconds between requests. On a 429 it waits 60 seconds and tries again, at most 5 times.
- A 404 is read as "no older data".
- Only `1min` and `5min` are downloaded. `15min`, `30min`, `1h`, `4h` and `1day` are built locally from `5min`.
- The download can be stopped and started again. It continues where it stopped.

## The API key

Put the key in the environment variable `TWELVEDATA_API_KEY`, or in the file `~/.tradelab/twelvedata.key` (one line). The key is never written to a log or an error message.

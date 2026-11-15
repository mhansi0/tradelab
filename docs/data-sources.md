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

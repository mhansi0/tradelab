# Data sources

tradelab downloads candles from [Twelve Data](https://twelvedata.com) and stores them locally. Indicators are never downloaded. They are always calculated from the stored candles.

## What the free plan gives (checked 15 November 2026)

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

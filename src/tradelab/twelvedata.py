"""Candles from Twelve Data. See docs/data-sources.md for what the API gives."""

import os
import time
from collections.abc import Iterator
from datetime import datetime, timezone

import httpx
import pandas as pd

from .paths import home
from .store import COLUMNS

BASE_URL = "https://api.twelvedata.com/time_series"
PAGE_SIZE = 5000
SECONDS_BETWEEN_CALLS = 8  # free plan: 8 requests per minute
RATE_LIMIT_WAIT = 60
RATE_LIMIT_RETRIES = 5


class DataSourceError(Exception):
    pass


class _RateLimited(DataSourceError):
    pass


def api_key() -> str:
    key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    key_file = home() / "twelvedata.key"
    if not key and key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise DataSourceError(
            "No Twelve Data API key. Set the TWELVEDATA_API_KEY environment variable "
            f"or put the key in {key_file} (one line). Free keys: https://twelvedata.com")
    return key


def fetch_page(symbol: str, interval: str, end: datetime | None, client: httpx.Client) -> pd.DataFrame:
    """At most PAGE_SIZE candles, the latest ones before `end`."""
    key = api_key()
    params = {"symbol": symbol, "interval": interval, "outputsize": PAGE_SIZE,
              "timezone": "UTC", "apikey": key}
    if end is not None:
        params["end_date"] = end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        body = client.get(BASE_URL, params=params).json()
    except (httpx.HTTPError, ValueError) as error:
        # the request URL holds the key, so the original error is not passed on
        raise DataSourceError(f"Could not reach Twelve Data ({type(error).__name__})") from None

    if body.get("status") == "error":
        code = body.get("code")
        if code == 404:  # no data found: there is nothing older
            return _to_frame([])
        message = str(body.get("message", "")).replace(key, "***")
        if code == 429:
            raise _RateLimited(f"Twelve Data request limit reached: {message}")
        raise DataSourceError(f"Twelve Data error {code} for {symbol} {interval}: {message}")

    df = _to_frame(body.get("values", []))
    return df[df.index < end] if end is not None else df


def _to_frame(values: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(values, columns=["datetime", *COLUMNS])
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("datetime")), name="time").tz_localize("UTC")
    return df.astype(float).fillna({"volume": 0.0}).sort_index()


def fetch_range(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    client: httpx.Client | None = None,
    sleep=time.sleep,
) -> Iterator[pd.DataFrame]:
    """Pages of candles in [start, end), newest page first."""
    own_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        first_call = True
        while end > start:
            if not first_call:
                sleep(SECONDS_BETWEEN_CALLS)
            first_call = False
            page = _fetch_with_retry(symbol, interval, end, client, sleep)
            page = page[page.index >= start]
            if page.empty:
                return
            yield page
            end = page.index[0]
    finally:
        if own_client:
            client.close()


def _fetch_with_retry(symbol, interval, end, client, sleep) -> pd.DataFrame:
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return fetch_page(symbol, interval, end, client)
        except _RateLimited as error:
            if attempt == RATE_LIMIT_RETRIES:
                raise DataSourceError(
                    f"{error} Still limited after {RATE_LIMIT_RETRIES} waits. The daily limit may be "
                    "used up. Run the download again later, it continues where it stopped.") from None
            sleep(RATE_LIMIT_WAIT)

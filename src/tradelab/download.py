"""`tradelab download`: fetch candles once and keep them on disk. Safe to stop and run again."""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from . import twelvedata
from .markets import MARKETS, get_market
from .store import load_base, save_candles
from .twelvedata import DataSourceError


def plan_ranges(first, last, want_start, now) -> list[tuple[datetime, datetime]]:
    """What is still missing: first the catch-up to now, then the older history."""
    if first is None:
        return [(want_start, now)]
    ranges = [(last, now)]
    if want_start < first:
        ranges.append((want_start, first))
    return ranges


def download(
    markets: list[str],
    years_5min: float = 5,
    years_1min: float = 1,
    fetch=twelvedata.fetch_range,
    now: datetime | None = None,
    log=print,
) -> None:
    now = now or datetime.now(timezone.utc)
    chosen = [get_market(key) for key in markets]
    for market in chosen:
        for base, years in (("5min", years_5min), ("1min", years_1min)):
            stored = load_base(market.key, base)
            first, last = (None, None) if stored.empty else (stored.index[0], stored.index[-1])
            want_start = now - timedelta(days=365.25 * years)
            for start, end in plan_ranges(first, last, want_start, now):
                catching_up = first is not None and end == now
                held, pages = [], 0
                for page in fetch(market.symbol, base, start, end):
                    pages += 1
                    if catching_up:
                        # pages arrive newest first: saving one before the rest would leave a hole
                        # that the next run cannot see, so the catch-up is saved in one go
                        held.append(page)
                    else:
                        save_candles(market.key, base, page)
                    log(f"{market.key} {base}: {page.index[0]:%Y-%m-%d} ({pages} pages)")
                for page in held:
                    save_candles(market.key, base, page)
    log("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tradelab", description="Download candles from Twelve Data and store them locally.")
    parser.add_argument("command", choices=["download"])
    parser.add_argument("--markets", default=",".join(MARKETS),
                        help=f"comma-separated, default: all ({', '.join(MARKETS)})")
    parser.add_argument("--years-5min", type=float, default=5)
    parser.add_argument("--years-1min", type=float, default=1)
    args = parser.parse_args()
    try:
        twelvedata.api_key()
        download(args.markets.split(","), args.years_5min, args.years_1min)
    except (DataSourceError, ValueError) as error:
        sys.exit(f"Error: {error}")
    except KeyboardInterrupt:
        sys.exit("Stopped. Run the same command again to continue.")

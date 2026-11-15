"""`tradelab download`: fetch candles once and keep them on disk. Safe to stop and run again."""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from . import twelvedata
from .histdata import import_folder
from .fetch import SOURCE_ENV, available, fetch
from .markets import MARKETS, get_market
from .parquet_import import import_parquet_folder
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
    chosen = [get_market(key.strip().upper()) for key in markets]
    for market in chosen:
        if market.source != "twelvedata":
            # prices differ per source, so a market filled from files is never topped up from the API
            log(f"{market.key}: skipped, its candles come from files. "
                "Add newer files with 'tradelab import' or 'tradelab import-parquet'.")
            continue
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tradelab", description="Get candles onto this computer.")
    commands = parser.add_subparsers(dest="command", required=True)
    from_files = commands.add_parser(
        "import", help="read 1-minute files downloaded by hand from HistData.com (no key, no limits)")
    from_files.add_argument("folder", help="folder with the HistData .zip or .csv files")
    from_files.add_argument("--replace", action="store_true",
                            help="delete a market's Twelve Data candles and use the files instead")
    from_parquet = commands.add_parser(
        "import-parquet", help="read 1-minute .parquet files: US stocks and forex pairs, any number of markets")
    from_parquet.add_argument("folder", help="folder with .parquet files, subfolders included")
    from_web = commands.add_parser(
        "fetch", help="download single markets (AAPL, EURUSD, ...) from a published copy of the parquet files")
    from_web.add_argument("names", nargs="*", help="market names; with --list: part of a name to look for")
    from_web.add_argument("--source", help=f"web folder with the files and index.json (or set {SOURCE_ENV})")
    from_web.add_argument("--list", action="store_true", help="show which markets can be fetched")
    from_api = commands.add_parser("download", help="download candles from Twelve Data (needs a free key)")
    from_api.add_argument("--markets", default=",".join(MARKETS),
                          help=f"comma-separated, default: all ({', '.join(MARKETS)})")
    from_api.add_argument("--years-5min", type=float, default=5)
    from_api.add_argument("--years-1min", type=float, default=1)
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            import_folder(args.folder, args.replace)
        elif args.command == "import-parquet":
            import_parquet_folder(args.folder)
        elif args.command == "fetch" and args.list:
            found = [name for name in available(args.source) if all(part.upper() in name for part in args.names)]
            print(f"{len(found)} markets: {' '.join(found)}")
        elif args.command == "fetch":
            if not args.names:
                raise ValueError("Give at least one market name, for example: tradelab fetch AAPL EURUSD")
            fetch(args.names, args.source)
        else:
            twelvedata.api_key()
            download(args.markets.split(","), args.years_5min, args.years_1min)
    except (DataSourceError, ValueError) as error:
        sys.exit(f"Error: {error}")
    except KeyboardInterrupt:
        sys.exit("Stopped. Run the same command again to continue.")

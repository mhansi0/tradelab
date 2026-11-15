import os
import re
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("TRADELAB_HOME") or Path.home() / ".tradelab")


def data_file(market: str, base: str) -> Path:
    return home() / "data" / market / f"{base}.parquet"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"Name {name!r} has no letters or digits")
    return slug


def strategy_dir(name: str) -> Path:
    return home() / "strategies" / slugify(name)

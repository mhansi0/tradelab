"""`tradelab fetch`: download single markets from a published copy of the parquet files.

The files sit in one folder on a web server (for example a Hugging Face dataset), next to an
`index.json` that lists them. Nobody has to download all of it: `tradelab fetch AAPL EURUSD` gets
those two files and imports them with `tradelab import-parquet`.
"""

import json
import os
import re
import tempfile
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .parquet_import import import_parquet_folder
from .twelvedata import DataSourceError

SOURCE_ENV = "TRADELAB_DATA_URL"
DEFAULT_SOURCE = "https://huggingface.co/datasets/DDZI43/tradelab-data/resolve/main"
MAX_FILE_BYTES = 500_000_000  # the biggest file of the 1313 is 31 MB
FILE_NAME = re.compile(r"[A-Za-z0-9._-]+\.parquet")


def write_index(folder: str | Path) -> Path:
    """For whoever publishes the files: write the `index.json` that goes next to them."""
    folder = Path(folder)
    index = folder / "index.json"
    index.write_text(json.dumps({"files": sorted(p.name for p in folder.glob("*.parquet"))}), encoding="utf-8")
    return index


def _open(client: httpx.Client | None):
    """The given client stays open for the caller; an own client is closed afterwards."""
    return nullcontext(client) if client else httpx.Client(timeout=60, follow_redirects=True)


def _address(source: str | None) -> str:
    address = (source or os.environ.get(SOURCE_ENV) or DEFAULT_SOURCE).rstrip("/")
    url = urlparse(address)
    # https only; plain http just for a folder served on this computer (testing)
    if url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1")):
        raise DataSourceError(
            f"Not a usable download address. It must be an https:// web folder that holds the .parquet files "
            f"and their index.json (--source or {SOURCE_ENV}).")
    return address


def available(source: str | None = None, client: httpx.Client | None = None) -> dict[str, str]:
    """Market name -> file name, as listed in the index. The name is the file name up to the first underscore."""
    address = _address(source)
    with _open(client) as http:
        try:
            files = http.get(f"{address}/index.json").raise_for_status().json()["files"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise DataSourceError(f"Could not read {address}/index.json ({type(error).__name__}).") from None
    # only plain file names: the index is not trusted to point outside the download folder
    return {f.split("_")[0].upper(): f for f in files if isinstance(f, str) and FILE_NAME.fullmatch(f)}


def _download(address: str, file: str, target: Path, client: httpx.Client) -> None:
    try:
        with client.stream("GET", f"{address}/{file}") as response, target.open("wb") as out:
            response.raise_for_status()
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise DataSourceError(f"{file} is larger than {MAX_FILE_BYTES // 10**6} MB, not downloaded.")
                out.write(chunk)
    except httpx.HTTPError as error:
        raise DataSourceError(f"Could not download {file} ({type(error).__name__}).") from None


def fetch(names: list[str], source: str | None = None, client: httpx.Client | None = None, log=print) -> dict[str, int]:
    """Download and import the named markets. Nothing is downloaded when one name is unknown."""
    address = _address(source)
    with _open(client) as http:
        files = available(address, http)
        wanted = [name.strip().upper() for name in names]
        unknown = [name for name in wanted if name not in files]
        if unknown:
            raise DataSourceError(f"Not in the index: {', '.join(unknown)}. List what exists with: tradelab fetch --list")
        with tempfile.TemporaryDirectory() as folder:
            for name in wanted:
                log(f"Downloading {files[name]}")
                _download(address, files[name], Path(folder) / files[name], http)
            return import_parquet_folder(folder, log)

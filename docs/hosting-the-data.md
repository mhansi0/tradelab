# Hosting the data files

For whoever publishes the candle files so that `tradelab fetch` can get single markets. The maker does this on Hugging Face, as a public dataset.

## The attribution that goes with every copy

Put this text in the bucket as `ATTRIBUTION.md` and on any page that links to the files:

```
US stock candles: HF Data Library, Ahmed Elkassabgi, https://hfdatalibrary.com
(CC BY 4.0, doi 10.5281/zenodo.19501604). Data provided for free by IEX.
IEX Historical Data Terms of Use: https://www.iex.io/legal/hist-data-terms
Terms of the HF Data Library: https://hfdatalibrary.com/pages/terms
These files may be used for academic and educational research only, not for trading.

Forex and CFD candles: HistData.com, https://www.histdata.com
```

Share the original files, not tradelab's stored copies: the originals carry `citation` and `iex_attribution` in their metadata.

## Steps

1. Make a flat folder with all `.parquet` files (no subfolders), `ATTRIBUTION.md` and the index. The index is written by:

   ```
   uv run python -c "from tradelab.fetch import write_index; write_index(r'<folder>')"
   ```

   Rewrite it whenever files are added.
2. On huggingface.co make a free account and create a new **dataset** repository, public, for example `<username>/tradelab-candles`. Public storage is free but "best-effort" (Hugging Face's storage page, checked 17 November 2026): beyond the first few gigabytes they ask for data that is useful to the community, and they may set limits. The 1313 files are 6 GB. A dataset card is required for large datasets: the folder holds one (`README.md`). If Hugging Face ever limits the repository, the same files work on any web folder (Cloudflare R2, Backblaze B2) and only the address changes.
3. Create an access token with write rights (Settings, Access Tokens). Never paste it in a chat or in the repository.
4. Install the command `hf` (`uv tool install huggingface_hub`, or `pip install -U huggingface_hub`; check Hugging Face's install page) and log in with `hf auth login`. You paste the token there yourself.
5. Upload the folder to the repository root. The upload splits itself into several commits and can be started again after an interruption:

   ```
   hf upload <username>/tradelab-candles "<folder>" . --repo-type=dataset
   ```

6. The address for `--source` is `https://huggingface.co/datasets/<username>/tradelab-candles/resolve/main` (the usual address pattern for a file in a dataset; test it). Test: `tradelab fetch --source <that address> --list EUR`. Anonymous downloads are limited to 3,000 file requests per 5 minutes per IP address (Hugging Face's rate limit page, September 2025 figures, subject to change). Fetching a handful of markets uses a handful of requests.
7. Put the address in the README and, if wanted, as the default in `fetch.py` so that `--source` can be left out.

Do not put the files in the git repository.

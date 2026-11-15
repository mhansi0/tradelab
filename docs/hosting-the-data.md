# Hosting the data files

For whoever publishes the candle files so that `tradelab fetch` can get single markets. The maker does this on Backblaze B2.

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
2. In Backblaze create a B2 bucket. The first 10 GB of storage is free, and downloads are free up to 3 times the stored data per month, then $0.01 per GB (Backblaze's pricing page, checked 15 November 2026). The 1313 files are 6 GB, so about 4 GB is left, and about 18 GB of downloads a month are free. Their bucket page speaks of 1 GB of free downloads per day instead: that contradicts the pricing page, so look at your own bill in the first weeks. Set a spending cap in your Backblaze account (not checked how).
3. Make the bucket public (bucket type `allPublic`), so that files can be downloaded without a login. The address must be `https`. A custom domain cannot be put on a B2 bucket directly (Backblaze says so); the address of the bucket is enough for `tradelab fetch`.
4. Upload the folder with `rclone`, which has a B2 backend (create an application key in your Backblaze account; never paste it in a chat or in the repository). The website is slow for 1300 files. Check rclone's B2 page for the exact settings.
5. In the B2 website open one file: it shows the address to download that file (the "friendly URL"). Remove the file name from it: what is left is the address of the folder for `--source`. Test: `tradelab fetch --source https://<that address> --list EUR`.
6. Put the address in the README and, if wanted, as the default in `fetch.py` so that `--source` can be left out.

Do not put the files in the git repository.

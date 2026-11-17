# Hosting the data files

For whoever publishes the candle files so that `tradelab fetch` can get single markets. The maker does this on Cloudflare R2.

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
2. In Cloudflare create an R2 bucket. The free tier has 10 GB of storage per month and no charge for downloads (Cloudflare's pricing page, checked 15 November 2026). The 1313 files are 6 GB, so about 4 GB is left: check the size before adding more. Whether Cloudflare asks for a payment method to switch R2 on is not checked.
3. Make the bucket readable without a login by switching on its public development URL (`https://pub-<code>.r2.dev`, shown in the bucket settings). Cloudflare says that `r2.dev` addresses are rate-limited (the limit is not published), meant for non-production traffic, and without caching or access control. That is enough to start: `tradelab fetch` gets a few files of 1 to 30 MB. When it gets throttled, add a custom domain: it must be a zone in the same Cloudflare account as the bucket (a bought domain, or one added with a partial CNAME setup), and then only the address in the README and in `fetch.py` changes.
4. Upload the folder with `rclone`: create an R2 API token with read and write rights for this bucket (never paste its keys in a chat or in the repository), and use rclone's S3 type with provider Cloudflare and the endpoint `https://<account id>.r2.cloudflarestorage.com`. The Cloudflare website is slow for 1300 files. Check Cloudflare's rclone page for the exact settings.
5. Test: `tradelab fetch --source https://pub-<code>.r2.dev --list EUR`.
6. Put the address in the README and, if wanted, as the default in `fetch.py` so that `--source` can be left out.

Do not put the files in the git repository.

"""One command: extract -> upload to ADLS -> load to Azure SQL."""
from __future__ import annotations

import argparse
from pathlib import Path

from ingestion import extract_pdf as ep
from ingestion import ingest_exchange_rates as fx
from ingestion.load_to_sql import load_directory
from ingestion.upload_adls import upload_directory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bronze", default="data/bronze")
    parser.add_argument("--silver", default="data/silver")
    parser.add_argument("--skip-upload", action="store_true", help="skip ADLS upload")
    args = parser.parse_args()

    bronze, silver = Path(args.bronze), Path(args.silver)
    silver.mkdir(parents=True, exist_ok=True)

    # 1) Extract PDFs
   # for pdf in sorted(bronze.glob("rapport_annuel_*.pdf")):
    #    year, lang = ep.parse_meta(pdf)
     #   print(f"[extract] {pdf.name}")
      #  pages_df, rows_df = ep.extract_pdf(pdf)
       # pages_df.to_parquet(silver / f"report_pages_{year}_{lang}.parquet", index=False)
        #rows_df.to_parquet(silver / f"report_table_rows_{year}_{lang}.parquet", index=False)

    # 2) Normalize FX files
    #for f in sorted(bronze.glob("fx_*")):
     #   if f.suffix.lower() in {".csv", ".xlsx", ".xls"}:
      #      print(f"[fx] {f.name}")
       #     fx.load_fx_file(f).to_parquet(silver / f"exchange_rates_{f.stem}.parquet", index=False)

    # 3) Upload to the lake
    if not args.skip_upload:
        print("[adls] uploading bronze + silver")
        upload_directory(bronze, "bronze", "rapport_annuel_*.pdf", "reports")
        upload_directory(bronze, "bronze", "fx_*", "fx")
        upload_directory(silver, "silver", "report_*.parquet", "reports")
        upload_directory(silver, "silver", "exchange_rates_*.parquet", "fx")

    # 4) Load to the warehouse
    print("[sql] loading landing tables")
    load_directory(silver)
    print("Done.")


if __name__ == "__main__":
    main()
"""Normalize and load BAM exchange rates into Azure SQL."""
import pandas as pd
from pathlib import Path
import argparse
from ingestion.load_to_sql import load_parquet
from common.db import make_engine, wait_for_db

def process_fx_file(csv_path: Path, silver_dir: Path) -> Path:
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path, sep=';', decimal=',')

    # 1. Convert date (Removed the year filter to keep all 26 years!)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)

    # 2. Keep ONLY the reference rates (BAM uses 'reference', not 'buy')
    if 'type' in df.columns:
        df = df[df['type'] == 'reference']

    # 3. Format it exactly as your pipeline expects
    # The 'base' column contains EUR, USD, etc. The 'value' column is the rate in MAD.
    clean_df = pd.DataFrame({
        'rate_date': df['date'].dt.strftime('%Y-%m-%d'),
        'currency_code': df['base'].str.upper(),
        'rate_mad': df['value'],
        'source_file': csv_path.name, # <--- ADD THIS
        'unit': 1
    })

    # 4. Remove duplicates and save to Silver
    clean_df = clean_df.drop_duplicates(subset=['rate_date', 'currency_code'])

    silver_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = silver_dir / "exchange_rates_fx.parquet"
    clean_df.to_parquet(parquet_path, index=False)

    print(f"Saved clean data to {parquet_path} ({len(clean_df)} rows)")
    return parquet_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/bronze/bam_raw.csv", help="Path to raw BAM CSV")
    parser.add_argument("--silver-dir", default="data/silver")
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        print(f"Error: Could not find {csv_path}. Please check the filename.")
        return

    # Process the CSV and save Parquet
    parquet_path = process_fx_file(csv_path, Path(args.silver_dir))

    # Load into Azure SQL
    print("\nConnecting to Azure SQL...")
    engine = make_engine()
    wait_for_db(engine)

    print("Loading into landing.exchange_rates...")
    # Note: load_parquet will DELETE the old broken rows and insert the new ones
    rows_loaded = load_parquet(engine, parquet_path)
    print(f"Success! Loaded {rows_loaded} rows into Azure SQL.")

if __name__ == "__main__":
    main()
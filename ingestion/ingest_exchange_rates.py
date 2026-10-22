"""Normalize BAM reference exchange-rate files into a clean long-format Parquet file."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ALIASES = {
    "rate_date": {"date", "date_cours", "datecours", "rate_date", "jour"},
    "currency_code": {"currency", "devise", "code", "code_devise", "currency_code", "iso"},
    "unit": {"unit", "unite", "unité", "unites", "quantite", "quantité", "unit_value"},
    "rate_mad": {"rate", "cours", "cours_reference", "cours_de_reference", "cours_de_référence",
                 "reference_rate", "rate_mad", "mid", "valeur"},
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_").replace("-", "_")
        for target, names in ALIASES.items():
            if key in names:
                rename[col] = target
    df = df.rename(columns=rename)
    missing = {"rate_date", "currency_code", "rate_mad"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns {missing}. Found: {list(df.columns)}. "
            "Extend ALIASES in ingest_exchange_rates.py to match your file."
        )
    if "unit" not in df.columns:
        df["unit"] = 1
    return df


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def load_fx_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    df = _normalize_columns(df)

    out = pd.DataFrame(
        {
            "rate_date": pd.to_datetime(df["rate_date"], dayfirst=True, errors="coerce").dt.date,
            "currency_code": df["currency_code"].astype(str).str.strip().str.upper(),
            "unit": pd.to_numeric(df["unit"], errors="coerce").fillna(1).astype(int),
            "rate_mad": _to_float(df["rate_mad"]),
        }
    )
    out = out.dropna(subset=["rate_date", "rate_mad"])
    out = out[(out["rate_mad"] > 0) & (out["currency_code"].str.len().between(3, 10))]
    out["source_file"] = path.name
    return out.drop_duplicates(subset=["rate_date", "currency_code", "source_file"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/bronze")
    parser.add_argument("--output-dir", default="data/silver")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in Path(args.input_dir).glob("fx_*") if p.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )
    if not files:
        raise SystemExit(f"No fx_* files in {args.input_dir}")

    for f in files:
        df = load_fx_file(f)
        target = out_dir / f"exchange_rates_{f.stem}.parquet"
        df.to_parquet(target, index=False)
        print(f"{f.name}: {len(df)} rows, {df['currency_code'].nunique()} currencies "
              f"({df['rate_date'].min()} -> {df['rate_date'].max()}) -> {target.name}")


if __name__ == "__main__":
    main()
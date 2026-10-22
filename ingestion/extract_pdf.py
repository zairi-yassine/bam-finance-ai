"""Extract page text and table rows from BAM annual-report PDFs using pdfplumber.

Outputs (Parquet, in data/silver/):
  - report_pages_<year>_<lang>.parquet
  - report_table_rows_<year>_<lang>.parquet
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import pdfplumber

FILENAME_RE = re.compile(r"rapport_annuel_(?P<year>\d{4})_(?P<lang>fr|en)\.pdf$", re.IGNORECASE)
MAX_VALUE_COLS = 6

# The magic regex: Finds "Tableau 3.2.19" or "Table 12"
TABLE_TITLE_REGEX = re.compile(r"(Tableau|Table)\s+(\d+(\.\d+)*)", re.IGNORECASE)

LINES_STRATEGY = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
TEXT_STRATEGY = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 5,
}
HAS_DIGIT = re.compile(r"\d")


def parse_meta(pdf_path: Path) -> tuple[int, str]:
    # Only matches _fr and _en now. If it's _ar, it throws a ValueError, but we filter them out in main().
    m = FILENAME_RE.search(pdf_path.name)
    if not m:
        raise ValueError(
            f"Bad file name '{pdf_path.name}'. Expected rapport_annuel_<YYYY>_<fr|en>.pdf"
        )
    return int(m.group("year")), m.group("lang").lower()


def clean_cell(cell: object) -> str:
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip()


def table_looks_real(rows: list[list[str]]) -> bool:
    """Heuristic filter: keeps tables with >=2 rows, >=2 columns, and numeric content."""
    if len(rows) < 2:
        return False
    numeric_rows = 0
    for r in rows:
        if any(HAS_DIGIT.search(c) for c in r[1:]):
            numeric_rows += 1
    return numeric_rows / len(rows) >= 0.3 and max(len(r) for r in rows) >= 2


def extract_tables_from_page(page: "pdfplumber.page.Page") -> tuple[str | None, list[list[list[str]]]]:
    """
    Returns the table title and a list of extracted tables IF the page contains
    a title like "Tableau X.Y".
    """
    text = page.extract_text() or ""

    # 1. Look for the table title using Regex
    match = TABLE_TITLE_REGEX.search(text)
    if not match:
        return None, []

    table_title = match.group(0)

    # 2. Extract tables
    raw_tables = page.extract_tables(LINES_STRATEGY)
    if not raw_tables:
        raw_tables = page.extract_tables(TEXT_STRATEGY)

    cleaned_tables: list[list[list[str]]] = []
    for table in raw_tables or []:
        rows = [[clean_cell(c) for c in row] for row in table]
        rows = [r for r in rows if any(r)]

        # 3. Keep only if it passes the numeric check
        if table_looks_real(rows):
            cleaned_tables.append(rows)

    return table_title, cleaned_tables


def row_to_record(row: list[str]) -> tuple[str, list[str]] | None:
    """Split a table row into (label, values). The label is the first non-numeric text cell."""
    label_idx = None
    for i, cell in enumerate(row):
        if cell and not re.fullmatch(r"[\d\s.,()%\-–−+/]*", cell):
            label_idx = i
            break
    if label_idx is None:
        return None
    label = row[label_idx]
    values = [c for c in row[label_idx + 1:] if c != ""]
    return label, values[:MAX_VALUE_COLS]


def extract_pdf(pdf_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    year, lang = parse_meta(pdf_path)
    page_records: list[dict] = []
    row_records: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            # --- RULE FOR TEXT (RAG) ---
            if len(text.strip()) > 200:
                page_records.append(
                    {
                        "report_year": year,
                        "language": lang,
                        "source_file": pdf_path.name,
                        "page_number": page_number,
                        "text_content": text,
                        "n_chars": len(text),
                    }
                )

            # --- RULE FOR TABLES (SQL) ---
            table_title, extracted_tables = extract_tables_from_page(page)

            if not extracted_tables:
                continue

            for table_index, rows in enumerate(extracted_tables):
                header_text = " | ".join(c for c in rows[0] if c)[:1000]
                for row_index, row in enumerate(rows):
                    parsed = row_to_record(row)
                    if parsed is None:
                        continue
                    label, values = parsed

                    rec = {
                        "report_year": year,
                        "language": lang,
                        "source_file": pdf_path.name,
                        "page_number": page_number,
                        "table_index": table_index,
                        "table_title": table_title,
                        "row_index": row_index,
                        "row_label": label[:500],
                        "header_text": header_text,
                        "n_cols": len(values),
                    }
                    for i in range(MAX_VALUE_COLS):
                        rec[f"col_{i + 1}"] = values[i][:200] if i < len(values) else None
                    row_records.append(rec)

            page.flush_cache()
            if page_number % 25 == 0:
                print(f"  [{pdf_path.name}] {page_number}/{total} pages")

    pages_df = pd.DataFrame(page_records)
    rows_df = pd.DataFrame(row_records)
    return pages_df, rows_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract BAM annual-report PDFs to Parquet")
    parser.add_argument("--input-dir", default="data/bronze")
    parser.add_argument("--output-dir", default="data/silver")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Only process _fr and _en files
    pdfs = sorted(
        p for p in Path(args.input_dir).glob("rapport_annuel_*.pdf")
        if not p.name.endswith("_ar.pdf")
    )

    if not pdfs:
        raise SystemExit(f"No FR/EN PDFs found in {args.input_dir}")

    for pdf_path in pdfs:
        year, lang = parse_meta(pdf_path)
        print(f"Extracting {pdf_path.name} ...")
        pages_df, rows_df = extract_pdf(pdf_path)

        pages_df.to_parquet(out_dir / f"report_pages_{year}_{lang}.parquet", index=False)
        rows_df.to_parquet(out_dir / f"report_table_rows_{year}_{lang}.parquet", index=False)

        empty_pages = int((pages_df["n_chars"] == 0).sum()) if not pages_df.empty else 0
        print(
            f"  -> {len(pages_df)} pages ({empty_pages} without text layer), "
            f"{len(rows_df)} table rows"
        )


if __name__ == "__main__":
    main()
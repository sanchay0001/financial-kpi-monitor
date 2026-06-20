"""
Layer 3b: Load
Reads processed CSVs + raw JSON (for company info) and inserts into SQLite.
Uses INSERT OR REPLACE so it's safe to re-run without duplicates.

Run directly:  python src/etl/load.py
"""
import json
import math
import sqlite3
import pandas as pd
from pathlib import Path

# Resolve paths relative to this file
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "financial_kpi.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _clean_val(v):
    """Convert NaN/inf to None so SQLite doesn't choke."""
    if v is None:
        return None
    try:
        if math.isnan(v) or math.isinf(v):
            return None
    except TypeError:
        pass
    return v


def load_companies():
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    for path in RAW_DIR.glob("*.json"):
        with open(path) as f:
            raw = json.load(f)
        info = raw.get("info", {})
        ticker = raw.get("ticker", path.stem)
        cur.execute("""
            INSERT OR REPLACE INTO companies
                (ticker, short_name, sector, industry, market_cap, currency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            info.get("shortName"),
            info.get("sector"),
            info.get("industry"),
            _clean_val(info.get("marketCap")),
            info.get("currency"),
        ))
        inserted += 1
    conn.commit()
    conn.close()
    print(f"  companies: {inserted} rows loaded")


def load_csv(csv_name: str, table: str, columns: list):
    path = PROCESSED_DIR / csv_name
    if not path.exists():
        print(f"  [warn] {csv_name} not found, skipping.")
        return

    df = pd.read_csv(path)
    conn = get_connection()
    cur = conn.cursor()

    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"

    inserted = 0
    for _, row in df.iterrows():
        values = [_clean_val(row.get(c)) for c in columns]
        cur.execute(sql, values)
        inserted += 1

    conn.commit()
    conn.close()
    print(f"  {table}: {inserted} rows loaded")


def verify():
    """Quick sanity check — print row counts for all tables."""
    conn = get_connection()
    cur = conn.cursor()
    print("\nVerification:")
    for table in ["companies", "income_stmt", "balance_sheet", "cashflow"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()


def run():
    print("Loading data into SQLite...")

    load_companies()

    load_csv("income_stmt.csv", "income_stmt", [
        "ticker", "year", "total_revenue", "gross_profit",
        "operating_income", "net_income", "ebitda"
    ])

    load_csv("balance_sheet.csv", "balance_sheet", [
        "ticker", "year", "total_assets", "total_liabilities",
        "stockholders_equity", "current_assets", "current_liabilities",
        "cash", "inventory", "total_debt"
    ])

    load_csv("cashflow.csv", "cashflow", [
        "ticker", "year", "operating_cashflow", "capex", "free_cashflow"
    ])

    verify()


if __name__ == "__main__":
    run()
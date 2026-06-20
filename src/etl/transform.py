"""
Layer 2: Data Transformation
Reads raw JSON files from data/raw/, cleans and normalizes them,
and saves structured CSVs to data/processed/.

Run directly:  python src/etl/transform.py
"""

import json
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Raw JSON structure: { "2023-09-30": { "Total Revenue": 123, ... }, ... }

INCOME_FIELDS = {
    "Total Revenue": "total_revenue",
    "Gross Profit": "gross_profit",
    "Operating Income": "operating_income",
    "Net Income": "net_income",
    "EBITDA": "ebitda",
}

BALANCE_FIELDS = {
    "Total Assets": "total_assets",
    "Total Liabilities Net Minority Interest": "total_liabilities",
    "Stockholders Equity": "stockholders_equity",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Cash And Cash Equivalents": "cash",
    "Inventory": "inventory",
    "Total Debt": "total_debt",
}

CASHFLOW_FIELDS = {
    "Operating Cash Flow": "operating_cashflow",
    "Capital Expenditure": "capex",
    "Free Cash Flow": "free_cashflow",
}


def _extract_fields(raw_dict: dict, field_map: dict, ticker: str) -> pd.DataFrame:
    """
    raw_dict: { "2023-09-30": { "Total Revenue": 394328000000, ... }, ... }
    Returns tidy DataFrame with columns: ticker, year, field1, field2, ...
    """
    if not raw_dict:
        return pd.DataFrame()

    rows = []
    for date_str, fields in raw_dict.items():
        year = date_str[:4]
        row = {"ticker": ticker, "year": int(year)}
        for yf_key, col_name in field_map.items():
            row[col_name] = fields.get(yf_key)  # None if missing
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("year", ascending=False).reset_index(drop=True)
    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    numeric_cols = [c for c in df.columns if c not in ("ticker", "year")]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=numeric_cols, how="all")
    return df


def transform_ticker(ticker: str) -> dict:
    path = RAW_DIR / f"{ticker}.json"
    if not path.exists():
        print(f"  [warn] No raw file for {ticker}, skipping.")
        return {}

    with open(path) as f:
        raw = json.load(f)

    income   = _clean(_extract_fields(raw.get("income_stmt",   {}), INCOME_FIELDS,   ticker))
    balance  = _clean(_extract_fields(raw.get("balance_sheet", {}), BALANCE_FIELDS,  ticker))
    cashflow = _clean(_extract_fields(raw.get("cashflow",      {}), CASHFLOW_FIELDS, ticker))

    return {"income": income, "balance": balance, "cashflow": cashflow}


def run(tickers=None):
    if tickers is None:
        tickers = [p.stem for p in RAW_DIR.glob("*.json")]

    all_income, all_balance, all_cashflow = [], [], []

    for ticker in tickers:
        print(f"Transforming {ticker} ...")
        frames = transform_ticker(ticker)
        if not frames:
            continue

        inc, bal, cf = frames["income"], frames["balance"], frames["cashflow"]
        print(f"  income rows: {len(inc)}  |  balance rows: {len(bal)}  |  cashflow rows: {len(cf)}")

        if not inc.empty:  all_income.append(inc)
        if not bal.empty:  all_balance.append(bal)
        if not cf.empty:   all_cashflow.append(cf)

    for name, frames_list, filename in [
        ("income",   all_income,   "income_stmt.csv"),
        ("balance",  all_balance,  "balance_sheet.csv"),
        ("cashflow", all_cashflow, "cashflow.csv"),
    ]:
        if frames_list:
            combined = pd.concat(frames_list, ignore_index=True)
            out = PROCESSED_DIR / filename
            combined.to_csv(out, index=False)
            print(f"\nSaved {filename}  ({len(combined)} rows x {len(combined.columns)} cols)")
            print(combined.to_string(index=False))
        else:
            print(f"\n[warn] No data for {name}")


if __name__ == "__main__":
    run()
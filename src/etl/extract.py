"""
Layer 1: Data Extraction
Pulls income statement, balance sheet, and cash flow data for a list of
companies using yfinance, and saves each as raw JSON under data/raw/.

Run directly:  python src/etl/extract.py
"""

import json
import time
from pathlib import Path

import yfinance as yf

# ---- Config ----
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _df_to_dict(df):
    """Convert a yfinance financial statement DataFrame to a JSON-safe dict.
    Columns are dates (pandas Timestamps) -> convert to strings.
    """
    if df is None or df.empty:
        return {}
    df = df.copy()
    df.columns = [str(c.date()) if hasattr(c, "date") else str(c) for c in df.columns]
    # Replace NaN with None so json.dumps doesn't choke
    df = df.where(df.notna(), None)
    return df.to_dict()


def fetch_company_financials(ticker: str) -> dict:
    """Fetch raw financial statements + basic info for one ticker."""
    t = yf.Ticker(ticker)

    data = {
        "ticker": ticker,
        "info": {},
        "income_stmt": {},
        "balance_sheet": {},
        "cashflow": {},
    }

    try:
        info = t.info
        # Keep only the fields we actually need (avoids huge/noisy dumps)
        data["info"] = {
            "shortName": info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "marketCap": info.get("marketCap"),
            "currency": info.get("currency"),
        }
    except Exception as e:
        print(f"  [warn] info fetch failed for {ticker}: {e}")

    try:
        data["income_stmt"] = _df_to_dict(t.income_stmt)
    except Exception as e:
        print(f"  [warn] income_stmt fetch failed for {ticker}: {e}")

    try:
        data["balance_sheet"] = _df_to_dict(t.balance_sheet)
    except Exception as e:
        print(f"  [warn] balance_sheet fetch failed for {ticker}: {e}")

    try:
        data["cashflow"] = _df_to_dict(t.cashflow)
    except Exception as e:
        print(f"  [warn] cashflow fetch failed for {ticker}: {e}")

    return data


def save_raw(ticker: str, data: dict) -> Path:
    out_path = RAW_DIR / f"{ticker}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return out_path


def run(tickers=None):
    tickers = tickers or TICKERS
    results = []

    for ticker in tickers:
        print(f"Fetching {ticker} ...")
        data = fetch_company_financials(ticker)
        path = save_raw(ticker, data)
        has_data = bool(data["income_stmt"])
        print(f"  -> saved to {path} (data found: {has_data})")
        results.append((ticker, has_data))
        time.sleep(1)  # be polite to the API, avoid rate-limit issues

    print("\nSummary:")
    for ticker, ok in results:
        print(f"  {ticker}: {'OK' if ok else 'NO DATA'}")

    return results


if __name__ == "__main__":
    run()
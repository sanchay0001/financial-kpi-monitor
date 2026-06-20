"""
Layer 3a: Schema
Creates all SQLite tables. Safe to re-run (CREATE TABLE IF NOT EXISTS).

Run directly:  python src/db/models.py
"""
from database import get_connection

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker      TEXT PRIMARY KEY,
            short_name  TEXT,
            sector      TEXT,
            industry    TEXT,
            market_cap  REAL,
            currency    TEXT
        );

        CREATE TABLE IF NOT EXISTS income_stmt (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker              TEXT NOT NULL,
            year                INTEGER NOT NULL,
            total_revenue       REAL,
            gross_profit        REAL,
            operating_income    REAL,
            net_income          REAL,
            ebitda              REAL,
            UNIQUE(ticker, year),
            FOREIGN KEY(ticker) REFERENCES companies(ticker)
        );

        CREATE TABLE IF NOT EXISTS balance_sheet (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker                  TEXT NOT NULL,
            year                    INTEGER NOT NULL,
            total_assets            REAL,
            total_liabilities       REAL,
            stockholders_equity     REAL,
            current_assets          REAL,
            current_liabilities     REAL,
            cash                    REAL,
            inventory               REAL,
            total_debt              REAL,
            UNIQUE(ticker, year),
            FOREIGN KEY(ticker) REFERENCES companies(ticker)
        );

        CREATE TABLE IF NOT EXISTS cashflow (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker              TEXT NOT NULL,
            year                INTEGER NOT NULL,
            operating_cashflow  REAL,
            capex               REAL,
            free_cashflow       REAL,
            UNIQUE(ticker, year),
            FOREIGN KEY(ticker) REFERENCES companies(ticker)
        );
    """)

    conn.commit()
    conn.close()
    print("All tables created successfully.")

if __name__ == "__main__":
    create_tables()
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "stock_data.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            stock_code TEXT PRIMARY KEY,
            corp_code  TEXT,
            name       TEXT,
            market     TEXT,
            added_at   TEXT DEFAULT (date('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS financials (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code  TEXT,
            year        INTEGER,
            quarter     INTEGER,  -- 0=연간, 1~4=분기
            item        TEXT,     -- 항목명 (매출액, 영업이익 등)
            value       REAL,
            unit        TEXT DEFAULT '백만원',
            source      TEXT DEFAULT 'DART',
            updated_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(stock_code, year, quarter, item)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            stock_code TEXT,
            date       TEXT,
            close      REAL,
            PRIMARY KEY (stock_code, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS manual_data (
            stock_code TEXT,
            year       INTEGER,
            item       TEXT,
            value      REAL,
            memo       TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (stock_code, year, item)
        )
    """)

    conn.commit()
    conn.close()

def get_all_stocks():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM stocks ORDER BY name", conn)
    conn.close()
    return df

def add_stock(stock_code, corp_code, name, market="KRX"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO stocks (stock_code, corp_code, name, market) VALUES (?,?,?,?)",
            (stock_code, corp_code, name, market)
        )
        conn.commit()
        return True, "추가 완료"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def delete_stock(stock_code):
    conn = get_conn()
    conn.execute("DELETE FROM stocks WHERE stock_code=?", (stock_code,))
    conn.execute("DELETE FROM financials WHERE stock_code=?", (stock_code,))
    conn.execute("DELETE FROM prices WHERE stock_code=?", (stock_code,))
    conn.execute("DELETE FROM manual_data WHERE stock_code=?", (stock_code,))
    conn.commit()
    conn.close()

def upsert_financial(stock_code, year, quarter, item, value, source="DART"):
    conn = get_conn()
    conn.execute("""
        INSERT INTO financials (stock_code, year, quarter, item, value, source, updated_at)
        VALUES (?,?,?,?,?,?, datetime('now'))
        ON CONFLICT(stock_code, year, quarter, item)
        DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (stock_code, year, quarter, item, value, source))
    conn.commit()
    conn.close()

def upsert_manual(stock_code, year, item, value, memo=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO manual_data (stock_code, year, item, value, memo, updated_at)
        VALUES (?,?,?,?,?, datetime('now'))
        ON CONFLICT(stock_code, year, item)
        DO UPDATE SET value=excluded.value, memo=excluded.memo, updated_at=excluded.updated_at
    """, (stock_code, year, item, value, memo))
    conn.commit()
    conn.close()

def get_financials(stock_codes, items, years=None):
    conn = get_conn()
    codes_ph = ",".join("?" * len(stock_codes))
    items_ph = ",".join("?" * len(items))
    params = list(stock_codes) + list(items)
    year_clause = ""
    if years:
        year_clause = f" AND year IN ({','.join('?'*len(years))})"
        params += list(years)
    df = pd.read_sql(f"""
        SELECT f.stock_code, s.name, f.year, f.quarter, f.item, f.value, f.source
        FROM financials f
        JOIN stocks s ON f.stock_code = s.stock_code
        WHERE f.stock_code IN ({codes_ph})
          AND f.item IN ({items_ph})
          {year_clause}
        ORDER BY f.stock_code, f.year, f.quarter
    """, conn, params=params)
    conn.close()
    return df

def get_latest_prices(stock_codes):
    conn = get_conn()
    codes_ph = ",".join("?" * len(stock_codes))
    df = pd.read_sql(f"""
        SELECT p.stock_code, s.name, p.date, p.close
        FROM prices p
        JOIN stocks s ON p.stock_code = s.stock_code
        WHERE p.stock_code IN ({codes_ph})
          AND p.date = (SELECT MAX(date) FROM prices p2 WHERE p2.stock_code = p.stock_code)
    """, conn, params=list(stock_codes))
    conn.close()
    return df

def upsert_price(stock_code, date, close):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO prices (stock_code, date, close) VALUES (?,?,?)
    """, (stock_code, str(date), close))
    conn.commit()
    conn.close()

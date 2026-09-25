"""
IBM Supply Chain Intelligence Platform
database/db_manager.py

Supports two modes (set DASHBOARD_MODE in .env):
  - local  : SQLite  (default, no credentials needed)
  - cloud  : IBM Db2 (requires DB2_* env vars from .env)

Usage:
    from database.db_manager import get_engine, execute_query, execute_write, bulk_insert, init_db
"""
import os
import sys
import pandas as pd
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load .env if present (silently skip if missing)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(BASE_DIR, "data", "supply_chain.db")
MODE       = os.getenv("DASHBOARD_MODE", "local").strip().lower()

# ── Engine factory ────────────────────────────────────────────────────────────
def get_engine():
    """Return a SQLAlchemy engine (Db2 in cloud mode, SQLite otherwise)."""
    if MODE == "cloud":
        try:
            from sqlalchemy import create_engine as _ce
            host   = os.getenv("DB2_HOST", "")
            port   = os.getenv("DB2_PORT", "50000")
            dbname = os.getenv("DB2_DATABASE", "")
            user   = os.getenv("DB2_USER", "")
            pwd    = os.getenv("DB2_PASSWORD", "")
            if not all([host, dbname, user, pwd]):
                raise ValueError("DB2 credentials missing in .env — switching to local SQLite.")
            url = f"db2+ibm_db://{user}:{pwd}@{host}:{port}/{dbname}"
            engine = _ce(url)
            # Quick connectivity test
            with engine.connect() as c:
                c.execute("SELECT 1 FROM SYSIBM.SYSDUMMY1")
            print(f"[DB] Connected to IBM Db2 — {host}:{port}/{dbname}")
            return engine
        except Exception as e:
            print(f"[DB] WARNING: Db2 connection failed ({e}). Falling back to SQLite.")
    # Default: SQLite
    from sqlalchemy import create_engine as _ce
    engine = _ce(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    return engine

_engine = None
def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine

def get_connection():
    """Return a raw DBAPI connection for backward compat."""
    return _get_engine().raw_connection()

def execute_query(query, params=None):
    """Run a SELECT query and return a DataFrame."""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if params:
                df = pd.read_sql_query(query, conn, params=params)
            else:
                df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"[DB] Query error: {e}")
        return pd.DataFrame()

def execute_write(query, params=()):
    """Run an INSERT/UPDATE/DELETE statement."""
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            conn.execute(query, params)
    except Exception as e:
        print(f"[DB] Write error: {e}\nQuery: {query[:100]}")

def bulk_insert(df, table_name, if_exists="append", chunksize=5000):
    """Bulk-insert a DataFrame (chunked for large datasets)."""
    try:
        engine = _get_engine()
        schema = os.getenv("DB2_SCHEMA", None) if MODE == "cloud" else None
        df.to_sql(table_name, engine,
                  if_exists=if_exists, index=False,
                  chunksize=chunksize, schema=schema)
        return len(df)
    except Exception as e:
        print(f"[DB] Bulk insert error ({table_name}): {e}")
        return 0

# ── Schema (DDL) ──────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY, product_name TEXT, category TEXT,
    unit_cost REAL, reorder_point INTEGER, lead_time_days INTEGER
);
CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id TEXT PRIMARY KEY, warehouse_name TEXT, region TEXT,
    city TEXT, country TEXT, capacity INTEGER
);
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY, supplier_name TEXT, country TEXT,
    contact_email TEXT, avg_lead_days REAL, reliability_score REAL
);
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT, warehouse_id TEXT, stock_level INTEGER,
    reserved_stock INTEGER, last_updated TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY, product_id TEXT, warehouse_id TEXT,
    supplier_id TEXT, customer_region TEXT,
    order_date TIMESTAMP, expected_ship_date TIMESTAMP,
    actual_ship_date TIMESTAMP, expected_delivery_date TIMESTAMP,
    actual_delivery_date TIMESTAMP,
    quantity INTEGER, status TEXT, delay_days INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS demand_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT, warehouse_id TEXT, date TEXT, demand INTEGER
);
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY, order_id TEXT, carrier TEXT,
    origin_warehouse TEXT, destination_region TEXT, status TEXT,
    shipped_date TIMESTAMP, estimated_arrival TIMESTAMP,
    actual_arrival TIMESTAMP, delay_days INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT, severity TEXT,
    product_id TEXT, warehouse_id TEXT, supplier_id TEXT,
    message TEXT, created_at TIMESTAMP, is_read INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT, warehouse_id TEXT, forecast_date TEXT,
    predicted_demand REAL, lower_bound REAL, upper_bound REAL,
    model_type TEXT DEFAULT "ridge_regression"
);
"""

def init_db():
    """Initialize all tables (SQLite: CREATE IF NOT EXISTS; Db2: CREATE TABLE)."""
    try:
        engine = _get_engine()
        if MODE == "cloud":
            # Db2 does not support IF NOT EXISTS in older versions — use tryexcept per table
            with engine.connect() as conn:
                for stmt in SCHEMA_SQL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            conn.execute(stmt.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"))
                        except Exception:
                            pass  # Table already exists
        else:
            with engine.begin() as conn:
                for stmt in SCHEMA_SQL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(stmt)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"[DB] Init error: {e}")

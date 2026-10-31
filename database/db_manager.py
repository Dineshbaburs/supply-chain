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

# -- Engine factory ------------------------------------------------------------
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
                raise ValueError("DB2 credentials missing in .env  -  switching to local SQLite.")
            url = f"db2+ibm_db://{user}:{pwd}@{host}:{port}/{dbname}"
            engine = _ce(url)
            with engine.connect() as c:
                c.execute("SELECT 1 FROM SYSIBM.SYSDUMMY1")
            print(f"[DB] Connected to IBM Db2  -  {host}:{port}/{dbname}")
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
            p = tuple(params) if isinstance(params, (list, tuple)) else ((params,) if params != () else ())
            conn.exec_driver_sql(query, p)
    except Exception as e:
        print(f"[DB] Write error: {e}\nQuery: {str(query)[:100]}")

def bulk_insert(df, table_name, if_exists="append", chunksize=10000):
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

# -- Schema (DDL) --------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    unit_cost REAL,
    unit_price REAL,
    reorder_point INTEGER,
    reorder_qty INTEGER
);

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id TEXT PRIMARY KEY,
    warehouse_name TEXT,
    region TEXT,
    country TEXT,
    capacity INTEGER
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT,
    country TEXT,
    reliability_score REAL,
    avg_lead_days REAL
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    warehouse_id TEXT,
    stock_level INTEGER,
    reserved_stock INTEGER,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    product_id TEXT,
    warehouse_id TEXT,
    supplier_id TEXT,
    customer_region TEXT,
    order_date TIMESTAMP,
    expected_ship_date TIMESTAMP,
    actual_ship_date TIMESTAMP,
    expected_delivery_date TIMESTAMP,
    actual_delivery_date TIMESTAMP,
    quantity INTEGER,
    status TEXT,
    delay_days INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS demand_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    warehouse_id TEXT,
    date TEXT,
    demand INTEGER
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT,
    carrier TEXT,
    origin_warehouse TEXT,
    destination_region TEXT,
    status TEXT,
    shipped_date TIMESTAMP,
    estimated_arrival TIMESTAMP,
    actual_arrival TIMESTAMP,
    delay_days INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT,
    severity TEXT,
    product_id TEXT,
    warehouse_id TEXT,
    supplier_id TEXT,
    message TEXT,
    created_at TIMESTAMP,
    is_read INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    warehouse_id TEXT,
    forecast_date TEXT,
    predicted_demand REAL,
    lower_bound REAL,
    upper_bound REAL,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS m5_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT,
    cat_id TEXT,
    dept_id TEXT,
    store_id TEXT,
    state_id TEXT,
    forecast_date TEXT,
    actual_demand REAL,
    predicted_demand REAL,
    baseline_demand REAL,
    lower_bound REAL,
    upper_bound REAL,
    model_type TEXT DEFAULT 'ridge_regression'
);

CREATE INDEX IF NOT EXISTS idx_orders_oid ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_pid ON orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_wid ON orders(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_orders_sid ON orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_orders_dt ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_st ON orders(status);
CREATE INDEX IF NOT EXISTS idx_shipments_oid ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_delay ON shipments(delay_days);
CREATE INDEX IF NOT EXISTS idx_demand_pwd ON demand_history(product_id, warehouse_id, date);
CREATE INDEX IF NOT EXISTS idx_inventory_pw ON inventory(product_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_m5_item ON m5_forecasts(item_id, store_id);
"""

def init_db():
    """Initialize all tables (SQLite executescript; Db2 text execution)."""
    try:
        if MODE == "cloud":
            from sqlalchemy import text
            engine = _get_engine()
            with engine.connect() as conn:
                for stmt in SCHEMA_SQL.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            conn.execute(text(stmt.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY")))
                        except Exception:
                            pass
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA_SQL)
            conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"[DB] Init error: {e}")

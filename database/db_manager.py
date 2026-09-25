import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'supply_chain.db')

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
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
            avg_lead_days INTEGER
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
            order_id TEXT PRIMARY KEY,
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
            delay_days INTEGER
        );
        CREATE TABLE IF NOT EXISTS demand_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            warehouse_id TEXT,
            date DATE,
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
            delay_days INTEGER
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT,
            severity TEXT,
            product_id TEXT,
            warehouse_id TEXT,
            supplier_id TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            warehouse_id TEXT,
            forecast_date DATE,
            predicted_demand REAL,
            lower_bound REAL,
            upper_bound REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    print('Database initialized successfully.')

def execute_query(query, params=()):
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

def execute_write(query, params=()):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def bulk_insert(df, table_name, if_exists='append'):
    conn = get_connection()
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()

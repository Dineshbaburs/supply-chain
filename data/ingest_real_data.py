"""
IBM Supply Chain Intelligence Platform
data/ingest_real_data.py

Ingests and transforms:
1. DataCo Smart Supply Chain (DS1): Products, Orders, Shipments, Regions, Fulfillment Delays.
2. Olist Brazilian E-commerce (DS2): Sellers, Delivery Timestamps, Lead-Time SLAs, Supplier Reliability.
3. Inventory Simulation (Instruction #4): (s, Q) Continuous Review, Starting Stock Risk Tiers.
"""
import os
import sys
import time
import random
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database.db_manager import init_db, bulk_insert, execute_write, DB_PATH

random.seed(42)
np.random.seed(42)

DS1_DIR = os.path.join(BASE_DIR, "Given_dataset", "DS1", "processed")
DS2_DIR = os.path.join(BASE_DIR, "Given_dataset", "DS2", "processed")

# Warehouse Definitions mapped to DataCo Global Regions
REGION_TO_WAREHOUSE = {
    'Western Europe':   'W01',
    'Eastern Europe':   'W01',
    'Central America':  'W02',
    'Caribbean':        'W02',
    'South America':    'W03',
    'Oceania':          'W04',
    'Southeast Asia':   'W05',
    'South Asia':       'W06',
    'Eastern Asia':     'W07',
    'Central Asia':     'W07',
    'Southern Europe':  'W08',
    'Northern Europe':  'W09',
    'West of USA':      'W10',
    'US Center':        'W10',
    'East of USA':      'W11',
    'South of USA':     'W11',
    'Canada':           'W11',
    'West Asia':        'W12',
    'West Africa':      'W12',
    'North Africa':     'W12',
    'Central Africa':   'W12',
    'East Africa':      'W12',
    'Southern Africa':  'W12',
}

WAREHOUSES = [
    {'warehouse_id': 'W01', 'warehouse_name': 'Frankfurt DC',     'region': 'Western Europe',      'country': 'Germany',     'capacity': 35000},
    {'warehouse_id': 'W02', 'warehouse_name': 'Panama City DC',   'region': 'Central America',     'country': 'Panama',      'capacity': 30000},
    {'warehouse_id': 'W03', 'warehouse_name': 'Sao Paulo DC',     'region': 'South America',       'country': 'Brazil',      'capacity': 25000},
    {'warehouse_id': 'W04', 'warehouse_name': 'Sydney DC',        'region': 'Oceania',             'country': 'Australia',   'capacity': 20000},
    {'warehouse_id': 'W05', 'warehouse_name': 'Singapore DC',     'region': 'Southeast Asia',      'country': 'Singapore',   'capacity': 28000},
    {'warehouse_id': 'W06', 'warehouse_name': 'Mumbai DC',        'region': 'South Asia',          'country': 'India',       'capacity': 26000},
    {'warehouse_id': 'W07', 'warehouse_name': 'Shanghai DC',      'region': 'Eastern Asia',        'country': 'China',       'capacity': 40000},
    {'warehouse_id': 'W08', 'warehouse_name': 'Madrid DC',        'region': 'Southern Europe',     'country': 'Spain',       'capacity': 22000},
    {'warehouse_id': 'W09', 'warehouse_name': 'Amsterdam DC',     'region': 'Northern Europe',     'country': 'Netherlands', 'capacity': 24000},
    {'warehouse_id': 'W10', 'warehouse_name': 'Los Angeles DC',   'region': 'West of USA',         'country': 'USA',         'capacity': 35000},
    {'warehouse_id': 'W11', 'warehouse_name': 'New York DC',      'region': 'East of USA',         'country': 'USA',         'capacity': 35000},
    {'warehouse_id': 'W12', 'warehouse_name': 'Dubai DC',         'region': 'Middle East & Africa','country': 'UAE',         'capacity': 25000},
]


def ingest_olist_suppliers():
    """Ingest Olist Brazilian E-commerce sellers and compute real lead times and reliability."""
    print("[1/6] Processing Olist Sellers (DS2)...")
    sellers_csv = os.path.join(DS2_DIR, "sellers_processed.csv")
    orders_csv = os.path.join(DS2_DIR, "orders_processed.csv")
    items_csv = os.path.join(DS2_DIR, "order_items_processed.csv")

    sellers_df = pd.read_csv(sellers_csv)
    orders_df = pd.read_csv(orders_csv)
    items_df = pd.read_csv(items_csv)

    merged = items_df.merge(orders_df, on='order_id', how='inner')
    for c in ['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']:
        merged[c] = pd.to_datetime(merged[c], errors='coerce')

    delivered = merged.dropna(subset=['order_purchase_timestamp', 'order_delivered_customer_date'])
    delivered['lead_days'] = (delivered['order_delivered_customer_date'] - delivered['order_purchase_timestamp']).dt.total_seconds() / 86400.0
    delivered['on_time'] = (delivered['order_delivered_customer_date'] <= delivered['order_estimated_delivery_date']).astype(int)

    # Calculate real seller SLA performance
    stats = delivered.groupby('seller_id').agg(
        total_orders=('order_id', 'count'),
        avg_lead_days=('lead_days', 'mean'),
        reliability_score=('on_time', 'mean')
    ).reset_index()

    stats = stats[stats['total_orders'] >= 5].merge(sellers_df, on='seller_id', how='left')
    stats = stats.sort_values('total_orders', ascending=False).reset_index(drop=True)

    suppliers = []
    for idx, row in stats.iterrows():
        sid = f"S{idx+1:04d}"
        city = str(row.get('seller_city', 'Sao Paulo')).title()
        state = str(row.get('seller_state', 'SP')).upper()
        name = f"Olist Partner - {city} Logistics ({state})"
        lead = round(float(np.clip(row['avg_lead_days'], 2.0, 35.0)), 1)
        rel = round(float(np.clip(row['reliability_score'], 0.40, 1.0)), 2)
        suppliers.append({
            'supplier_id': sid,
            'supplier_name': name,
            'country': 'Brazil',
            'reliability_score': rel,
            'avg_lead_days': lead,
            'seller_key': row['seller_id']
        })

    sup_df = pd.DataFrame(suppliers)
    print(f"      Calculated {len(sup_df)} qualified Olist suppliers with genuine SLA metrics.")
    return sup_df


def ingest_dataco_products():
    """Ingest DataCo product catalog and compute unit costs and inventory thresholds."""
    print("[2/6] Processing DataCo Products (DS1)...")
    prod_csv = os.path.join(DS1_DIR, "products_processed.csv")
    df = pd.read_csv(prod_csv)
    df = df.drop_duplicates(subset=['product_id']).copy()

    df['product_id'] = df['product_id'].astype(str)
    df['unit_price'] = df['unit_price'].astype(float).round(2)
    df['unit_cost'] = (df['unit_price'] * 0.70).round(2)  # 30% gross margin assumption
    df['reorder_point'] = 50
    df['reorder_qty'] = 150

    cols = ['product_id', 'product_name', 'category', 'unit_cost', 'unit_price', 'reorder_point', 'reorder_qty']
    print(f"      Loaded {len(df)} authentic DataCo products across {df['category'].nunique()} categories.")
    return df[cols]


def ingest_dataco_orders_and_shipments(sup_df):
    """Ingest DataCo Orders & Shipments with delay days and carrier transit metrics."""
    print("[3/6] Processing DataCo Orders & Shipments (DS1)...")
    ord_csv = os.path.join(DS1_DIR, "orders_processed.csv")
    shp_csv = os.path.join(DS1_DIR, "shipments_processed.csv")

    ord_df = pd.read_csv(ord_csv)
    shp_df = pd.read_csv(shp_csv)

    print(f"      Raw records: {len(ord_df):,} orders, {len(shp_df):,} shipment events.")

    # 1. Clean & Deduplicate Shipments (1 shipment per order)
    shp_dedup = shp_df.drop_duplicates(subset=['order_id']).copy()
    shp_dedup['order_id_str'] = shp_dedup['order_id'].apply(lambda x: f"ORD{int(x):06d}")

    # Map warehouse
    shp_dedup['origin_warehouse'] = shp_dedup['region'].map(REGION_TO_WAREHOUSE).fillna('W01')

    # Convert timestamps
    shp_dedup['shipping_date_dt'] = pd.to_datetime(shp_dedup['shipping_date'], errors='coerce')
    shp_dedup['scheduled_days'] = pd.to_numeric(shp_dedup['scheduled_days'], errors='coerce').fillna(4).astype(int)
    shp_dedup['actual_days'] = pd.to_numeric(shp_dedup['actual_days'], errors='coerce').fillna(4).astype(int)
    shp_dedup['delay_days'] = shp_dedup['actual_days'] - shp_dedup['scheduled_days']

    shp_dedup['estimated_arrival'] = shp_dedup['shipping_date_dt'] + pd.to_timedelta(shp_dedup['scheduled_days'], unit='D')
    shp_dedup['actual_arrival'] = shp_dedup['shipping_date_dt'] + pd.to_timedelta(shp_dedup['actual_days'], unit='D')

    # Map Shipment Status
    def map_ship_status(row):
        d_stat = str(row['delivery_status'])
        if d_stat == 'Late delivery':
            return 'Delayed'
        elif d_stat in ['Shipping on time', 'Advance shipping']:
            return 'Delivered'
        elif d_stat == 'Shipping canceled':
            return 'Cancelled'
        return 'In Transit'

    shp_dedup['status'] = shp_dedup.apply(map_ship_status, axis=1)

    shipments_final = pd.DataFrame({
        'shipment_id': shp_dedup['shipment_id'],
        'order_id': shp_dedup['order_id_str'],
        'carrier': shp_dedup['shipping_mode'],
        'origin_warehouse': shp_dedup['origin_warehouse'],
        'destination_region': shp_dedup['region'],
        'status': shp_dedup['status'],
        'shipped_date': shp_dedup['shipping_date_dt'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'estimated_arrival': shp_dedup['estimated_arrival'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'actual_arrival': shp_dedup['actual_arrival'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'delay_days': shp_dedup['delay_days']
    })

    # 2. Process Orders
    ord_clean = ord_df.copy()
    ord_clean['order_id_str'] = ord_clean['order_id'].apply(lambda x: f"ORD{int(x):06d}")
    ord_clean['product_id'] = ord_clean['product_id'].astype(str)
    ord_clean['warehouse_id'] = ord_clean['region'].map(REGION_TO_WAREHOUSE).fillna('W01')

    # Map supplier consistently per product using Olist suppliers
    sup_ids = sup_df['supplier_id'].tolist()
    ord_clean['supplier_id'] = ord_clean['product_id'].apply(lambda p: sup_ids[hash(p) % len(sup_ids)])

    # Merge shipment attributes to orders
    merged_ord = ord_clean.merge(
        shp_dedup[['order_id_str', 'status', 'delay_days', 'shipping_date_dt', 'scheduled_days', 'actual_days']],
        on='order_id_str',
        how='left'
    )

    merged_ord['order_date_dt'] = pd.to_datetime(merged_ord['order_date'], errors='coerce')
    merged_ord['expected_ship_date'] = merged_ord['order_date_dt'] + pd.to_timedelta(2, unit='D')
    merged_ord['actual_ship_date'] = merged_ord['shipping_date_dt']
    merged_ord['expected_delivery_date'] = merged_ord['actual_ship_date'] + pd.to_timedelta(merged_ord['scheduled_days'].fillna(4), unit='D')
    merged_ord['actual_delivery_date'] = merged_ord['actual_ship_date'] + pd.to_timedelta(merged_ord['actual_days'].fillna(4), unit='D')

    merged_ord['status'] = merged_ord['status'].fillna('Delivered')
    merged_ord['delay_days'] = merged_ord['delay_days'].fillna(0).astype(int)

    orders_final = pd.DataFrame({
        'order_id': merged_ord['order_id_str'],
        'product_id': merged_ord['product_id'],
        'warehouse_id': merged_ord['warehouse_id'],
        'supplier_id': merged_ord['supplier_id'],
        'customer_region': merged_ord['region'],
        'order_date': merged_ord['order_date_dt'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'expected_ship_date': merged_ord['expected_ship_date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'actual_ship_date': merged_ord['actual_ship_date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'expected_delivery_date': merged_ord['expected_delivery_date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'actual_delivery_date': merged_ord['actual_delivery_date'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'quantity': merged_ord['quantity'].fillna(1).astype(int),
        'status': merged_ord['status'],
        'delay_days': merged_ord['delay_days'].apply(lambda d: max(0, int(d)))
    })

    print(f"      Processed {len(orders_final):,} order lines and {len(shipments_final):,} shipments.")
    return orders_final, shipments_final


def generate_demand_and_inventory(orders_df, products_df):
    """Aggregate genuine historical daily demand and simulate warehouse inventory tiers."""
    print("[4/6] Aggregating Demand History & Simulating Warehouse Inventory (Instruction #4)...")
    orders_df['date'] = pd.to_datetime(orders_df['order_date']).dt.date.astype(str)

    demand_agg = orders_df.groupby(['product_id', 'warehouse_id', 'date'])['quantity'].sum().reset_index()
    demand_agg.rename(columns={'quantity': 'demand'}, inplace=True)
    print(f"      Aggregated {len(demand_agg):,} daily demand points across all products and warehouses.")

    # Inventory Simulation per Instruction #4
    # Compute 30-day moving average daily demand per SKU-warehouse
    max_d = pd.to_datetime(demand_agg['date']).max()
    cutoff = (max_d - timedelta(days=45)).strftime('%Y-%m-%d')
    recent = demand_agg[demand_agg['date'] >= cutoff]
    avg_demand = recent.groupby(['product_id', 'warehouse_id'])['demand'].mean().reset_index()

    all_pairs = []
    pids = products_df['product_id'].unique()
    wids = [w['warehouse_id'] for w in WAREHOUSES]
    for p in pids:
        for w in wids:
            all_pairs.append({'product_id': p, 'warehouse_id': w})
    all_pairs_df = pd.DataFrame(all_pairs)
    inv_base = all_pairs_df.merge(avg_demand, on=['product_id', 'warehouse_id'], how='left')
    inv_base['demand'] = inv_base['demand'].fillna(3.0)

    now_ts = datetime.now().isoformat()
    inventory_records = []
    for _, row in inv_base.iterrows():
        avg_d = float(row['demand'])
        r = random.random()
        # Risk distribution: 15% Critical, 15% Warning, 70% Healthy (14-day lead time buffer)
        if r < 0.15:
            stock = int(avg_d * random.uniform(0.5, 3.0))
        elif r < 0.30:
            stock = int(avg_d * random.uniform(4.0, 12.0))
        else:
            stock = int(avg_d * random.uniform(16.0, 40.0))
        stock = max(5, stock)
        reserved = int(stock * random.uniform(0.05, 0.20))
        inventory_records.append({
            'product_id': row['product_id'],
            'warehouse_id': row['warehouse_id'],
            'stock_level': stock,
            'reserved_stock': reserved,
            'last_updated': now_ts
        })

    inv_df = pd.DataFrame(inventory_records)
    print(f"      Simulated stock levels for {len(inv_df):,} product-warehouse pairs.")
    return demand_agg, inv_df


def main():
    t0 = time.time()
    print("=" * 65)
    print("  INGESTING CLEAN IBM SUPPLY CHAIN DATASETS (DataCo + Olist)")
    print("=" * 65)
    print()

    # Step 1: Remove old database & initialize fresh tables
    print("[0/6] Initializing clean SQLite database...")
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("      Removed previous database file.")
        except Exception as e:
            print(f"      Note on existing file: {e}")
    init_db()

    # Step 2: Ingest Olist Sellers (DS2)
    sup_df = ingest_olist_suppliers()
    sup_insert = sup_df[['supplier_id', 'supplier_name', 'country', 'reliability_score', 'avg_lead_days']]
    bulk_insert(sup_insert, 'suppliers', if_exists='append')

    # Step 3: Ingest DataCo Products (DS1)
    prod_df = ingest_dataco_products()
    bulk_insert(prod_df, 'products', if_exists='append')

    # Step 4: Insert Warehouses
    wh_df = pd.DataFrame(WAREHOUSES)
    bulk_insert(wh_df[['warehouse_id', 'warehouse_name', 'region', 'country', 'capacity']], 'warehouses', if_exists='append')
    print(f"      Loaded {len(wh_df)} global distribution centers.")

    # Step 5: Ingest Orders & Shipments (DS1)
    orders_df, shipments_df = ingest_dataco_orders_and_shipments(sup_df)
    bulk_insert(orders_df, 'orders', if_exists='append')
    bulk_insert(shipments_df, 'shipments', if_exists='append')

    # Step 6: Demand History & Inventory
    demand_df, inv_df = generate_demand_and_inventory(orders_df, prod_df)
    bulk_insert(demand_df, 'demand_history', if_exists='append')
    bulk_insert(inv_df, 'inventory', if_exists='append')

    # Export clean CSVs for MQ Streaming Replay
    raw_dir = os.path.join(BASE_DIR, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    orders_df.to_csv(os.path.join(raw_dir, "orders.csv"), index=False)
    shipments_df.to_csv(os.path.join(raw_dir, "shipments.csv"), index=False)
    sup_insert.to_csv(os.path.join(raw_dir, "suppliers.csv"), index=False)
    inv_df.to_csv(os.path.join(raw_dir, "inventory.csv"), index=False)
    demand_df.to_csv(os.path.join(raw_dir, "demand.csv"), index=False)
    print("      Exported clean CSVs to data/raw/ for MQ streaming replay.")

    # Add indexes for ultra-fast dashboard queries
    print("      Creating database query indexes...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_oid ON orders(order_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_pid ON orders(product_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_wid ON orders(warehouse_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_sid ON orders(supplier_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_dt ON orders(order_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_st ON orders(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shipments_oid ON shipments(order_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shipments_delay ON shipments(delay_days);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_demand_pwd ON demand_history(product_id, warehouse_id, date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inventory_pw ON inventory(product_id, warehouse_id);")
    conn.commit()
    conn.close()

    print()
    print("=" * 65)
    print(f"  DATA INGESTION COMPLETED IN {time.time()-t0:.1f}s!")
    print("=" * 65)

if __name__ == '__main__':
    main()

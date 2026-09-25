import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, bulk_insert

random.seed(42)
np.random.seed(42)

CATEGORIES = ['Electronics', 'Apparel', 'Food & Beverage', 'Pharmaceuticals',
              'Industrial', 'Home Goods', 'Automotive', 'Sports']
REGIONS = ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East']
CARRIERS = ['FedEx', 'UPS', 'DHL', 'USPS', 'Maersk', 'MSC Shipping']
PRODUCT_NAMES = {
    'Electronics': ['Laptop', 'Tablet', 'Smartphone', 'Headphones', 'Camera', 'Speaker'],
    'Apparel': ['T-Shirt', 'Jeans', 'Jacket', 'Sneakers', 'Dress', 'Shorts'],
    'Food & Beverage': ['Coffee', 'Tea', 'Juice', 'Snacks', 'Cereal', 'Water'],
    'Pharmaceuticals': ['Vitamin C', 'Paracetamol', 'Ibuprofen', 'Antacid', 'Antibiotic', 'Supplement'],
    'Industrial': ['Drill Bit', 'Wrench Set', 'Bolt Kit', 'Safety Helmet', 'Gloves', 'Cable'],
    'Home Goods': ['Blender', 'Toaster', 'Lamp', 'Pillow', 'Curtains', 'Mug'],
    'Automotive': ['Engine Oil', 'Air Filter', 'Brake Pad', 'Spark Plug', 'Wiper Blade', 'Coolant'],
    'Sports': ['Yoga Mat', 'Dumbbell', 'Running Shoes', 'Water Bottle', 'Resistance Band', 'Gloves']
}

PRODUCTS = []
idx = 1
for cat in CATEGORIES:
    for name in PRODUCT_NAMES[cat]:
        cost = round(random.uniform(5, 500), 2)
        PRODUCTS.append({
            'product_id': f'P{idx:03d}',
            'product_name': f'{name} Pro',
            'category': cat,
            'unit_cost': cost,
            'unit_price': round(cost * random.uniform(1.2, 2.5), 2),
            'reorder_point': random.randint(20, 100),
            'reorder_qty': random.randint(100, 500)
        })
        idx += 1

WAREHOUSES = [
    {'warehouse_id': 'W01', 'warehouse_name': 'Chicago DC', 'region': 'North America', 'country': 'USA', 'capacity': 15000},
    {'warehouse_id': 'W02', 'warehouse_name': 'Los Angeles DC', 'region': 'North America', 'country': 'USA', 'capacity': 12000},
    {'warehouse_id': 'W03', 'warehouse_name': 'London DC', 'region': 'Europe', 'country': 'UK', 'capacity': 10000},
    {'warehouse_id': 'W04', 'warehouse_name': 'Frankfurt DC', 'region': 'Europe', 'country': 'Germany', 'capacity': 11000},
    {'warehouse_id': 'W05', 'warehouse_name': 'Shanghai DC', 'region': 'Asia Pacific', 'country': 'China', 'capacity': 20000},
    {'warehouse_id': 'W06', 'warehouse_name': 'Tokyo DC', 'region': 'Asia Pacific', 'country': 'Japan', 'capacity': 9000},
    {'warehouse_id': 'W07', 'warehouse_name': 'Sao Paulo DC', 'region': 'Latin America', 'country': 'Brazil', 'capacity': 8000},
    {'warehouse_id': 'W08', 'warehouse_name': 'Mexico City DC', 'region': 'Latin America', 'country': 'Mexico', 'capacity': 7500},
    {'warehouse_id': 'W09', 'warehouse_name': 'Dubai DC', 'region': 'Middle East', 'country': 'UAE', 'capacity': 10000},
    {'warehouse_id': 'W10', 'warehouse_name': 'Riyadh DC', 'region': 'Middle East', 'country': 'Saudi Arabia', 'capacity': 8500},
]

SUPPLIER_COMPANIES = [
    'GlobalTech Manufacturing', 'Pacific Rim Exports', 'Euro Logistics Partners',
    'Asia Supply Co', 'Atlantic Trade Corp', 'Southern Cross Industries',
    'Nordic Suppliers Ltd', 'Mideast Trading Co', 'Americas Distribution',
    'Eastern Europe Goods', 'Far East Solutions', 'Western Imports Inc',
    'Central Asia Goods', 'North Star Suppliers', 'Delta Manufacturing',
    'Omega Industrial', 'Premier Supply Chain', 'Apex Distributors',
    'Horizon Logistics', 'Pinnacle Exports'
]
SUPPLIER_COUNTRIES = ['China', 'USA', 'Germany', 'Japan', 'Brazil', 'India', 'South Korea', 'Mexico', 'UK', 'France',
                      'Canada', 'Australia', 'Italy', 'Spain', 'Vietnam', 'Thailand', 'Turkey', 'Netherlands', 'Poland', 'UAE']

SUPPLIERS = []
for i, (name, country) in enumerate(zip(SUPPLIER_COMPANIES, SUPPLIER_COUNTRIES)):
    SUPPLIERS.append({
        'supplier_id': f'S{i+1:03d}',
        'supplier_name': name,
        'country': country,
        'reliability_score': round(random.uniform(0.6, 1.0), 2),
        'avg_lead_days': random.randint(3, 21)
    })

def generate_demand_history(start_date, end_date):
    records = []
    date_range = pd.date_range(start_date, end_date, freq='D')
    print(f'  Generating demand for {len(PRODUCTS)} products x {len(WAREHOUSES)} warehouses x {len(date_range)} days...')
    for prod in PRODUCTS:
        pid = prod['product_id']
        base_demand = random.randint(5, 60)
        trend = random.uniform(-0.005, 0.015)
        for wh in WAREHOUSES:
            wid = wh['warehouse_id']
            region_factor = {'North America': 1.3, 'Europe': 1.1, 'Asia Pacific': 1.5,
                            'Latin America': 0.8, 'Middle East': 0.9}.get(wh['region'], 1.0)
            for day_idx, date in enumerate(date_range):
                doy = date.day_of_year
                seasonal = 1.0 + 0.25 * np.sin(2 * np.pi * doy / 365 - np.pi / 2)
                holiday_bump = 1.0
                if date.month == 12 and date.day >= 15:
                    holiday_bump = 1.4
                elif date.month == 11 and date.day >= 25:
                    holiday_bump = 1.3
                elif date.month in [6, 7]:
                    holiday_bump = 1.1
                noise = np.random.lognormal(0, 0.1)
                demand = max(0, int(base_demand * region_factor * seasonal * holiday_bump * (1 + trend * day_idx) * noise))
                records.append({'product_id': pid, 'warehouse_id': wid, 'date': date.date(), 'demand': demand})
    return pd.DataFrame(records)

def generate_orders(start_date, end_date, n=5000):
    records = []
    date_range = pd.date_range(start_date, end_date, freq='D').tolist()
    status_weights = [0.52, 0.20, 0.14, 0.09, 0.05]
    statuses = ['Delivered', 'In Transit', 'Delayed', 'Processing', 'Cancelled']
    for i in range(n):
        order_date = random.choice(date_range)
        supplier = random.choice(SUPPLIERS)
        lead = supplier['avg_lead_days']
        delay = 0 if random.random() < supplier['reliability_score'] else random.randint(1, 14)
        exp_ship = order_date + timedelta(days=2)
        act_ship = exp_ship + timedelta(days=delay)
        exp_del = exp_ship + timedelta(days=lead)
        act_del = act_ship + timedelta(days=lead + random.randint(0, 3))
        status = random.choices(statuses, weights=status_weights)[0]
        if order_date > (datetime.now() - timedelta(days=7)):
            status = random.choices(['Processing', 'In Transit', 'Delayed'], weights=[0.5, 0.35, 0.15])[0]
        records.append({
            'order_id': f'ORD{i+1:06d}',
            'product_id': random.choice(PRODUCTS)['product_id'],
            'warehouse_id': random.choice(WAREHOUSES)['warehouse_id'],
            'supplier_id': supplier['supplier_id'],
            'customer_region': random.choice(REGIONS),
            'order_date': order_date.isoformat(),
            'expected_ship_date': exp_ship.isoformat(),
            'actual_ship_date': act_ship.isoformat() if status not in ['Processing', 'Cancelled'] else None,
            'expected_delivery_date': exp_del.isoformat(),
            'actual_delivery_date': act_del.isoformat() if status == 'Delivered' else None,
            'quantity': random.randint(10, 300),
            'status': status,
            'delay_days': delay
        })
    return pd.DataFrame(records)

def generate_shipments(orders_df):
    records = []
    for _, row in orders_df.iterrows():
        if row['status'] not in ['Processing', 'Cancelled']:
            records.append({
                'shipment_id': f'SHP{row["order_id"][3:]}',
                'order_id': row['order_id'],
                'carrier': random.choice(CARRIERS),
                'origin_warehouse': row['warehouse_id'],
                'destination_region': row['customer_region'],
                'status': row['status'],
                'shipped_date': row['actual_ship_date'],
                'estimated_arrival': row['expected_delivery_date'],
                'actual_arrival': row['actual_delivery_date'],
                'delay_days': row['delay_days']
            })
    return pd.DataFrame(records)

def generate_inventory(demand_df):
    records = []
    max_date = pd.to_datetime(demand_df['date']).max()
    cutoff = max_date - timedelta(days=30)
    recent = demand_df[pd.to_datetime(demand_df['date']) >= cutoff]
    avg_d = recent.groupby(['product_id', 'warehouse_id'])['demand'].mean().reset_index()
    for _, row in avg_d.iterrows():
        avg = row['demand']
        product = next(p for p in PRODUCTS if p['product_id'] == row['product_id'])
        risk_factor = random.random()
        if risk_factor < 0.15:
            stock = int(avg * random.uniform(0.5, 2))
        elif risk_factor < 0.30:
            stock = int(avg * random.uniform(2, 6))
        else:
            stock = int(avg * random.uniform(6, 25))
        records.append({
            'product_id': row['product_id'],
            'warehouse_id': row['warehouse_id'],
            'stock_level': max(0, stock),
            'reserved_stock': max(0, int(stock * random.uniform(0.05, 0.25))),
            'last_updated': datetime.now().isoformat()
        })
    return pd.DataFrame(records)

def run_simulation():
    print('=== Supply Chain Data Simulator ===')
    print('Initializing database...')
    init_db()
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=730)
    print(f'Simulating data from {start_date} to {end_date}')
    print('Inserting products...')
    bulk_insert(pd.DataFrame(PRODUCTS), 'products', if_exists='replace')
    print(f'  -> {len(PRODUCTS)} products inserted')
    print('Inserting warehouses...')
    bulk_insert(pd.DataFrame(WAREHOUSES), 'warehouses', if_exists='replace')
    print(f'  -> {len(WAREHOUSES)} warehouses inserted')
    print('Inserting suppliers...')
    bulk_insert(pd.DataFrame(SUPPLIERS), 'suppliers', if_exists='replace')
    print(f'  -> {len(SUPPLIERS)} suppliers inserted')
    print('Generating demand history...')
    demand_df = generate_demand_history(start_date, end_date)
    bulk_insert(demand_df, 'demand_history', if_exists='replace')
    print(f'  -> {len(demand_df):,} demand records inserted')
    print('Generating orders...')
    orders_df = generate_orders(start_date, end_date, n=5000)
    bulk_insert(orders_df, 'orders', if_exists='replace')
    print(f'  -> {len(orders_df):,} orders inserted')
    print('Generating shipments...')
    shipments_df = generate_shipments(orders_df)
    bulk_insert(shipments_df, 'shipments', if_exists='replace')
    print(f'  -> {len(shipments_df):,} shipments inserted')
    print('Generating inventory levels...')
    inventory_df = generate_inventory(demand_df)
    bulk_insert(inventory_df, 'inventory', if_exists='replace')
    print(f'  -> {len(inventory_df):,} inventory records inserted')
    print()
    print('=== Simulation Complete! ===')
    return demand_df, orders_df, inventory_df

if __name__ == '__main__':
    run_simulation()

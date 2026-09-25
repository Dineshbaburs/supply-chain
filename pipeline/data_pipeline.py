"""
Data Pipeline - Continuous/scheduled data updates
Simulates a real-time pipeline by replaying orders in date order
and updating the database tables as new "messages" arrive.
"""
import sys
import os
import time
import random
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query, execute_write, bulk_insert

def simulate_pipeline_tick():
    """
    Simulate one pipeline tick:
    - Pick a random recent order
    - Update its status (simulate movement)
    - Update inventory accordingly
    - Return summary of changes
    """
    changes = []

    # Update a random 'Processing' order to 'In Transit'
    proc_orders = execute_query("""
        SELECT order_id, product_id, warehouse_id, quantity
        FROM orders WHERE status = 'Processing'
        ORDER BY RANDOM() LIMIT 3
    """)
    for _, row in proc_orders.iterrows():
        execute_write(
            "UPDATE orders SET status='In Transit', actual_ship_date=? WHERE order_id=?",
            (datetime.now().isoformat(), row['order_id'])
        )
        changes.append(f"Order {row['order_id']} -> In Transit")

    # Update a random 'In Transit' order to 'Delivered'
    transit_orders = execute_query("""
        SELECT order_id, product_id, warehouse_id, quantity
        FROM orders WHERE status = 'In Transit'
        ORDER BY RANDOM() LIMIT 2
    """)
    for _, row in transit_orders.iterrows():
        execute_write(
            "UPDATE orders SET status='Delivered', actual_delivery_date=? WHERE order_id=?",
            (datetime.now().isoformat(), row['order_id'])
        )
        # Reduce inventory
        execute_write("""
            UPDATE inventory SET stock_level = MAX(0, stock_level - ?),
            last_updated = ? WHERE product_id = ? AND warehouse_id = ?
        """, (row['quantity'], datetime.now().isoformat(), row['product_id'], row['warehouse_id']))
        changes.append(f"Order {row['order_id']} -> Delivered")

    # Simulate a new demand record
    products = execute_query("SELECT product_id FROM products ORDER BY RANDOM() LIMIT 1")
    warehouses = execute_query("SELECT warehouse_id FROM warehouses ORDER BY RANDOM() LIMIT 1")
    if not products.empty and not warehouses.empty:
        demand = random.randint(5, 50)
        execute_write(
            "INSERT INTO demand_history (product_id, warehouse_id, date, demand) VALUES (?,?,?,?)",
            (products['product_id'].iloc[0], warehouses['warehouse_id'].iloc[0],
             datetime.now().date().isoformat(), demand)
        )
        changes.append(f"New demand recorded: {demand} units")

    return changes

def run_pipeline_loop(ticks=10, interval_seconds=2):
    """Run the pipeline for N ticks, simulating real-time data flow."""
    print(f"Starting pipeline loop ({ticks} ticks, {interval_seconds}s interval)...")
    for i in range(ticks):
        changes = simulate_pipeline_tick()
        print(f"Tick {i+1}/{ticks}: {len(changes)} changes")
        for c in changes:
            print(f"  -> {c}")
        time.sleep(interval_seconds)
    print("Pipeline loop complete.")

def get_pipeline_stats():
    """Get current pipeline statistics."""
    q = """
        SELECT status, COUNT(*) as count
        FROM orders
        GROUP BY status
    """
    return execute_query(q)

if __name__ == '__main__':
    run_pipeline_loop(ticks=5, interval_seconds=1)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query, execute_write

def get_kpi_summary():
    """Get top-level KPIs for the dashboard header."""
    kpis = {}
    # Total inventory value
    val_q = """
        SELECT SUM(i.stock_level * p.unit_cost) as inventory_value,
               SUM(i.stock_level) as total_units
        FROM inventory i JOIN products p ON i.product_id = p.product_id
    """
    val = execute_query(val_q)
    kpis['inventory_value'] = round(float(val['inventory_value'].iloc[0] or 0), 2)
    kpis['total_units'] = int(val['total_units'].iloc[0] or 0)
    # Order stats (last 30 days)
    ord_q = """
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Delivered' THEN 1 ELSE 0 END) as delivered,
               SUM(CASE WHEN status='Delayed' THEN 1 ELSE 0 END) as delayed,
               SUM(CASE WHEN status='In Transit' THEN 1 ELSE 0 END) as in_transit,
               AVG(CASE WHEN status='Delayed' THEN delay_days ELSE NULL END) as avg_delay
        FROM orders WHERE order_date >= date('now', '-30 days')
    """
    ord_stats = execute_query(ord_q)
    kpis['total_orders_30d'] = int(ord_stats['total'].iloc[0] or 0)
    kpis['delivered_orders'] = int(ord_stats['delivered'].iloc[0] or 0)
    kpis['delayed_orders'] = int(ord_stats['delayed'].iloc[0] or 0)
    kpis['in_transit'] = int(ord_stats['in_transit'].iloc[0] or 0)
    kpis['avg_delay_days'] = round(float(ord_stats['avg_delay'].iloc[0] or 0), 1)
    total = kpis['total_orders_30d']
    kpis['on_time_rate'] = round(kpis['delivered_orders'] / max(total, 1) * 100, 1)
    # Active alerts
    alert_q = "SELECT COUNT(*) as cnt FROM alerts WHERE is_read=0"
    alerts = execute_query(alert_q)
    kpis['active_alerts'] = int(alerts['cnt'].iloc[0] or 0)
    critical_q = "SELECT COUNT(*) as cnt FROM alerts WHERE is_read=0 AND severity='CRITICAL'"
    critical = execute_query(critical_q)
    kpis['critical_alerts'] = int(critical['cnt'].iloc[0] or 0)
    # Supplier count
    sup_q = "SELECT COUNT(*) as cnt FROM suppliers"
    kpis['total_suppliers'] = int(execute_query(sup_q)['cnt'].iloc[0] or 0)
    return kpis

def get_inventory_overview(product_id=None, warehouse_id=None, region=None, category=None):
    conditions = ["1=1"]
    params = []
    if product_id:
        conditions.append("i.product_id = ?")
        params.append(product_id)
    if warehouse_id:
        conditions.append("i.warehouse_id = ?")
        params.append(warehouse_id)
    if region:
        conditions.append("w.region = ?")
        params.append(region)
    if category:
        conditions.append("p.category = ?")
        params.append(category)
    where = " AND ".join(conditions)
    q = f"""
        SELECT i.product_id, i.warehouse_id, i.stock_level, i.reserved_stock,
               (i.stock_level - i.reserved_stock) as available_stock,
               i.last_updated,
               p.product_name, p.category, p.unit_cost, p.unit_price,
               p.reorder_point, p.reorder_qty,
               w.warehouse_name, w.region, w.country, w.capacity,
               (i.stock_level * p.unit_cost) as stock_value
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        WHERE {where}
        ORDER BY available_stock ASC
    """
    return execute_query(q, params=tuple(params))

def get_shipment_status(product_id=None, warehouse_id=None, region=None,
                        supplier_id=None, start_date=None, end_date=None):
    conditions = ["1=1"]
    params = []
    if product_id:
        conditions.append("o.product_id = ?")
        params.append(product_id)
    if warehouse_id:
        conditions.append("s.origin_warehouse = ?")
        params.append(warehouse_id)
    if region:
        conditions.append("s.destination_region = ?")
        params.append(region)
    if supplier_id:
        conditions.append("o.supplier_id = ?")
        params.append(supplier_id)
    if start_date:
        conditions.append("o.order_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("o.order_date <= ?")
        params.append(end_date)
    where = " AND ".join(conditions)
    q = f"""
        SELECT s.shipment_id, s.order_id, s.carrier, s.origin_warehouse,
               s.destination_region, s.status, s.shipped_date,
               s.estimated_arrival, s.actual_arrival, s.delay_days,
               o.product_id, p.product_name, p.category,
               o.quantity, o.supplier_id, sup.supplier_name,
               o.order_date
        FROM shipments s
        JOIN orders o ON s.order_id = o.order_id
        JOIN products p ON o.product_id = p.product_id
        JOIN suppliers sup ON o.supplier_id = sup.supplier_id
        WHERE {where}
        ORDER BY s.delay_days DESC, o.order_date DESC
        LIMIT 500
    """
    return execute_query(q, params=tuple(params))

def get_demand_trends(product_id=None, warehouse_id=None, region=None,
                      start_date=None, end_date=None, freq='W'):
    conditions = ["1=1"]
    params = []
    if product_id:
        conditions.append("dh.product_id = ?")
        params.append(product_id)
    if warehouse_id:
        conditions.append("dh.warehouse_id = ?")
        params.append(warehouse_id)
    if region:
        conditions.append("w.region = ?")
        params.append(region)
    if start_date:
        conditions.append("dh.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("dh.date <= ?")
        params.append(end_date)
    where = " AND ".join(conditions)
    q = f"""
        SELECT dh.date, dh.demand, dh.product_id, dh.warehouse_id,
               p.product_name, p.category, w.region
        FROM demand_history dh
        JOIN products p ON dh.product_id = p.product_id
        JOIN warehouses w ON dh.warehouse_id = w.warehouse_id
        WHERE {where}
        ORDER BY dh.date
    """
    df = execute_query(q, params=tuple(params))
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_lead_time_analysis(supplier_id=None, region=None, start_date=None, end_date=None):
    conditions = ["o.status = 'Delivered'"]
    params = []
    if supplier_id:
        conditions.append("o.supplier_id = ?")
        params.append(supplier_id)
    if region:
        conditions.append("o.customer_region = ?")
        params.append(region)
    if start_date:
        conditions.append("o.order_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("o.order_date <= ?")
        params.append(end_date)
    where = " AND ".join(conditions)
    q = f"""
        SELECT o.order_id, o.supplier_id, sup.supplier_name, o.customer_region,
               o.order_date, o.expected_delivery_date, o.actual_delivery_date,
               CAST(julianday(o.actual_delivery_date) - julianday(o.order_date) AS INTEGER) as actual_lead_days,
               CAST(julianday(o.expected_delivery_date) - julianday(o.order_date) AS INTEGER) as expected_lead_days,
               o.delay_days, p.category, p.product_name
        FROM orders o
        JOIN suppliers sup ON o.supplier_id = sup.supplier_id
        JOIN products p ON o.product_id = p.product_id
        WHERE {where}
        ORDER BY o.order_date DESC
        LIMIT 1000
    """
    return execute_query(q, params=tuple(params))

def get_order_fulfillment_rate(group_by='status', start_date=None, end_date=None):
    conditions = ["1=1"]
    params = []
    if start_date:
        conditions.append("order_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("order_date <= ?")
        params.append(end_date)
    where = " AND ".join(conditions)
    if group_by == 'status':
        q = f"SELECT status, COUNT(*) as count FROM orders WHERE {where} GROUP BY status"
    elif group_by == 'region':
        q = f"SELECT customer_region as region, status, COUNT(*) as count FROM orders WHERE {where} GROUP BY customer_region, status"
    elif group_by == 'supplier':
        q = f"""SELECT sup.supplier_name, o.status, COUNT(*) as count
                FROM orders o JOIN suppliers sup ON o.supplier_id=sup.supplier_id
                WHERE {where} GROUP BY sup.supplier_name, o.status"""
    elif group_by == 'date':
        q = f"""SELECT strftime('%Y-%W', order_date) as week, status, COUNT(*) as count
                FROM orders WHERE {where} GROUP BY week, status ORDER BY week"""
    else:
        q = f"SELECT status, COUNT(*) as count FROM orders WHERE {where} GROUP BY status"
    return execute_query(q, params=tuple(params))

def get_supplier_performance():
    q = """
        SELECT s.supplier_id, s.supplier_name, s.country, s.reliability_score, s.avg_lead_days,
               COUNT(o.order_id) as total_orders,
               SUM(CASE WHEN o.status='Delivered' THEN 1 ELSE 0 END) as delivered,
               SUM(CASE WHEN o.status='Delayed' THEN 1 ELSE 0 END) as delayed,
               SUM(CASE WHEN o.status='Cancelled' THEN 1 ELSE 0 END) as cancelled,
               AVG(CASE WHEN o.delay_days > 0 THEN o.delay_days ELSE NULL END) as avg_delay_days,
               SUM(o.quantity * p.unit_price) as total_order_value
        FROM suppliers s
        LEFT JOIN orders o ON s.supplier_id = o.supplier_id
        LEFT JOIN products p ON o.product_id = p.product_id
        GROUP BY s.supplier_id
        ORDER BY delayed DESC
    """
    df = execute_query(q)
    df['on_time_rate'] = (df['delivered'] / df['total_orders'].clip(lower=1) * 100).round(1)
    df['delay_rate'] = (df['delayed'] / df['total_orders'].clip(lower=1) * 100).round(1)
    return df

def get_warehouse_utilization():
    q = """
        SELECT w.warehouse_id, w.warehouse_name, w.region, w.capacity,
               SUM(i.stock_level) as current_stock,
               COUNT(DISTINCT i.product_id) as product_count,
               SUM(i.stock_level * p.unit_cost) as stock_value
        FROM warehouses w
        LEFT JOIN inventory i ON w.warehouse_id = i.warehouse_id
        LEFT JOIN products p ON i.product_id = p.product_id
        GROUP BY w.warehouse_id
    """
    df = execute_query(q)
    df['utilization_pct'] = (df['current_stock'] / df['capacity'].clip(lower=1) * 100).round(1)
    return df

def get_actionable_insights(stockout_df=None):
    insights = []
    # Items needing replenishment
    replen_q = """
        SELECT p.product_name, p.category, w.warehouse_name, w.region,
               i.stock_level, p.reorder_point, p.reorder_qty,
               i.stock_level - p.reorder_point as stock_gap
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        WHERE i.stock_level <= p.reorder_point
        ORDER BY (i.stock_level - p.reorder_point) ASC
        LIMIT 15
    """
    replen = execute_query(replen_q)
    if not replen.empty:
        insights.append({
            'type': 'REPLENISHMENT',
            'title': f'{len(replen)} Items Need Immediate Replenishment',
            'data': replen,
            'priority': 'CRITICAL'
        })
    # Top delayed shipments
    delay_q = """
        SELECT p.product_name, s.carrier, s.destination_region, s.delay_days,
               sup.supplier_name
        FROM shipments s
        JOIN orders o ON s.order_id = o.order_id
        JOIN products p ON o.product_id = p.product_id
        JOIN suppliers sup ON o.supplier_id = sup.supplier_id
        WHERE s.status = 'Delayed'
        ORDER BY s.delay_days DESC LIMIT 10
    """
    delays = execute_query(delay_q)
    if not delays.empty:
        insights.append({
            'type': 'DELAYS',
            'title': f'Top {len(delays)} Most Delayed Shipments',
            'data': delays,
            'priority': 'HIGH'
        })
    # Lead time reduction opportunities
    lead_q = """
        SELECT sup.supplier_name, sup.country, 
               AVG(CAST(julianday(o.actual_delivery_date) - julianday(o.order_date) AS REAL)) as avg_lead_time,
               AVG(CAST(julianday(o.expected_delivery_date) - julianday(o.order_date) AS REAL)) as expected_lead_time,
               COUNT(*) as order_count
        FROM orders o
        JOIN suppliers sup ON o.supplier_id = sup.supplier_id
        WHERE o.status = 'Delivered'
        GROUP BY sup.supplier_id
        HAVING order_count >= 10
        ORDER BY avg_lead_time DESC
        LIMIT 5
    """
    lead_times = execute_query(lead_q)
    if not lead_times.empty:
        insights.append({
            'type': 'LEAD_TIME',
            'title': 'Top 5 Suppliers with Longest Lead Times',
            'data': lead_times,
            'priority': 'MEDIUM'
        })
    return insights

if __name__ == '__main__':
    kpis = get_kpi_summary()
    print("KPIs:", kpis)

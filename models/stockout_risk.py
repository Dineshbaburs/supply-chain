import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query, bulk_insert, execute_write

def calculate_stockout_risk(lead_time_days=14, service_level=0.95):
    """
    Stockout risk = P(demand_in_lead_time > current_stock)
    Uses historical demand variance and current stock level.
    Returns a DataFrame with risk scores for all product-warehouse combos.
    """
    print("Calculating stockout risk...")
    inventory_q = """
        SELECT i.product_id, i.warehouse_id, i.stock_level, i.reserved_stock,
               p.product_name, p.category, p.reorder_point, p.reorder_qty,
               w.region, w.warehouse_name
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        JOIN warehouses w ON i.warehouse_id = w.warehouse_id
    """
    inventory_df = execute_query(inventory_q)
    demand_stats_q = """
        SELECT product_id, warehouse_id,
               AVG(demand) as avg_daily_demand,
               SUM(demand * demand) / COUNT(*) - (AVG(demand) * AVG(demand)) as demand_variance,
               MAX(demand) as max_demand,
               MIN(demand) as min_demand,
               COUNT(*) as days_observed
        FROM demand_history
        WHERE date >= date('now', '-90 days')
        GROUP BY product_id, warehouse_id
    """
    demand_stats = execute_query(demand_stats_q)
    merged = inventory_df.merge(demand_stats, on=['product_id', 'warehouse_id'], how='left')
    merged['avg_daily_demand'] = merged['avg_daily_demand'].fillna(10)
    merged['demand_variance'] = merged['demand_variance'].fillna(25).clip(lower=1)
    merged['available_stock'] = merged['stock_level'] - merged['reserved_stock']
    merged['available_stock'] = merged['available_stock'].clip(lower=0)
    # Expected demand over lead time
    merged['expected_lead_demand'] = merged['avg_daily_demand'] * lead_time_days
    merged['demand_std'] = np.sqrt(merged['demand_variance'] * lead_time_days)
    # Z-score: how many standard deviations above expected demand is current stock
    merged['z_score'] = np.where(
        merged['demand_std'] > 0,
        (merged['available_stock'] - merged['expected_lead_demand']) / merged['demand_std'],
        np.where(merged['available_stock'] >= merged['expected_lead_demand'], 3.0, -3.0)
    )
    from scipy import stats
    merged['stockout_probability'] = 1 - stats.norm.cdf(merged['z_score'])
    merged['stockout_probability'] = merged['stockout_probability'].clip(0, 1)
    # Days of stock remaining
    merged['days_of_stock'] = np.where(
        merged['avg_daily_demand'] > 0,
        merged['available_stock'] / merged['avg_daily_demand'],
        999
    )
    # Risk category
    def risk_category(prob):
        if prob >= 0.70:
            return 'CRITICAL'
        elif prob >= 0.40:
            return 'HIGH'
        elif prob >= 0.20:
            return 'MEDIUM'
        else:
            return 'LOW'
    merged['risk_category'] = merged['stockout_probability'].apply(risk_category)
    # Safety stock recommendation
    from scipy.stats import norm
    z_service = norm.ppf(service_level)
    merged['safety_stock_recommended'] = (z_service * merged['demand_std']).clip(lower=0).round()
    # Replenishment recommendation
    merged['needs_replenishment'] = (
        (merged['available_stock'] <= merged['reorder_point']) |
        (merged['stockout_probability'] >= 0.40)
    )
    merged['replenishment_qty'] = np.where(
        merged['needs_replenishment'],
        merged['reorder_qty'],
        0
    )
    result_cols = [
        'product_id', 'warehouse_id', 'product_name', 'category',
        'warehouse_name', 'region', 'stock_level', 'reserved_stock',
        'available_stock', 'avg_daily_demand', 'expected_lead_demand',
        'days_of_stock', 'stockout_probability', 'risk_category',
        'safety_stock_recommended', 'needs_replenishment', 'replenishment_qty',
        'reorder_point', 'reorder_qty'
    ]
    result = merged[result_cols].copy()
    result['days_of_stock'] = result['days_of_stock'].round(1)
    result['stockout_probability'] = result['stockout_probability'].round(4)
    result['avg_daily_demand'] = result['avg_daily_demand'].round(2)
    result['expected_lead_demand'] = result['expected_lead_demand'].round(2)
    print(f"  -> Stockout risk calculated for {len(result):,} product-warehouse combinations")
    critical = len(result[result['risk_category'] == 'CRITICAL'])
    high = len(result[result['risk_category'] == 'HIGH'])
    print(f"  -> CRITICAL: {critical}, HIGH: {high}")
    return result

def detect_supply_chain_bottlenecks():
    """Detect bottlenecks in the supply chain based on delays and supplier performance."""
    supplier_perf_q = """
        SELECT s.supplier_id, s.supplier_name, s.country, s.reliability_score, s.avg_lead_days,
               COUNT(o.order_id) as total_orders,
               SUM(CASE WHEN o.status = 'Delayed' THEN 1 ELSE 0 END) as delayed_orders,
               AVG(o.delay_days) as avg_delay_days,
               SUM(CASE WHEN o.status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_orders
        FROM suppliers s
        LEFT JOIN orders o ON s.supplier_id = o.supplier_id
        GROUP BY s.supplier_id
    """
    supplier_perf = execute_query(supplier_perf_q)
    supplier_perf['delay_rate'] = (supplier_perf['delayed_orders'] / supplier_perf['total_orders'].clip(lower=1)).round(4)
    supplier_perf['bottleneck_score'] = (
        supplier_perf['delay_rate'] * 0.5 +
        (supplier_perf['avg_delay_days'].fillna(0) / 14) * 0.3 +
        ((1 - supplier_perf['reliability_score']) * 0.2)
    ).round(4)
    supplier_perf['is_bottleneck'] = supplier_perf['bottleneck_score'] > 0.3
    regional_q = """
        SELECT customer_region,
               COUNT(*) as total_shipments,
               SUM(CASE WHEN status = 'Delayed' THEN 1 ELSE 0 END) as delayed,
               AVG(delay_days) as avg_delay
        FROM shipments
        GROUP BY customer_region
    """
    regional = execute_query(regional_q)
    regional['delay_rate'] = (regional['delayed'] / regional['total_shipments'].clip(lower=1)).round(4)
    return supplier_perf, regional

def estimate_delay_impact(days_ahead=30):
    """Estimate financial and operational impact of current delays."""
    delayed_q = """
        SELECT o.order_id, o.product_id, o.warehouse_id, o.quantity, o.delay_days,
               p.unit_price, p.unit_cost, w.region
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        JOIN warehouses w ON o.warehouse_id = w.warehouse_id
        WHERE o.status = 'Delayed'
    """
    delayed = execute_query(delayed_q)
    if delayed.empty:
        return pd.DataFrame(), {'total_value_at_risk': 0, 'total_orders': 0}
    delayed['order_value'] = delayed['quantity'] * delayed['unit_price']
    delayed['holding_cost'] = delayed['quantity'] * delayed['unit_cost'] * 0.002 * delayed['delay_days']
    delayed['lost_margin'] = delayed['order_value'] * 0.05 * (delayed['delay_days'] / 7)
    delayed['total_impact'] = delayed['holding_cost'] + delayed['lost_margin']
    summary = {
        'total_value_at_risk': round(delayed['order_value'].sum(), 2),
        'total_holding_cost': round(delayed['holding_cost'].sum(), 2),
        'total_lost_margin': round(delayed['lost_margin'].sum(), 2),
        'total_financial_impact': round(delayed['total_impact'].sum(), 2),
        'total_orders': len(delayed),
        'avg_delay_days': round(delayed['delay_days'].mean(), 1)
    }
    return delayed, summary

if __name__ == '__main__':
    risk_df = calculate_stockout_risk()
    print(risk_df[['product_id', 'warehouse_id', 'stockout_probability', 'risk_category']].head(10))

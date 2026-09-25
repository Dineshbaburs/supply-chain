import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query, bulk_insert, execute_write

ALERT_THRESHOLDS = {
    'low_stock_days': 7,
    'critical_stock_days': 3,
    'stockout_high': 0.40,
    'stockout_critical': 0.70,
    'delay_high': 5,
    'delay_critical': 10,
    'supplier_delay_rate': 0.25,
    'supplier_reliability_low': 0.70
}

def generate_alerts(stockout_df=None):
    """Generate all types of alerts and store them in the database."""
    execute_write("DELETE FROM alerts WHERE is_read = 0", ())
    all_alerts = []
    # 1. Low stock / stockout alerts
    if stockout_df is None:
        inv_q = """
            SELECT i.product_id, i.warehouse_id, i.stock_level, i.reserved_stock,
                   p.product_name, p.reorder_point,
                   w.warehouse_name, w.region
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        """
        stockout_df = execute_query(inv_q)
        stockout_df['available_stock'] = (stockout_df['stock_level'] - stockout_df['reserved_stock']).clip(lower=0)
        stockout_df['stockout_probability'] = 0.1
        stockout_df['days_of_stock'] = stockout_df['available_stock'] / 10
        stockout_df['risk_category'] = 'LOW'
    for _, row in stockout_df.iterrows():
        if row.get('risk_category') == 'CRITICAL' or row.get('stockout_probability', 0) >= ALERT_THRESHOLDS['stockout_critical']:
            all_alerts.append({
                'alert_type': 'STOCKOUT_CRITICAL',
                'severity': 'CRITICAL',
                'product_id': row['product_id'],
                'warehouse_id': row['warehouse_id'],
                'supplier_id': None,
                'message': (f"CRITICAL STOCKOUT RISK: {row['product_name']} at {row['warehouse_name']} "
                           f"({row['region']}). Stock: {int(row['stock_level'])} units, "
                           f"Risk: {row.get('stockout_probability', 0)*100:.0f}%, "
                           f"Days remaining: {row.get('days_of_stock', 0):.1f}")
            })
        elif row.get('risk_category') == 'HIGH' or row.get('stockout_probability', 0) >= ALERT_THRESHOLDS['stockout_high']:
            all_alerts.append({
                'alert_type': 'STOCKOUT_HIGH',
                'severity': 'HIGH',
                'product_id': row['product_id'],
                'warehouse_id': row['warehouse_id'],
                'supplier_id': None,
                'message': (f"HIGH STOCKOUT RISK: {row['product_name']} at {row['warehouse_name']}. "
                           f"Stock: {int(row['stock_level'])} units, "
                           f"Days remaining: {row.get('days_of_stock', 0):.1f}")
            })
        elif row.get('days_of_stock', 999) <= ALERT_THRESHOLDS['low_stock_days']:
            all_alerts.append({
                'alert_type': 'LOW_STOCK',
                'severity': 'MEDIUM',
                'product_id': row['product_id'],
                'warehouse_id': row['warehouse_id'],
                'supplier_id': None,
                'message': (f"LOW STOCK: {row['product_name']} at {row['warehouse_name']}. "
                           f"Only {int(row['stock_level'])} units left ({row.get('days_of_stock', 0):.1f} days of supply).")
            })
    # 2. Delayed shipment alerts
    delayed_q = """
        SELECT s.shipment_id, s.order_id, s.delay_days, s.destination_region,
               s.carrier, s.origin_warehouse,
               o.product_id, p.product_name
        FROM shipments s
        JOIN orders o ON s.order_id = o.order_id
        JOIN products p ON o.product_id = p.product_id
        WHERE s.status = 'Delayed' AND s.delay_days > 0
        ORDER BY s.delay_days DESC
        LIMIT 50
    """
    delayed = execute_query(delayed_q)
    for _, row in delayed.iterrows():
        severity = 'CRITICAL' if row['delay_days'] >= ALERT_THRESHOLDS['delay_critical'] else 'HIGH'
        all_alerts.append({
            'alert_type': 'SHIPMENT_DELAY',
            'severity': severity,
            'product_id': row['product_id'],
            'warehouse_id': row['origin_warehouse'],
            'supplier_id': None,
            'message': (f"SHIPMENT DELAYED: {row['product_name']} shipment {row['shipment_id']} "
                       f"via {row['carrier']} to {row['destination_region']} "
                       f"is delayed by {int(row['delay_days'])} days.")
        })
    # 3. Supplier disruption alerts
    supplier_q = """
        SELECT s.supplier_id, s.supplier_name, s.reliability_score,
               COUNT(o.order_id) as total,
               SUM(CASE WHEN o.status='Delayed' THEN 1 ELSE 0 END) as delayed,
               AVG(o.delay_days) as avg_delay
        FROM suppliers s
        JOIN orders o ON s.supplier_id = o.supplier_id
        WHERE o.order_date >= date('now', '-60 days')
        GROUP BY s.supplier_id
        HAVING total > 2
    """
    suppliers = execute_query(supplier_q)
    for _, row in suppliers.iterrows():
        delay_rate = row['delayed'] / max(row['total'], 1)
        if delay_rate >= ALERT_THRESHOLDS['supplier_delay_rate'] or row['reliability_score'] < ALERT_THRESHOLDS['supplier_reliability_low']:
            severity = 'CRITICAL' if delay_rate >= 0.5 else 'HIGH'
            all_alerts.append({
                'alert_type': 'SUPPLIER_DISRUPTION',
                'severity': severity,
                'product_id': None,
                'warehouse_id': None,
                'supplier_id': row['supplier_id'],
                'message': (f"SUPPLIER DISRUPTION: {row['supplier_name']} has a "
                           f"{delay_rate*100:.0f}% delay rate "
                           f"({int(row['delayed'])}/{int(row['total'])} orders delayed) "
                           f"with avg {row['avg_delay']:.1f} days delay. "
                           f"Reliability score: {row['reliability_score']:.2f}")
            })
    # 4. Demand spike alerts
    demand_q = """
        SELECT d.product_id, d.warehouse_id, p.product_name, w.warehouse_name,
               AVG(d.demand) as recent_avg,
               (SELECT AVG(d2.demand) FROM demand_history d2
                WHERE d2.product_id = d.product_id AND d2.warehouse_id = d.warehouse_id
                AND d2.date < date('now', '-30 days')
                AND d2.date >= date('now', '-90 days')) as baseline_avg
        FROM demand_history d
        JOIN products p ON d.product_id = p.product_id
        JOIN warehouses w ON d.warehouse_id = w.warehouse_id
        WHERE d.date >= date('now', '-14 days')
        GROUP BY d.product_id, d.warehouse_id
    """
    demand_spikes = execute_query(demand_q)
    demand_spikes = demand_spikes.dropna()
    demand_spikes['spike_ratio'] = demand_spikes['recent_avg'] / demand_spikes['baseline_avg'].clip(lower=0.1)
    for _, row in demand_spikes[demand_spikes['spike_ratio'] > 1.5].iterrows():
        all_alerts.append({
            'alert_type': 'DEMAND_SPIKE',
            'severity': 'MEDIUM',
            'product_id': row['product_id'],
            'warehouse_id': row['warehouse_id'],
            'supplier_id': None,
            'message': (f"DEMAND SPIKE: {row['product_name']} at {row['warehouse_name']} "
                       f"shows {row['spike_ratio']:.1f}x demand increase. "
                       f"Recent avg: {row['recent_avg']:.0f}/day vs baseline {row['baseline_avg']:.0f}/day.")
        })
    if all_alerts:
        alerts_df = pd.DataFrame(all_alerts)
        alerts_df['created_at'] = datetime.now().isoformat()
        alerts_df['is_read'] = 0
        bulk_insert(alerts_df, 'alerts', if_exists='append')
    print(f"Generated {len(all_alerts)} alerts")
    return len(all_alerts)

def get_active_alerts(severity=None, alert_type=None, limit=100):
    conditions = ["is_read = 0"]
    params = []
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if alert_type:
        conditions.append("alert_type = ?")
        params.append(alert_type)
    where = " AND ".join(conditions)
    q = f"""
        SELECT id, alert_type, severity, product_id, warehouse_id, supplier_id,
               message, created_at
        FROM alerts
        WHERE {where}
        ORDER BY
            CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT {limit}
    """
    return execute_query(q, params=tuple(params))

def mark_alert_read(alert_id):
    execute_write("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))

def get_alert_summary():
    q = """
        SELECT severity, alert_type, COUNT(*) as count
        FROM alerts WHERE is_read = 0
        GROUP BY severity, alert_type
        ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END
    """
    return execute_query(q)

if __name__ == '__main__':
    n = generate_alerts()
    print(f'Generated {n} alerts')
    alerts = get_active_alerts()
    print(alerts[['alert_type', 'severity', 'message']].head(10))

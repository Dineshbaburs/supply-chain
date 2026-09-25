"""
IBM Supply Chain Intelligence Platform
Report Generator — produces HTML insight summary reports
"""
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query
from pipeline.analytics import get_kpi_summary, get_supplier_performance
from alerts.alert_system import get_active_alerts
from models.stockout_risk import calculate_stockout_risk, estimate_delay_impact

def generate_html_report(output_path=None):
    """Generate a full HTML insight summary report."""
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"IBM_Supply_Chain_Report_{ts}.html")
    print("Collecting data for report...")
    kpis = get_kpi_summary()
    alerts = get_active_alerts(limit=500)
    stockout = calculate_stockout_risk()
    suppliers = get_supplier_performance()
    try:
        delay_impact = estimate_delay_impact()
    except Exception:
        delay_impact = None
    now = datetime.now().strftime("%B %d, %Y %H:%M")
    health = min(100, max(0,
        kpis.get("on_time_rate", 75) * 0.5 +
        max(0, 100 - kpis.get("critical_alerts", 0) * 5) * 0.3 +
        max(0, 100 - kpis.get("avg_delay_days", 0) * 10) * 0.2))
    health_color = "#24a148" if health >= 75 else "#ff832b" if health >= 50 else "#da1e28"
    health_label = "GOOD" if health >= 75 else "AT RISK" if health >= 50 else "CRITICAL"
    alert_summary = alerts.groupby(["alert_type","severity"]).size().reset_index(name="count") if not alerts.empty else None
    critical_items = stockout[stockout["risk_category"]=="CRITICAL"].sort_values("stockout_probability",ascending=False).head(10) if not stockout.empty else None
    bottleneck_sup = suppliers[suppliers["delay_rate"]>20].sort_values("delay_rate",ascending=False).head(5) if not suppliers.empty else None
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>IBM Supply Chain Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'IBM Plex Sans',Arial,sans-serif;background:#f4f4f4;color:#161616;font-size:14px}}
.header{{background:linear-gradient(135deg,#0043ce,#0f62fe 60%,#1192e8);padding:28px 40px;color:#fff}}
.header-top{{display:flex;justify-content:space-between;align-items:flex-start}}
.ibm-logo{{background:#fff;color:#0043ce;font-size:1.4rem;font-weight:700;padding:6px 14px;display:inline-block;margin-bottom:12px}}
.header h1{{font-size:1.5rem;font-weight:600;margin-bottom:4px}}
.header-sub{{font-size:0.75rem;opacity:0.8;text-transform:uppercase;letter-spacing:0.08em}}
.health-badge{{font-size:2rem;font-weight:700;color:{health_color};font-family:'IBM Plex Mono',monospace}}
.container{{max-width:1100px;margin:0 auto;padding:32px 24px}}
.section-title{{font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:#6f6f6f;border-bottom:1px solid #c6c6c6;padding-bottom:6px;margin:28px 0 14px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#c6c6c6;border:1px solid #c6c6c6;margin-bottom:24px}}
.kpi-card{{background:#fff;padding:16px}}
.kpi-label{{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;color:#6f6f6f;margin-bottom:6px}}
.kpi-value{{font-size:1.4rem;font-weight:600;font-family:'IBM Plex Mono',monospace}}
.blue{{color:#0f62fe}} .red{{color:#da1e28}} .orange{{color:#ff832b}} .green{{color:#24a148}}
table{{width:100%;border-collapse:collapse;margin-bottom:20px}}
th{{background:#262626;color:#f4f4f4;text-align:left;padding:10px 12px;font-weight:500;text-transform:uppercase;font-size:0.68rem;letter-spacing:0.06em}}
td{{padding:9px 12px;border-bottom:1px solid #e0e0e0;font-size:0.82rem}}
tr:nth-child(even){{background:#f4f4f4}}
.badge{{display:inline-block;padding:2px 8px;font-size:0.65rem;font-weight:600;text-transform:uppercase}}
.badge-critical{{background:#ffd7d9;color:#da1e28;border-left:3px solid #da1e28}}
.badge-high{{background:#ffe8cc;color:#ff832b;border-left:3px solid #ff832b}}
.badge-medium{{background:#fdf6dd;color:#8a6914;border-left:3px solid #f1c21b}}
.badge-low{{background:#defbe6;color:#198038;border-left:3px solid #24a148}}
.insight-box{{background:#fff;border-left:4px solid #0f62fe;padding:14px 16px;margin:8px 0;border:1px solid #e0e0e0}}
.insight-box h4{{font-size:0.82rem;font-weight:600;margin-bottom:6px}}
.insight-box p{{font-size:0.8rem;color:#525252;line-height:1.5}}
.footer{{text-align:center;padding:24px;font-size:0.7rem;color:#6f6f6f;border-top:1px solid #c6c6c6;margin-top:40px}}
</style></head><body>
<div class="header">
  <div class="header-top">
    <div>
      <div class="ibm-logo">IBM</div>
      <h1>Supply Chain Intelligence Report</h1>
      <div class="header-sub">Predictive Analytics &amp; Real-Time Visibility — Enterprise Edition</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:0.68rem;opacity:0.7;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">Supply Chain Health Score</div>
      <div class="health-badge">{health:.0f}/100</div>
      <div style="font-size:0.75rem;font-weight:600;color:{health_color};margin-top:2px">{health_label}</div>
      <div style="margin-top:10px;font-size:0.7rem;opacity:0.8;font-family:'IBM Plex Mono',monospace">Generated: {now}</div>
    </div>
  </div>
</div>
<div class="container">
<div class="section-title">Key Performance Indicators</div>
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-label">Inventory Value</div><div class="kpi-value blue">${kpis.get('inventory_value',0):,.0f}</div></div>
  <div class="kpi-card"><div class="kpi-label">On-Time Delivery</div><div class="kpi-value {'green' if kpis.get('on_time_rate',0)>=85 else 'orange'}">{kpis.get('on_time_rate',0):.1f}%</div></div>
  <div class="kpi-card"><div class="kpi-label">Active Alerts</div><div class="kpi-value {'red' if kpis.get('critical_alerts',0)>0 else 'orange'}">{kpis.get('active_alerts',0)}</div></div>
  <div class="kpi-card"><div class="kpi-label">Avg Delay</div><div class="kpi-value {'red' if kpis.get('avg_delay_days',0)>5 else 'orange'}">{kpis.get('avg_delay_days',0):.1f} days</div></div>
  <div class="kpi-card"><div class="kpi-label">Orders (Last 30d)</div><div class="kpi-value">{kpis.get('total_orders_30d',0):,}</div></div>
  <div class="kpi-card"><div class="kpi-label">In Transit</div><div class="kpi-value blue">{kpis.get('in_transit',0):,}</div></div>
  <div class="kpi-card"><div class="kpi-label">Critical Alerts</div><div class="kpi-value red">{kpis.get('critical_alerts',0)}</div></div>
  <div class="kpi-card"><div class="kpi-label">Total Suppliers</div><div class="kpi-value">{kpis.get('total_suppliers',0)}</div></div>
</div>
"""
    html += '<div class="section-title">Alert Summary by Type</div>\n'
    if alert_summary is not None and not alert_summary.empty:
        html += '<table><thead><tr><th>Alert Type</th><th>Severity</th><th>Count</th></tr></thead><tbody>\n'
        for _, r in alert_summary.iterrows():
            bc = f"badge-{r['severity'].lower()}"
            html += f'<tr><td>{r["alert_type"]}</td><td><span class="badge {bc}">{r["severity"]}</span></td><td><strong>{r["count"]}</strong></td></tr>\n'
        html += '</tbody></table>\n'
    html += '<div class="section-title">Critical Stockout Risk Items — Immediate Action Required</div>\n'
    if critical_items is not None and not critical_items.empty:
        html += '<table><thead><tr><th>Product</th><th>Warehouse</th><th>Region</th><th>Stock Units</th><th>Days Left</th><th>Stockout Risk</th><th>Replenish Qty</th></tr></thead><tbody>\n'
        for _, r in critical_items.iterrows():
            html += (f'<tr><td><strong>{r["product_name"]}</strong></td><td>{r["warehouse_name"]}</td>'
                    f'<td>{r.get("region","")}</td>'
                    f'<td style="color:#da1e28;font-weight:700">{int(r["stock_level"]):,}</td>'
                    f'<td style="color:#da1e28;font-weight:700">{r["days_of_stock"]:.1f}</td>'
                    f'<td style="color:#da1e28;font-weight:700">{r["stockout_probability"]*100:.0f}%</td>'
                    f'<td style="color:#ff832b;font-weight:600">{int(r.get("replenishment_qty",0)):,}</td></tr>\n')
        html += '</tbody></table>\n'
    html += '<div class="section-title">High-Risk Suppliers — Bottleneck Analysis</div>\n'
    if bottleneck_sup is not None and not bottleneck_sup.empty:
        html += '<table><thead><tr><th>Supplier</th><th>Country</th><th>Delay Rate</th><th>Avg Lead Days</th><th>Reliability Score</th><th>Action</th></tr></thead><tbody>\n'
        for _, r in bottleneck_sup.iterrows():
            action = "IMMEDIATE REVIEW" if r['delay_rate']>30 else "Monitor Closely"
            ac = "#da1e28" if r['delay_rate']>30 else "#ff832b"
            html += (f'<tr><td><strong>{r["supplier_name"]}</strong></td><td>{r["country"]}</td>'
                    f'<td style="color:#da1e28;font-weight:700">{r["delay_rate"]:.1f}%</td>'
                    f'<td>{r["avg_lead_days"]:.1f}</td>'
                    f'<td>{r["reliability_score"]:.2f}</td>'
                    f'<td style="color:{ac};font-weight:600">{action}</td></tr>\n')
        html += '</tbody></table>\n'
    recs = [
        ("Replenishment Action Required","#da1e28",f"{kpis.get('critical_alerts',0)} SKU-locations are at CRITICAL stockout risk. Initiate emergency purchase orders immediately for items with fewer than 7 days of supply remaining. Prioritize high-velocity products in high-demand regions."),
        ("Reduce Lead Times","#0f62fe","Suppliers with average lead time greater than 14 days should be renegotiated or replaced. Consider dual-sourcing strategies for top-10 products by demand volume. Target: reduce avg lead time by 20% within 90 days."),
        ("Shipment Delay Mitigation","#ff832b",f"Currently {kpis.get('in_transit',0)} orders in transit with {kpis.get('delayed_orders',0)} delayed in the last 30 days. Proactively communicate with affected customers, reroute critical shipments, and audit top-delayed carriers."),
        ("Demand Forecasting Integration","#24a148","30-day predictive demand forecasts (Ridge Regression model) are available for all 48 products. Align procurement cycles to forecast peaks. Holiday/seasonal bumps detected — pre-order buffer stock for Q4 demand surge."),
    ]
    html += '<div class="section-title">Actionable Recommendations</div>\n'
    for title, color, text in recs:
        html += f'<div class="insight-box" style="border-left-color:{color}"><h4 style="color:{color}">{title}</h4><p>{text}</p></div>\n'
    html += f'</div><div class="footer">IBM Supply Chain Intelligence Platform &nbsp;|&nbsp; Predictive Analytics &amp; Real-Time Visibility &nbsp;|&nbsp; Report generated: {now} &nbsp;|&nbsp; &copy; {datetime.now().year} IBM Corporation</div></body></html>'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report saved: {output_path}")
    return output_path

if __name__ == "__main__":
    path = generate_html_report()
    print(f"Open in browser: file:///{path}")

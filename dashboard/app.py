import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os, sys, warnings
warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database.db_manager import execute_query
from pipeline.analytics import (
    get_kpi_summary, get_shipment_status, get_demand_trends,
    get_lead_time_analysis, get_order_fulfillment_rate,
    get_supplier_performance, get_warehouse_utilization, get_actionable_insights
)
from alerts.alert_system import get_active_alerts, get_alert_summary, generate_alerts
from models.stockout_risk import calculate_stockout_risk, detect_supply_chain_bottlenecks

# â”€â”€ IBM Carbon Design System Palette â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
IBM_BLUE        = "#0f62fe"
IBM_BLUE_DARK   = "#0043ce"
IBM_BLUE_LIGHT  = "#4589ff"
IBM_CYAN        = "#1192e8"
IBM_TEAL        = "#009d9a"
IBM_GREEN       = "#24a148"
IBM_RED         = "#da1e28"
IBM_ORANGE      = "#ff832b"
IBM_YELLOW      = "#f1c21b"
IBM_PURPLE      = "#8a3ffc"
IBM_DARK        = "#161616"
IBM_GRAY_90     = "#262626"
IBM_GRAY_80     = "#393939"
IBM_GRAY_70     = "#525252"
IBM_GRAY_60     = "#6f6f6f"
IBM_GRAY_30     = "#c6c6c6"
IBM_GRAY_10     = "#f4f4f4"
IBM_WHITE       = "#ffffff"

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor=IBM_GRAY_90,
        plot_bgcolor=IBM_GRAY_90,
        font=dict(family="IBM Plex Sans, Arial, sans-serif", color=IBM_GRAY_10, size=12),
        title=dict(font=dict(color=IBM_WHITE, size=14, family="IBM Plex Sans, Arial, sans-serif")),
        xaxis=dict(gridcolor=IBM_GRAY_80, linecolor=IBM_GRAY_70, tickcolor=IBM_GRAY_30, tickfont=dict(color=IBM_GRAY_30)),
        yaxis=dict(gridcolor=IBM_GRAY_80, linecolor=IBM_GRAY_70, tickcolor=IBM_GRAY_30, tickfont=dict(color=IBM_GRAY_30)),
        legend=dict(bgcolor=IBM_GRAY_80, bordercolor=IBM_GRAY_70, font=dict(color=IBM_GRAY_10)),
        coloraxis=dict(colorbar=dict(tickfont=dict(color=IBM_GRAY_10), title=dict(font=dict(color=IBM_GRAY_10)))),
        margin=dict(t=48, b=24, l=16, r=16),
    )
)

STATUS_COLORS = {
    "Delivered":  IBM_GREEN,
    "In Transit": IBM_BLUE,
    "Delayed":    IBM_RED,
    "Processing": IBM_YELLOW,
    "Cancelled":  IBM_GRAY_60,
}

RISK_COLORS = {
    "CRITICAL": IBM_RED,
    "HIGH":     IBM_ORANGE,
    "MEDIUM":   IBM_YELLOW,
    "LOW":      IBM_GREEN,
}

# â”€â”€ Page Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.set_page_config(
    page_title="IBM Supply Chain Intelligence",
    page_icon="https://upload.wikimedia.org/wikipedia/commons/5/51/IBM_logo.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# â”€â”€ IBM Carbon CSS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', Arial, sans-serif !important;
    background-color: {IBM_DARK} !important;
    color: {IBM_GRAY_10} !important;
  }}
  .stApp {{ background-color: {IBM_DARK} !important; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{
    background-color: {IBM_GRAY_90} !important;
    border-right: 1px solid {IBM_GRAY_80};
  }}
  section[data-testid="stSidebar"] * {{ color: {IBM_GRAY_10} !important; }}
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stDateInput label {{ color: {IBM_GRAY_30} !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em; }}
  section[data-testid="stSidebar"] [data-baseweb="select"] div {{
    background-color: {IBM_GRAY_80} !important;
    border-color: {IBM_GRAY_70} !important;
    color: {IBM_WHITE} !important;
  }}

  /* IBM Header */
  .ibm-header {{
    background: linear-gradient(135deg, {IBM_BLUE_DARK} 0%, {IBM_BLUE} 60%, {IBM_CYAN} 100%);
    padding: 20px 28px 16px 28px;
    border-radius: 0;
    margin: -1rem -1rem 0 -1rem;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 3px solid {IBM_BLUE_LIGHT};
  }}
  .ibm-header-left {{ display: flex; align-items: center; gap: 18px; }}
  .ibm-logo-box {{
    background: {IBM_WHITE}; color: {IBM_BLUE_DARK};
    font-size: 1.35rem; font-weight: 700; padding: 6px 14px;
    letter-spacing: -0.02em; border-radius: 2px;
    font-family: 'IBM Plex Sans', sans-serif;
  }}
  .ibm-header-title {{
    color: {IBM_WHITE}; font-size: 1.25rem; font-weight: 600;
    letter-spacing: 0.01em; line-height: 1.2;
  }}
  .ibm-header-sub {{
    color: rgba(255,255,255,0.75); font-size: 0.75rem; font-weight: 400;
    margin-top: 2px; letter-spacing: 0.04em; text-transform: uppercase;
  }}
  .ibm-header-right {{ color: rgba(255,255,255,0.8); font-size: 0.75rem; text-align: right; }}
  .ibm-header-ts {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.65); }}

  /* Tabs */
  [data-testid="stTabs"] [role="tablist"] {{
    background-color: {IBM_GRAY_90} !important;
    border-bottom: 1px solid {IBM_GRAY_80} !important;
    gap: 0 !important; padding: 0 !important;
  }}
  [data-testid="stTabs"] [role="tab"] {{
    color: {IBM_GRAY_30} !important;
    background: transparent !important;
    border: none !important; border-bottom: 3px solid transparent !important;
    padding: 12px 20px !important; font-size: 0.82rem !important;
    font-weight: 500 !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important; border-radius: 0 !important;
    transition: all 0.2s !important;
  }}
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {IBM_WHITE} !important;
    border-bottom: 3px solid {IBM_BLUE} !important;
    background-color: {IBM_GRAY_80} !important;
  }}
  [data-testid="stTabs"] [role="tab"]:hover {{
    color: {IBM_WHITE} !important;
    background-color: {IBM_GRAY_80} !important;
  }}

  /* Metrics */
  [data-testid="stMetric"] {{
    background: {IBM_GRAY_90};
    border: 1px solid {IBM_GRAY_80};
    border-left: 3px solid {IBM_BLUE};
    border-radius: 0;
    padding: 14px 16px !important;
  }}
  [data-testid="stMetricLabel"] {{ color: {IBM_GRAY_30} !important; font-size: 0.72rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }}
  [data-testid="stMetricValue"] {{ color: {IBM_WHITE} !important; font-size: 1.7rem !important; font-weight: 600 !important; font-family: 'IBM Plex Mono', monospace !important; }}
  [data-testid="stMetricDelta"] {{ font-size: 0.75rem !important; }}

  /* Section headers */
  .ibm-section {{
    font-size: 0.7rem; font-weight: 600; color: {IBM_GRAY_30};
    text-transform: uppercase; letter-spacing: 0.12em;
    border-bottom: 1px solid {IBM_GRAY_80}; padding-bottom: 6px;
    margin: 20px 0 12px 0;
  }}

  /* Alert cards */
  .alert-card {{
    padding: 10px 14px; border-radius: 0;
    margin: 4px 0; font-size: 0.82rem;
    border-left: 4px solid;
    font-family: 'IBM Plex Sans', sans-serif;
  }}
  .alert-CRITICAL {{ background: rgba(218,30,40,0.12); border-color: {IBM_RED}; color: {IBM_GRAY_10}; }}
  .alert-HIGH     {{ background: rgba(255,131,43,0.12); border-color: {IBM_ORANGE}; color: {IBM_GRAY_10}; }}
  .alert-MEDIUM   {{ background: rgba(241,194,27,0.10); border-color: {IBM_YELLOW}; color: {IBM_GRAY_10}; }}
  .alert-LOW      {{ background: rgba(36,161,72,0.10);  border-color: {IBM_GREEN};  color: {IBM_GRAY_10}; }}

  /* Bottleneck cards */
  .bottleneck-card {{
    background: rgba(218,30,40,0.08);
    border: 1px solid rgba(218,30,40,0.3);
    border-left: 4px solid {IBM_RED};
    padding: 10px 14px; margin: 4px 0;
    font-size: 0.82rem;
  }}

  /* Insight cards */
  .insight-card {{
    background: {IBM_GRAY_90}; border: 1px solid {IBM_GRAY_80};
    border-left: 4px solid {IBM_BLUE}; padding: 14px;
    margin: 6px 0; border-radius: 0;
  }}

  /* DataFrames */
  [data-testid="stDataFrame"] {{ border: 1px solid {IBM_GRAY_80}; border-radius: 0; }}
  .dvn-scroller {{ background: {IBM_GRAY_90} !important; }}

  /* Buttons */
  .stButton > button {{
    background: {IBM_BLUE} !important; color: {IBM_WHITE} !important;
    border: 1px solid {IBM_BLUE_DARK} !important; border-radius: 0 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    text-transform: uppercase !important; letter-spacing: 0.04em !important;
    padding: 8px 20px !important;
  }}
  .stButton > button:hover {{ background: {IBM_BLUE_DARK} !important; }}

  /* Download buttons */
  .stDownloadButton > button {{
    background: transparent !important; color: {IBM_BLUE_LIGHT} !important;
    border: 1px solid {IBM_BLUE} !important; border-radius: 0 !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
  }}

  /* Divider */
  hr {{ border-color: {IBM_GRAY_80} !important; }}

  /* Expander */
  [data-testid="stExpander"] {{
    background: {IBM_GRAY_90} !important;
    border: 1px solid {IBM_GRAY_80} !important;
    border-radius: 0 !important;
  }}
  [data-testid="stExpander"] summary {{ color: {IBM_GRAY_10} !important; font-weight: 500 !important; }}

  /* Caption */
  .stCaption {{ color: {IBM_GRAY_60} !important; font-size: 0.72rem !important; font-family: 'IBM Plex Mono', monospace !important; }}

  /* Spinner */
  .stSpinner > div {{ border-top-color: {IBM_BLUE} !important; }}

  /* Success / warning / error */
  [data-testid="stAlert"] {{ border-radius: 0 !important; }}

  /* Footer tag */
  .ibm-footer {{
    margin-top: 40px; padding: 16px 0;
    border-top: 1px solid {IBM_GRAY_80};
    color: {IBM_GRAY_60}; font-size: 0.7rem;
    text-align: center; letter-spacing: 0.04em;
  }}
</style>
""", unsafe_allow_html=True)

# â”€â”€ IBM Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
st.markdown(f"""
<div class="ibm-header">
  <div class="ibm-header-left">
    <div class="ibm-logo-box">IBM</div>
    <div>
      <div class="ibm-header-title">Supply Chain Intelligence Platform</div>
      <div class="ibm-header-sub">Predictive Analytics &amp; Real-Time Visibility</div>
    </div>
  </div>
  <div class="ibm-header-right">
    <div style="color:rgba(255,255,255,0.9);font-weight:500;font-size:0.8rem;">ENTERPRISE EDITION</div>
    <div class="ibm-header-ts">{ts}</div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.68rem;margin-top:2px;">LIVE Â· AUTO-REFRESH ENABLED</div>
  </div>
</div>
""", unsafe_allow_html=True)

# â”€â”€ DB Guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@st.cache_resource
def ensure_db():
    try:
        r = execute_query("SELECT COUNT(*) as c FROM products")
        return int(r["c"].iloc[0]) > 0
    except Exception:
        return False

if not ensure_db():
    st.error("âš ï¸  Database not initialised. Run:  `python setup.py`  then refresh.")
    st.stop()

# â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with st.sidebar:
    st.markdown(f"""
    <div style="padding:12px 0 16px 0; border-bottom:1px solid {IBM_GRAY_80}; margin-bottom:16px;">
      <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Navigation &amp; Filters</div>
      <div style="font-size:0.85rem;color:{IBM_GRAY_10};font-weight:500;">Control Panel</div>
    </div>
    """, unsafe_allow_html=True)

    @st.cache_data(ttl=300)
    def load_opts():
        p = execute_query("SELECT product_id,product_name,category FROM products ORDER BY product_name")
        w = execute_query("SELECT warehouse_id,warehouse_name,region FROM warehouses ORDER BY region")
        s = execute_query("SELECT supplier_id,supplier_name FROM suppliers ORDER BY supplier_name")
        r = execute_query("SELECT DISTINCT region FROM warehouses ORDER BY region")["region"].tolist()
        c = execute_query("SELECT DISTINCT category FROM products ORDER BY category")["category"].tolist()
        return p, w, s, r, c

    prod_df, wh_df, sup_df, regions, cats = load_opts()

    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;'>Region</div>", unsafe_allow_html=True)
    sel_region = st.selectbox("Region", ["All"] + regions, label_visibility="collapsed")
    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;margin-top:8px;'>Product Category</div>", unsafe_allow_html=True)
    sel_cat = st.selectbox("Category", ["All"] + cats, label_visibility="collapsed")

    po = prod_df if sel_cat == "All" else prod_df[prod_df["category"] == sel_cat]
    pl = ["All"] + po.apply(lambda r: f"{r['product_id']} â€” {r['product_name']}", axis=1).tolist()
    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;margin-top:8px;'>Product</div>", unsafe_allow_html=True)
    sel_prod_lbl = st.selectbox("Product", pl, label_visibility="collapsed")
    sel_prod = None if sel_prod_lbl == "All" else sel_prod_lbl.split(" â€” ")[0]

    wo = wh_df if sel_region == "All" else wh_df[wh_df["region"] == sel_region]
    wl = ["All"] + wo.apply(lambda r: f"{r['warehouse_id']} â€” {r['warehouse_name']}", axis=1).tolist()
    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;margin-top:8px;'>Warehouse</div>", unsafe_allow_html=True)
    sel_wh_lbl = st.selectbox("Warehouse", wl, label_visibility="collapsed")
    sel_wh = None if sel_wh_lbl == "All" else sel_wh_lbl.split(" â€” ")[0]

    sl = ["All"] + sup_df.apply(lambda r: f"{r['supplier_id']} â€” {r['supplier_name']}", axis=1).tolist()
    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;margin-top:8px;'>Supplier</div>", unsafe_allow_html=True)
    sel_sup_lbl = st.selectbox("Supplier", sl, label_visibility="collapsed")
    sel_sup = None if sel_sup_lbl == "All" else sel_sup_lbl.split(" â€” ")[0]

    st.markdown(f"<hr style='border-color:{IBM_GRAY_80};margin:16px 0;'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;'>Date Range</div>", unsafe_allow_html=True)
    end_d = datetime.now().date()
    start_d = end_d - timedelta(days=180)
    date_start = st.date_input("From", value=start_d, label_visibility="collapsed")
    date_end   = st.date_input("To",   value=end_d,   label_visibility="collapsed")

    st.markdown(f"<hr style='border-color:{IBM_GRAY_80};margin:16px 0;'>", unsafe_allow_html=True)
    if st.button("â†º  REFRESH ALERTS"):
        with st.spinner("Regenerating alertsâ€¦"):
            generate_alerts()
        st.cache_data.clear()
        st.sidebar.success("Alerts updated.")
    if st.button("â†º  CLEAR CACHE"):
        st.cache_data.clear()
        st.sidebar.success("Cache cleared.")

    st.markdown(f"""
    <div style="margin-top:32px;padding:12px;background:{IBM_GRAY_80};border-left:3px solid {IBM_BLUE};font-size:0.72rem;color:{IBM_GRAY_30};">
      <div style="font-weight:600;color:{IBM_GRAY_10};margin-bottom:4px;">DATA SOURCES</div>
      DataCo Smart Supply Chain<br/>
      Olist Brazilian E-Commerce<br/>
      M5 Forecasting (Walmart)
    </div>
    """, unsafe_allow_html=True)

# â”€â”€ Tabs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
T = st.tabs([
    "OVERVIEW",
    "INVENTORY & RISK",
    "SHIPMENTS",
    "DEMAND FORECAST",
    "SUPPLIERS",
    "ALERTS",
    "INSIGHTS & REPORT",
])

# helper to apply IBM template
def apply_ibm(fig, height=360):
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    fig.update_layout(height=height)
    return fig

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 0 â€” OVERVIEW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[0]:
    @st.cache_data(ttl=60)
    def kpis():
        return get_kpi_summary()
    k = kpis()

    # KPI row 1
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("INVENTORY VALUE",   f"${k.get('inventory_value',0):,.0f}")
    c2.metric("TOTAL UNITS",       f"{k.get('total_units',0):,}")
    c3.metric("ON-TIME RATE",      f"{k.get('on_time_rate',0):.1f}%",
              delta=f"{k.get('on_time_rate',0)-90:.1f}% vs 90% SLA")
    c4.metric("ACTIVE ALERTS",     k.get("active_alerts",0),
              delta=f"{k.get('critical_alerts',0)} critical", delta_color="inverse")
    c5.metric("IN TRANSIT",        k.get("in_transit",0))
    c6.metric("AVG DELAY (DAYS)",  f"{k.get('avg_delay_days',0):.1f}")

    st.markdown(f"<div class='ibm-section'>ORDER FLOW ANALYSIS</div>", unsafe_allow_html=True)
    col_l, col_r = st.columns([3, 2])

    with col_l:
        @st.cache_data(ttl=120)
        def weekly_orders(sd, ed):
            return get_order_fulfillment_rate(group_by="date", start_date=str(sd), end_date=str(ed))
        od = weekly_orders(date_start, date_end)
        if not od.empty:
            fig = px.area(od, x="week", y="count", color="status",
                         color_discrete_map=STATUS_COLORS,
                         title="Weekly Order Volume by Status")
            fig.update_traces(line_width=1.5)
            st.plotly_chart(apply_ibm(fig, 330), width='stretch')

    with col_r:
        @st.cache_data(ttl=120)
        def region_orders(sd, ed):
            return get_order_fulfillment_rate(group_by="region", start_date=str(sd), end_date=str(ed))
        rd = region_orders(date_start, date_end)
        if not rd.empty:
            rt = rd.groupby("region")["count"].sum().reset_index()
            fig2 = px.pie(rt, names="region", values="count", title="Orders by Region",
                         hole=0.55,
                         color_discrete_sequence=[IBM_BLUE, IBM_CYAN, IBM_TEAL, IBM_PURPLE, IBM_BLUE_LIGHT])
            fig2.update_traces(textfont_color=IBM_WHITE)
            st.plotly_chart(apply_ibm(fig2, 330), width='stretch')

    st.markdown(f"<div class='ibm-section'>WAREHOUSE UTILIZATION</div>", unsafe_allow_html=True)
    @st.cache_data(ttl=120)
    def wh_util():
        return get_warehouse_utilization()
    wu = wh_util()
    if not wu.empty:
        fig3 = go.Figure()
        colors = [IBM_RED if x > 90 else IBM_ORANGE if x > 70 else IBM_GREEN for x in wu["utilization_pct"]]
        fig3.add_bar(x=wu["warehouse_name"], y=wu["utilization_pct"],
                    marker_color=colors, name="Utilization %",
                    text=wu["utilization_pct"].round(1),
                    textposition="outside", textfont_color=IBM_GRAY_10)
        fig3.add_hline(y=80, line_dash="dash", line_color=IBM_ORANGE, line_width=1.5,
                      annotation_text="80% threshold", annotation_font_color=IBM_ORANGE)
        fig3.update_layout(title="Distribution Center Capacity Utilization (%)",
                          xaxis_tickangle=20, showlegend=False)
        st.plotly_chart(apply_ibm(fig3, 300), width='stretch')

    # Summary stats bar
    del_cnt = k.get("delivered_orders", 0)
    tot_cnt = k.get("total_orders_30d", 1)
    del_pct = del_cnt / max(tot_cnt, 1) * 100
    st.markdown(f"""
    <div style="display:flex;gap:1px;margin:16px 0 4px 0;">
      <div style="flex:{del_pct};background:{IBM_GREEN};height:6px;border-radius:0;"></div>
      <div style="flex:{k.get('in_transit',0)/max(tot_cnt,1)*100};background:{IBM_BLUE};height:6px;"></div>
      <div style="flex:{k.get('delayed_orders',0)/max(tot_cnt,1)*100};background:{IBM_RED};height:6px;"></div>
      <div style="flex:2;background:{IBM_GRAY_80};height:6px;"></div>
    </div>
    <div style="display:flex;gap:20px;font-size:0.7rem;color:{IBM_GRAY_60};">
      <span style="color:{IBM_GREEN};">â–  Delivered {del_cnt:,}</span>
      <span style="color:{IBM_BLUE};">â–  In Transit {k.get('in_transit',0):,}</span>
      <span style="color:{IBM_RED};">â–  Delayed {k.get('delayed_orders',0):,}</span>
    </div>
    """, unsafe_allow_html=True)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 1 â€” INVENTORY & RISK
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[1]:
    @st.cache_data(ttl=180)
    def risk_data():
        return calculate_stockout_risk(lead_time_days=14)
    rdf = risk_data()

    if not rdf.empty:
        f = rdf.copy()
        if sel_prod:    f = f[f["product_id"]   == sel_prod]
        if sel_wh:      f = f[f["warehouse_id"] == sel_wh]
        if sel_region != "All": f = f[f["region"] == sel_region]
        if sel_cat    != "All": f = f[f["category"] == sel_cat]

        st.markdown(f"<div class='ibm-section'>STOCKOUT RISK SUMMARY</div>", unsafe_allow_html=True)
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("CRITICAL",    len(f[f["risk_category"]=="CRITICAL"]))
        c2.metric("HIGH",        len(f[f["risk_category"]=="HIGH"]))
        c3.metric("MEDIUM",      len(f[f["risk_category"]=="MEDIUM"]))
        c4.metric("NEED REORDER",int(f["needs_replenishment"].sum()))
        c5.metric("SKU-LOCATIONS", len(f))

        col_a, col_b = st.columns([3, 2])
        with col_a:
            st.markdown(f"<div class='ibm-section'>STOCKOUT PROBABILITY MATRIX</div>", unsafe_allow_html=True)
            fig_r = px.scatter(
                f.head(300), x="days_of_stock", y="stockout_probability",
                color="risk_category", size="stock_level",
                hover_data=["product_name", "warehouse_name", "avg_daily_demand", "category"],
                color_discrete_map=RISK_COLORS,
                labels={"days_of_stock":"Days of Stock","stockout_probability":"Stockout Probability",
                        "risk_category":"Risk Level"})
            fig_r.add_vline(x=7,  line_dash="dash", line_color=IBM_RED,    line_width=1.2,
                           annotation_text="7-day critical",  annotation_font_color=IBM_RED)
            fig_r.add_vline(x=14, line_dash="dash", line_color=IBM_ORANGE, line_width=1.2,
                           annotation_text="14-day warning", annotation_font_color=IBM_ORANGE)
            fig_r.add_hline(y=0.7, line_dash="dot", line_color=IBM_RED,   line_width=1,
                           annotation_text="70% critical threshold", annotation_font_color=IBM_RED)
            st.plotly_chart(apply_ibm(fig_r, 400), width='stretch')

        with col_b:
            st.markdown(f"<div class='ibm-section'>RISK DISTRIBUTION</div>", unsafe_allow_html=True)
            rc = f["risk_category"].value_counts()
            rl = [x for x in ["CRITICAL","HIGH","MEDIUM","LOW"] if x in rc.index]
            rv = [rc[x] for x in rl]
            rcolors = [RISK_COLORS[x] for x in rl]
            fig_d = go.Figure(go.Pie(labels=rl, values=rv, hole=0.6,
                                     marker_colors=rcolors,
                                     textfont_color=IBM_WHITE))
            fig_d.update_layout(
                annotations=[dict(text=f"{len(f)}<br>SKUs", x=0.5, y=0.5,
                                  font_size=14, font_color=IBM_WHITE, showarrow=False)],
                legend=dict(orientation="h", yanchor="bottom", y=-0.15))
            st.plotly_chart(apply_ibm(fig_d, 360), width='stretch')

            # Mini risk legend
            for level, color in RISK_COLORS.items():
                cnt = len(f[f["risk_category"]==level])
                pct = cnt/max(len(f),1)*100
                st.markdown(f"""<div style="display:flex;justify-content:space-between;
                  align-items:center;padding:4px 0;border-bottom:1px solid {IBM_GRAY_80};font-size:0.78rem;">
                  <span style="color:{color};font-weight:600;">{level}</span>
                  <span style="color:{IBM_GRAY_10};font-family:'IBM Plex Mono',monospace;">
                    {cnt:,} &nbsp;({pct:.0f}%)</span>
                </div>""", unsafe_allow_html=True)

        st.markdown(f"<div class='ibm-section'>STOCK LEVEL BY CATEGORY</div>", unsafe_allow_html=True)
        cat_s = f.groupby("category").agg(
            total_stock=("stock_level","sum"),
            avg_risk=("stockout_probability","mean"),
            critical=("risk_category", lambda x: (x=="CRITICAL").sum())
        ).reset_index()
        fig_c = px.bar(cat_s, x="category", y="total_stock", color="avg_risk",
                      color_continuous_scale=[[0,IBM_GREEN],[0.4,IBM_YELLOW],[0.7,IBM_ORANGE],[1,IBM_RED]],
                      text="critical",
                      labels={"total_stock":"Total Units","avg_risk":"Avg Risk","critical":"Critical SKUs"},
                      title="Inventory by Category â€” Color Intensity = Avg Stockout Risk")
        fig_c.update_traces(texttemplate="%{text} crit.", textposition="outside",
                           textfont_color=IBM_GRAY_10)
        st.plotly_chart(apply_ibm(fig_c, 300), width='stretch')

        st.markdown(f"<div class='ibm-section'>CRITICAL & HIGH RISK ITEMS</div>", unsafe_allow_html=True)
        crit = f[f["risk_category"].isin(["CRITICAL","HIGH"])].sort_values("stockout_probability", ascending=False).head(30)
        if not crit.empty:
            disp = ["product_name","category","warehouse_name","region","stock_level",
                   "days_of_stock","stockout_probability","risk_category","replenishment_qty"]
            st.dataframe(
                crit[disp].style
                    .format({"stockout_probability":"{:.1%}","days_of_stock":"{:.1f}",
                             "stock_level":"{:,}","replenishment_qty":"{:,}"})
                    .map(lambda v: f"color:{IBM_RED};font-weight:700" if v=="CRITICAL"
                         else f"color:{IBM_ORANGE};font-weight:600" if v=="HIGH" else "",
                         subset=["risk_category"]),
                width='stretch', height=380
            )

        # GAP FIX: Inventory Trend Chart
        st.markdown(f"<div class='ibm-section'>INVENTORY TREND — STOCK LEVEL OVER TIME (BY CATEGORY)</div>", unsafe_allow_html=True)
        inv_trend_q = """
            SELECT p.category, DATE(i.last_updated) as update_date,
                   SUM(i.stock_level) as total_stock
            FROM inventory i JOIN products p ON i.product_id=p.product_id
            GROUP BY p.category, DATE(i.last_updated)
            ORDER BY update_date
        """
        inv_trend = execute_query(inv_trend_q)
        if not inv_trend.empty:
            fig_inv = px.bar(inv_trend, x="category", y="total_stock", color="category",
                            color_discrete_sequence=[IBM_BLUE, IBM_CYAN, IBM_TEAL, IBM_GREEN, IBM_PURPLE, IBM_ORANGE, IBM_YELLOW, IBM_BLUE_LIGHT],
                            title="Current Stock Levels by Product Category",
                            labels={"total_stock":"Total Units","category":"Category"})
            fig_inv.update_layout(showlegend=False)
            fig_inv.update_traces(text=inv_trend["total_stock"].apply(lambda x: f"{x:,.0f}"),
                                 textposition="outside", textfont_color=IBM_GRAY_10)
            st.plotly_chart(apply_ibm(fig_inv, 300), width='stretch')

        # GAP FIX: Delay Impact Estimation
        st.markdown(f"<div class='ibm-section'>DELAY IMPACT ESTIMATION — OPERATIONAL RISK</div>", unsafe_allow_html=True)
        from models.stockout_risk import estimate_delay_impact
        try:
            di_df = estimate_delay_impact()
            if di_df is not None and not di_df.empty:
                col_di1, col_di2 = st.columns([2, 1])
                with col_di1:
                    top_di = di_df.head(15)
                    fig_di = px.bar(top_di, x="product_name", y="delay_days",
                                   color="delay_days",
                                   color_continuous_scale=[[0,IBM_GREEN],[0.5,IBM_YELLOW],[1,IBM_RED]],
                                   title="Estimated Delay Days per Product (Top Delayed)",
                                   labels={"delay_days":"Delay (days)","product_name":"Product"})
                    fig_di.update_layout(showlegend=False, xaxis_tickangle=30)
                    st.plotly_chart(apply_ibm(fig_di, 320), width='stretch')
                with col_di2:
                    st.markdown(f"<div class='ibm-section'>IMPACT SUMMARY</div>", unsafe_allow_html=True)
                    total_delayed_orders = len(di_df)
                    avg_delay = di_df["delay_days"].mean() if "delay_days" in di_df.columns else 0
                    worst = di_df.iloc[0] if not di_df.empty else None
                    st.markdown(f"""
                    <div style="padding:10px 0;border-bottom:1px solid {IBM_GRAY_80};">
                      <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;">Delayed Shipments</div>
                      <div style="font-size:1.5rem;font-weight:700;color:{IBM_RED};font-family:'IBM Plex Mono',monospace;">{total_delayed_orders:,}</div>
                    </div>
                    <div style="padding:10px 0;border-bottom:1px solid {IBM_GRAY_80};">
                      <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;">Avg Delay</div>
                      <div style="font-size:1.5rem;font-weight:700;color:{IBM_ORANGE};font-family:'IBM Plex Mono',monospace;">{avg_delay:.1f}d</div>
                    </div>
                    <div style="padding:10px 0;">
                      <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;">Worst Product</div>
                      <div style="font-size:0.85rem;font-weight:600;color:{IBM_RED};margin-top:4px;">{worst['product_name'] if worst is not None else 'N/A'}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.info(f"Delay impact data not available: {e}")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 2 â€” SHIPMENTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[2]:
    @st.cache_data(ttl=120)
    def ships(pid, wid, reg, sid, sd, ed):
        return get_shipment_status(product_id=pid, warehouse_id=wid,
                                  region=reg if reg!="All" else None,
                                  supplier_id=sid, start_date=str(sd), end_date=str(ed))
    sd_df = ships(sel_prod, sel_wh, sel_region, sel_sup, date_start, date_end)

    if not sd_df.empty:
        st.markdown(f"<div class='ibm-section'>SHIPMENT PERFORMANCE</div>", unsafe_allow_html=True)
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("TOTAL SHIPMENTS",  len(sd_df))
        c2.metric("DELIVERED",        len(sd_df[sd_df["status"]=="Delivered"]))
        c3.metric("IN TRANSIT",       len(sd_df[sd_df["status"]=="In Transit"]))
        c4.metric("DELAYED",          len(sd_df[sd_df["status"]=="Delayed"]))
        dl = sd_df[sd_df["delay_days"]>0]["delay_days"]
        c5.metric("AVG DELAY",        f"{dl.mean():.1f}d" if len(dl)>0 else "0d")

        col_l, col_r = st.columns([3,2])
        with col_l:
            st.markdown(f"<div class='ibm-section'>STATUS BY CARRIER</div>", unsafe_allow_html=True)
            cs = sd_df.groupby(["carrier","status"]).size().reset_index(name="count")
            fig_c = px.bar(cs, x="carrier", y="count", color="status", barmode="stack",
                          color_discrete_map=STATUS_COLORS,
                          title="Shipment Status by Carrier")
            fig_c.update_layout(legend_title_text="Status")
            st.plotly_chart(apply_ibm(fig_c, 360), width='stretch')

        with col_r:
            st.markdown(f"<div class='ibm-section'>DELAY DISTRIBUTION</div>", unsafe_allow_html=True)
            if len(dl) > 0:
                fig_h = go.Figure()
                fig_h.add_trace(go.Histogram(x=dl, nbinsx=15,
                                            marker_color=IBM_RED,
                                            marker_line_color=IBM_GRAY_80,
                                            marker_line_width=0.5,
                                            opacity=0.85, name="Delay Days"))
                fig_h.update_layout(title="Delay Distribution (days)",
                                   xaxis_title="Delay (days)", yaxis_title="Frequency")
                st.plotly_chart(apply_ibm(fig_h, 360), width='stretch')

        st.markdown(f"<div class='ibm-section'>DELAY HEATMAP â€” REGION Ã— CARRIER</div>", unsafe_allow_html=True)
        hm = sd_df.groupby(["destination_region","carrier"])["delay_days"].mean().reset_index()
        hp = hm.pivot(index="destination_region", columns="carrier", values="delay_days").fillna(0)
        fig_hm = px.imshow(hp,
                          color_continuous_scale=[[0,IBM_GREEN],[0.3,IBM_YELLOW],[0.6,IBM_ORANGE],[1,IBM_RED]],
                          title="Average Delay Days: Region Ã— Carrier",
                          labels=dict(color="Avg Delay (days)"))
        fig_hm.update_traces(texttemplate="%{z:.1f}", textfont_color=IBM_WHITE)
        st.plotly_chart(apply_ibm(fig_hm, 280), width='stretch')

        st.markdown(f"<div class='ibm-section'>LEAD TIME ANALYSIS</div>", unsafe_allow_html=True)
        @st.cache_data(ttl=120)
        def lt(sid, reg, sd, ed):
            return get_lead_time_analysis(supplier_id=sid, region=reg if reg!="All" else None,
                                         start_date=str(sd), end_date=str(ed))
        ldf = lt(sel_sup, sel_region, date_start, date_end)
        if not ldf.empty:
            tops = ldf["supplier_name"].value_counts().head(8).index.tolist()
            fig_lt = px.box(ldf[ldf["supplier_name"].isin(tops)],
                           x="supplier_name", y="actual_lead_days",
                           color="supplier_name",
                           title="Lead Time Distribution by Supplier",
                           labels={"actual_lead_days":"Lead Days"})
            fig_lt.update_layout(showlegend=False, xaxis_tickangle=25)
            st.plotly_chart(apply_ibm(fig_lt, 350), width='stretch')

        st.markdown(f"<div class='ibm-section'>DELAYED ORDERS â€” TOP 20</div>", unsafe_allow_html=True)
        dtbl = sd_df[sd_df["status"]=="Delayed"].sort_values("delay_days", ascending=False).head(20)
        if not dtbl.empty:
            show = ["shipment_id","product_name","supplier_name","destination_region",
                   "carrier","delay_days","estimated_arrival","order_date"]
            st.dataframe(
                dtbl[show].style.map(
                    lambda v: f"color:{IBM_RED};font-weight:700" if isinstance(v, (int,float)) and v>=10 else "",
                    subset=["delay_days"]),
                width='stretch', height=320
            )
    else:
        st.info("No shipment data for the current filter selection.")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 3 â€” DEMAND FORECAST
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[3]:
    @st.cache_data(ttl=300)
    def dem(pid, wid, reg, sd, ed):
        return get_demand_trends(product_id=pid, warehouse_id=wid,
                                region=reg if reg!="All" else None,
                                start_date=str(sd), end_date=str(ed))
    ddf = dem(sel_prod, sel_wh, sel_region, date_start, date_end)

    if not ddf.empty:
        ddf["date"] = pd.to_datetime(ddf["date"])
        wk = ddf.groupby(pd.Grouper(key="date", freq="W"))["demand"].sum().reset_index()
        wk.columns = ["week","total_demand"]

        st.markdown(f"<div class='ibm-section'>DEMAND TREND ANALYSIS</div>", unsafe_allow_html=True)
        col_l, col_r = st.columns([3, 1])
        with col_l:
            fig_t = go.Figure()
            fig_t.add_scatter(x=wk["week"], y=wk["total_demand"],
                             name="Weekly Demand", mode="lines+markers",
                             line=dict(color=IBM_BLUE, width=2),
                             marker=dict(color=IBM_BLUE_LIGHT, size=4))
            if len(wk) > 2:
                from scipy.stats import linregress
                xa = np.arange(len(wk))
                sl2, ic, _, _, _ = linregress(xa, wk["total_demand"])
                tv = sl2 * xa + ic
                fig_t.add_scatter(x=wk["week"], y=tv, name="Trend",
                                 line=dict(color=IBM_ORANGE, dash="dash", width=1.5))
            fig_t.update_layout(title="Weekly Total Demand with Trend",
                               legend_title_text="Series")
            st.plotly_chart(apply_ibm(fig_t, 360), width='stretch')

        with col_r:
            st.markdown(f"<div class='ibm-section'>STATISTICS</div>", unsafe_allow_html=True)
            stats = ddf["demand"].describe()
            metrics = [
                ("AVG DAILY",  f"{stats['mean']:.1f}"),
                ("PEAK DAILY", f"{stats['max']:.0f}"),
                ("STD DEV",    f"{stats['std']:.1f}"),
                ("TOTAL DAYS", str((ddf['date'].max()-ddf['date'].min()).days)),
            ]
            for lbl, val in metrics:
                st.markdown(f"""<div style="padding:10px 0;border-bottom:1px solid {IBM_GRAY_80};">
                  <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;">{lbl}</div>
                  <div style="font-size:1.3rem;font-weight:600;color:{IBM_WHITE};font-family:'IBM Plex Mono',monospace;">{val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown(f"<div class='ibm-section'>CATEGORY DEMAND HEATMAP (LAST 12 WEEKS)</div>", unsafe_allow_html=True)
        cat_d = ddf.groupby(["date","category"])["demand"].sum().reset_index()
        cat_d["week"] = cat_d["date"].dt.to_period("W").astype(str)
        hm2 = cat_d.groupby(["category","week"])["demand"].sum().reset_index()
        last12 = sorted(hm2["week"].unique())[-12:]
        hm2f = hm2[hm2["week"].isin(last12)]
        if not hm2f.empty:
            hp3 = hm2f.pivot(index="category", columns="week", values="demand").fillna(0)
            fig_hm3 = px.imshow(hp3,
                               color_continuous_scale=[[0,"#161616"],[0.5,IBM_BLUE],[1,IBM_CYAN]],
                               title="Demand Intensity by Category",
                               labels=dict(color="Units"))
            fig_hm3.update_traces(texttemplate="%{z:.0f}", textfont_size=9, textfont_color=IBM_GRAY_10)
            st.plotly_chart(apply_ibm(fig_hm3, 320), width='stretch')

        st.markdown(f"<div class='ibm-section'>30-DAY PREDICTIVE DEMAND FORECAST</div>", unsafe_allow_html=True)
        if sel_prod and sel_wh:
            from models.demand_forecast import forecast_product_warehouse
            with st.spinner("Running Ridge Regression forecasting modelâ€¦"):
                fc = forecast_product_warehouse(sel_prod, sel_wh, horizon=30)
            if fc is not None and not fc.empty:
                hist = ddf.sort_values("date").tail(60).groupby("date")["demand"].sum().reset_index()
                fc["forecast_date"] = pd.to_datetime(fc["forecast_date"])
                fig_fc = go.Figure()
                fig_fc.add_scatter(x=hist["date"], y=hist["demand"],
                                  name="Historical", line=dict(color=IBM_BLUE, width=2))
                # CI shading
                x_ci = pd.concat([fc["forecast_date"], fc["forecast_date"][::-1]])
                y_ci = pd.concat([fc["upper_bound"],   fc["lower_bound"][::-1]])
                fig_fc.add_scatter(x=x_ci, y=y_ci, fill="toself",
                                  fillcolor="rgba(15,98,254,0.12)",
                                  line=dict(color="rgba(0,0,0,0)"), name="95% CI")
                fig_fc.add_scatter(x=fc["forecast_date"], y=fc["predicted_demand"],
                                  name="Forecast", mode="lines+markers",
                                  line=dict(color=IBM_ORANGE, dash="dash", width=2),
                                  marker=dict(size=5, color=IBM_ORANGE))
                fig_fc.add_vline(x=str(ddf["date"].max()),
                                line_dash="dot", line_color=IBM_GRAY_60,
                                annotation_text="Today", annotation_font_color=IBM_GRAY_60)
                prod_nm = sel_prod_lbl.split(" â€” ")[1] if " â€” " in sel_prod_lbl else sel_prod
                wh_nm  = sel_wh_lbl.split(" â€” ")[1]  if " â€” " in sel_wh_lbl  else sel_wh
                fig_fc.update_layout(title=f"30-Day Demand Forecast â€” {prod_nm} @ {wh_nm}",
                                    legend_title_text="Series")
                st.plotly_chart(apply_ibm(fig_fc, 380), width='stretch')
            else:
                st.info("Insufficient data for this combination. Select a product with more history.")
        else:
            fc_n = execute_query("SELECT COUNT(*) as c FROM forecasts")["c"].iloc[0]
            if fc_n > 0:
                fc_agg = execute_query("""
                    SELECT forecast_date,
                           SUM(predicted_demand) as total_demand,
                           SUM(lower_bound) as lb, SUM(upper_bound) as ub
                    FROM forecasts GROUP BY forecast_date ORDER BY forecast_date
                """)
                if not fc_agg.empty:
                    fig_agg = go.Figure()
                    x_ci2 = pd.concat([fc_agg["forecast_date"], fc_agg["forecast_date"][::-1]])
                    y_ci2 = pd.concat([fc_agg["ub"], fc_agg["lb"][::-1]])
                    fig_agg.add_scatter(x=x_ci2, y=y_ci2, fill="toself",
                                       fillcolor="rgba(15,98,254,0.12)",
                                       line=dict(color="rgba(0,0,0,0)"), name="95% CI")
                    fig_agg.add_scatter(x=fc_agg["forecast_date"], y=fc_agg["total_demand"],
                                       name="Aggregate Forecast",
                                       line=dict(color=IBM_ORANGE, width=2))
                    fig_agg.update_layout(title="30-Day Aggregate Demand Forecast (All Pre-computed Products)")
                    st.plotly_chart(apply_ibm(fig_agg, 380), width='stretch')
            else:
                st.markdown(f"""<div class="insight-card">
                  <b style="color:{IBM_BLUE_LIGHT};">SELECT A PRODUCT + WAREHOUSE</b><br/>
                  <span style="color:{IBM_GRAY_30};font-size:0.82rem;">
                  Use the sidebar filters to select a specific product and warehouse to generate
                  a live 30-day demand forecast with confidence intervals. Or run
                  <code>python setup.py</code> to pre-compute forecasts for all products.
                  </span>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("No demand data for selected filters.")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 4 â€” SUPPLIERS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[4]:
    @st.cache_data(ttl=180)
    def sup_data():
        return get_supplier_performance(), detect_supply_chain_bottlenecks()
    sp, (bn_df, reg_df) = sup_data()

    if not sp.empty:
        sf = sp if not sel_sup else sp[sp["supplier_id"] == sel_sup]

        st.markdown(f"<div class='ibm-section'>SUPPLIER PERFORMANCE MATRIX</div>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 2])
        with col1:
            fig_s = px.scatter(sf, x="on_time_rate", y="avg_lead_days",
                              color="delay_rate", size="total_orders",
                              hover_data=["supplier_name","country","reliability_score"],
                              color_continuous_scale=[[0,IBM_GREEN],[0.5,IBM_YELLOW],[1,IBM_RED]],
                              labels={"on_time_rate":"On-Time Rate (%)","avg_lead_days":"Avg Lead Time (days)",
                                      "delay_rate":"Delay Rate (%)"},
                              title="Supplier Quadrant â€” Performance vs Lead Time")
            fig_s.add_vline(x=85, line_dash="dash", line_color=IBM_GREEN, line_width=1.2,
                           annotation_text="85% OTR target", annotation_font_color=IBM_GREEN)
            fig_s.add_hline(y=14, line_dash="dash", line_color=IBM_ORANGE, line_width=1.2,
                           annotation_text="14-day LT target", annotation_font_color=IBM_ORANGE)
            # Quadrant labels
            fig_s.add_annotation(x=95, y=5,  text="â­ PREFERRED", showarrow=False,
                                 font=dict(color=IBM_GREEN,  size=9))
            fig_s.add_annotation(x=70, y=22, text="âš  AT RISK",   showarrow=False,
                                 font=dict(color=IBM_RED,    size=9))
            st.plotly_chart(apply_ibm(fig_s, 400), width='stretch')

        with col2:
            st.markdown(f"<div class='ibm-section'>BOTTLENECK SUPPLIERS</div>", unsafe_allow_html=True)
            bns = bn_df[bn_df["is_bottleneck"]].sort_values("bottleneck_score", ascending=False)
            if not bns.empty:
                for _, row in bns.head(8).iterrows():
                    score = row["bottleneck_score"]
                    bar_w = min(int(score * 100), 100)
                    bar_color = IBM_RED if score > 0.5 else IBM_ORANGE
                    st.markdown(f"""
                    <div class="bottleneck-card">
                      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <span style="font-weight:600;color:{IBM_GRAY_10};font-size:0.82rem;">{row['supplier_name']}</span>
                        <span style="color:{bar_color};font-family:'IBM Plex Mono',monospace;font-size:0.78rem;">{score:.2f}</span>
                      </div>
                      <div style="font-size:0.72rem;color:{IBM_GRAY_60};margin-bottom:6px;">
                        {row['country']} Â· {row['delay_rate']*100:.0f}% delay rate
                      </div>
                      <div style="background:{IBM_GRAY_80};height:3px;border-radius:2px;">
                        <div style="background:{bar_color};width:{bar_w}%;height:3px;border-radius:2px;"></div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:{IBM_GREEN};padding:16px;'>No bottleneck suppliers detected.</div>", unsafe_allow_html=True)

        if not reg_df.empty:
            st.markdown(f"<div class='ibm-section'>DELAY RATE BY DESTINATION REGION</div>", unsafe_allow_html=True)
            fig_r = px.bar(reg_df, x="customer_region", y="delay_rate",
                          color="avg_delay",
                          color_continuous_scale=[[0,IBM_GREEN],[0.5,IBM_YELLOW],[1,IBM_RED]],
                          labels={"customer_region":"Region","delay_rate":"Delay Rate","avg_delay":"Avg Delay (days)"},
                          title="Shipment Delay Rate by Destination Region")
            fig_r.update_traces(text=reg_df["delay_rate"].mul(100).round(1).astype(str)+"%",
                               textposition="outside", textfont_color=IBM_GRAY_10)
            st.plotly_chart(apply_ibm(fig_r, 300), width='stretch')

        st.markdown(f"<div class='ibm-section'>SUPPLIER SCORECARD</div>", unsafe_allow_html=True)
        dcols = ["supplier_name","country","reliability_score","avg_lead_days",
                "total_orders","on_time_rate","delay_rate","avg_delay_days"]
        def color_delay(v):
            try:
                val = float(str(v).replace("%",""))
                if val >= 30:   return f"color:#da1e28;font-weight:700"
                elif val >= 15: return f"color:#ff832b;font-weight:600"
                elif val >= 5:  return f"color:#f1c21b"
                else:           return f"color:#24a148"
            except Exception:
                return ""
        st.dataframe(
            sf[dcols].sort_values("delay_rate", ascending=False).style.format({
                "reliability_score": "{:.2f}",
                "on_time_rate":  "{:.1f}%",
                "delay_rate":    "{:.1f}%",
                "avg_delay_days":"{:.1f}",
                "total_orders":  "{:,}"
            }).map(color_delay, subset=["delay_rate"]),
            width='stretch', height=380
        )

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 5 â€” ALERTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[5]:
    @st.cache_data(ttl=30)
    def al():
        return get_active_alerts(limit=300), get_alert_summary()
    all_al, al_sum = al()

    st.markdown(f"<div class='ibm-section'>ALERT SUMMARY</div>", unsafe_allow_html=True)
    if not all_al.empty:
        sc = all_al["severity"].value_counts()
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("TOTAL ACTIVE",  len(all_al))
        c2.metric("CRITICAL",      sc.get("CRITICAL",0))
        c3.metric("HIGH",          sc.get("HIGH",0))
        c4.metric("MEDIUM",        sc.get("MEDIUM",0))
        c5.metric("LOW",           sc.get("LOW",0))

        # Alert timeline bar
        tc = all_al["alert_type"].value_counts().reset_index()
        tc.columns = ["type","count"]

        col_pie, col_bar = st.columns([1, 2])
        with col_pie:
            st.markdown(f"<div class='ibm-section'>BY TYPE</div>", unsafe_allow_html=True)
            type_colors = {
                "STOCKOUT_CRITICAL": IBM_RED,
                "STOCKOUT_HIGH":     IBM_ORANGE,
                "LOW_STOCK":         IBM_YELLOW,
                "SHIPMENT_DELAY":    IBM_BLUE,
                "SUPPLIER_DISRUPTION": IBM_PURPLE,
                "DEMAND_SPIKE":      IBM_CYAN,
            }
            fig_tp = go.Figure(go.Pie(
                labels=tc["type"].tolist(), values=tc["count"].tolist(),
                hole=0.55,
                marker_colors=[type_colors.get(t, IBM_GRAY_60) for t in tc["type"]],
                textfont_color=IBM_WHITE
            ))
            fig_tp.update_layout(legend_title_text="Type",
                                annotations=[dict(text=f"{len(all_al)}<br>alerts",
                                                 x=0.5, y=0.5, showarrow=False,
                                                 font_size=13, font_color=IBM_WHITE)])
            st.plotly_chart(apply_ibm(fig_tp, 340), width='stretch')

        with col_bar:
            st.markdown(f"<div class='ibm-section'>BY SEVERITY</div>", unsafe_allow_html=True)
            sev_order = ["CRITICAL","HIGH","MEDIUM","LOW"]
            sev_counts = [sc.get(s, 0) for s in sev_order]
            sev_colors = [IBM_RED, IBM_ORANGE, IBM_YELLOW, IBM_GREEN]
            fig_sv = go.Figure()
            for sv, cnt, col in zip(sev_order, sev_counts, sev_colors):
                fig_sv.add_bar(x=[sv], y=[cnt], name=sv, marker_color=col,
                              text=[cnt], textposition="outside",
                              textfont_color=IBM_GRAY_10)
            fig_sv.update_layout(title="Alert Count by Severity", showlegend=False)
            st.plotly_chart(apply_ibm(fig_sv, 340), width='stretch')

    st.markdown(f"<div class='ibm-section'>ALERT FEED</div>", unsafe_allow_html=True)
    cf1, cf2 = st.columns([2,2])
    with cf1:
        sev_f = st.selectbox("Filter Severity", ["All","CRITICAL","HIGH","MEDIUM","LOW"])
    with cf2:
        type_f = st.selectbox("Filter Type",
                             ["All","STOCKOUT_CRITICAL","STOCKOUT_HIGH","LOW_STOCK",
                              "SHIPMENT_DELAY","SUPPLIER_DISRUPTION","DEMAND_SPIKE"])

    fa = all_al.copy()
    if sev_f != "All": fa = fa[fa["severity"]==sev_f]
    if type_f != "All": fa = fa[fa["alert_type"]==type_f]

    sev_icons = {"CRITICAL":"â—","HIGH":"â—","MEDIUM":"â—","LOW":"â—"}
    sev_cols_map = {"CRITICAL":IBM_RED,"HIGH":IBM_ORANGE,"MEDIUM":IBM_YELLOW,"LOW":IBM_GREEN}
    st.markdown(f"<div style='font-size:0.75rem;color:{IBM_GRAY_60};margin-bottom:8px;'>"
                f"Showing {len(fa)} of {len(all_al)} alerts</div>", unsafe_allow_html=True)
    for _, row in fa.head(30).iterrows():
        sev = row["severity"]
        sc2 = sev_cols_map.get(sev, IBM_GRAY_60)
        st.markdown(f"""
        <div class="alert-card alert-{sev}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
            <div style="flex:1;">
              <span style="color:{sc2};font-weight:700;font-size:0.72rem;letter-spacing:0.08em;">
                {sev_icons.get(sev,'â—')} {row['alert_type']}
              </span>
              <div style="margin-top:3px;">{row['message']}</div>
            </div>
            <div style="font-size:0.68rem;color:{IBM_GRAY_60};white-space:nowrap;font-family:'IBM Plex Mono',monospace;">
              {row['created_at'][:16] if row['created_at'] else ''}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    if fa.empty:
        st.markdown(f"<div style='color:{IBM_GREEN};padding:24px;text-align:center;border:1px solid {IBM_GRAY_80};'>"
                    f"âœ“ No alerts match the current filter</div>", unsafe_allow_html=True)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TAB 6 â€” INSIGHTS & REPORT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
with T[6]:
    @st.cache_data(ttl=300)
    def ins():
        try:
            r = calculate_stockout_risk()
        except Exception:
            r = None
        return get_actionable_insights(stockout_df=r)
    insights = ins()
    k2 = get_kpi_summary()

    # Health score
    health = min(100, max(0,
        k2.get("on_time_rate",75) * 0.5 +
        max(0, 100 - k2.get("critical_alerts",0) * 5) * 0.3 +
        max(0, 100 - k2.get("avg_delay_days",0) * 10) * 0.2
    ))
    health_color = IBM_GREEN if health >= 75 else IBM_ORANGE if health >= 50 else IBM_RED
    health_label = "GOOD" if health >= 75 else "AT RISK" if health >= 50 else "CRITICAL"

    # Executive header
    now_str = datetime.now().strftime("%B %d, %Y â€” %H:%M UTC+5:30")
    st.markdown(f"""
    <div style="background:{IBM_GRAY_90};border:1px solid {IBM_GRAY_80};
                border-left:4px solid {IBM_BLUE};padding:20px 24px;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;
                      letter-spacing:0.1em;margin-bottom:6px;">IBM SUPPLY CHAIN INTELLIGENCE</div>
          <div style="font-size:1.4rem;font-weight:700;color:{IBM_WHITE};">Executive Summary Report</div>
          <div style="font-size:0.78rem;color:{IBM_GRAY_60};margin-top:4px;font-family:'IBM Plex Mono',monospace;">{now_str}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.65rem;color:{IBM_GRAY_60};text-transform:uppercase;letter-spacing:0.1em;">CHAIN HEALTH</div>
          <div style="font-size:2.2rem;font-weight:700;color:{health_color};font-family:'IBM Plex Mono',monospace;">{health:.0f}</div>
          <div style="font-size:0.75rem;color:{health_color};font-weight:600;">{health_label}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Health gauge
    col_g, col_kpi = st.columns([1, 2])
    with col_g:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(health, 1),
            number={"font": {"color": health_color, "size": 38, "family": "IBM Plex Mono"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": IBM_GRAY_60,
                         "tickfont": {"color": IBM_GRAY_60, "size": 10}},
                "bar":  {"color": health_color, "thickness": 0.25},
                "bgcolor": IBM_GRAY_80,
                "bordercolor": IBM_GRAY_70,
                "steps": [
                    {"range": [0,  50], "color": "rgba(218,30,40,0.15)"},
                    {"range": [50, 75], "color": "rgba(255,131,43,0.15)"},
                    {"range": [75,100], "color": "rgba(36,161,72,0.15)"},
                ],
                "threshold": {"value": 80, "line": {"color": IBM_BLUE, "width": 2},
                              "thickness": 0.8}
            }
        ))
        fig_g.update_layout(**{k: v for k, v in PLOTLY_TEMPLATE["layout"].items()
                               if k not in ["xaxis","yaxis","margin"]},
                           height=260, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_g, width='stretch')

    with col_kpi:
        st.markdown(f"<div class='ibm-section'>KEY PERFORMANCE INDICATORS</div>", unsafe_allow_html=True)
        kpi_rows = [
            ("Inventory Value",        f"${k2.get('inventory_value',0):>14,.0f}", IBM_BLUE_LIGHT),
            ("Total Units in Stock",   f"{k2.get('total_units',0):>14,}",         IBM_GRAY_10),
            ("On-Time Delivery Rate",  f"{k2.get('on_time_rate',0):>13.1f}%",     IBM_GREEN if k2.get('on_time_rate',0)>=90 else IBM_ORANGE),
            ("Orders Last 30 Days",    f"{k2.get('total_orders_30d',0):>14,}",    IBM_GRAY_10),
            ("Currently In Transit",   f"{k2.get('in_transit',0):>14,}",          IBM_BLUE_LIGHT),
            ("Active Alerts",          f"{k2.get('active_alerts',0):>14,}",       IBM_YELLOW),
            ("Critical Alerts",        f"{k2.get('critical_alerts',0):>14,}",     IBM_RED),
            ("Avg Delay (when delayed)",f"{k2.get('avg_delay_days',0):>13.1f}d",  IBM_ORANGE if k2.get('avg_delay_days',0)>3 else IBM_GREEN),
        ]
        for lbl, val, col in kpi_rows:
            st.markdown(f"""<div style="display:flex;justify-content:space-between;
              padding:6px 0;border-bottom:1px solid {IBM_GRAY_80};font-size:0.82rem;">
              <span style="color:{IBM_GRAY_60};">{lbl}</span>
              <span style="color:{col};font-family:'IBM Plex Mono',monospace;font-weight:600;">{val}</span>
            </div>""", unsafe_allow_html=True)

    # Recommendations
    st.markdown(f"<div class='ibm-section'>ACTIONABLE RECOMMENDATIONS</div>", unsafe_allow_html=True)
    icon_map = {"CRITICAL":"ðŸ”´","HIGH":"ðŸŸ ","MEDIUM":"ðŸŸ¡"}
    color_map = {"CRITICAL": IBM_RED, "HIGH": IBM_ORANGE, "MEDIUM": IBM_YELLOW}
    for ins_item in insights:
        pri = ins_item["priority"]
        col = color_map.get(pri, IBM_BLUE)
        icon = icon_map.get(pri, "ðŸ”µ")
        with st.expander(f"{icon}  {ins_item['title']}", expanded=(pri=="CRITICAL")):
            if not ins_item["data"].empty:
                st.dataframe(ins_item["data"], width='stretch', height=220)

    # Lead-time reduction
    st.markdown(f"<div class='ibm-section'>LEAD TIME REDUCTION OPPORTUNITIES</div>", unsafe_allow_html=True)
    lrq = """
        SELECT sup.supplier_name, sup.country,
               ROUND(AVG(CAST(julianday(o.actual_delivery_date)-julianday(o.order_date) AS REAL)),1) as avg_lead,
               ROUND(AVG(CAST(julianday(o.expected_delivery_date)-julianday(o.order_date) AS REAL)),1) as exp_lead,
               COUNT(*) as n
        FROM orders o JOIN suppliers sup ON o.supplier_id=sup.supplier_id
        WHERE o.status='Delivered' AND o.actual_delivery_date IS NOT NULL
        GROUP BY sup.supplier_id HAVING n>=5 ORDER BY avg_lead DESC LIMIT 10
    """
    lrdf = execute_query(lrq)
    if not lrdf.empty:
        lrdf["excess"] = (lrdf["avg_lead"] - lrdf["exp_lead"]).clip(lower=0)
        fig_lr = go.Figure()
        fig_lr.add_bar(x=lrdf["supplier_name"], y=lrdf["exp_lead"],
                      name="Expected Lead Time", marker_color=IBM_BLUE)
        fig_lr.add_bar(x=lrdf["supplier_name"], y=lrdf["excess"],
                      name="Excess (Reducible)", marker_color=IBM_RED,
                      text=lrdf["excess"].apply(lambda v: f"+{v:.1f}d"),
                      textposition="outside", textfont_color=IBM_RED)
        fig_lr.update_layout(barmode="stack", title="Lead Time Breakdown â€” Expected vs Excess Days",
                            legend_title_text="Component")
        fig_lr.update_xaxes(tickangle=30)
        st.plotly_chart(apply_ibm(fig_lr, 360), width='stretch')

    # Downloads
    st.markdown(f"<div class='ibm-section'>EXPORT REPORTS</div>", unsafe_allow_html=True)
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        @st.cache_data(ttl=300)
        def risk_csv():
            try:
                return calculate_stockout_risk().to_csv(index=False)
            except Exception:
                return ""
        st.download_button("â¬‡  STOCKOUT RISK REPORT", data=risk_csv(),
                          file_name=f"IBM_stockout_{datetime.now():%Y%m%d}.csv",
                          mime="text/csv")
    with dc2:
        al_dl = get_active_alerts(limit=1000)
        if not al_dl.empty:
            st.download_button("â¬‡  ACTIVE ALERTS", data=al_dl.to_csv(index=False),
                              file_name=f"IBM_alerts_{datetime.now():%Y%m%d}.csv",
                              mime="text/csv")
    with dc3:
        sup_dl = get_supplier_performance()
        if not sup_dl.empty:
            st.download_button("\u2b07  SUPPLIER SCORECARD", data=sup_dl.to_csv(index=False),
                              file_name=f"IBM_suppliers_{datetime.now():%Y%m%d}.csv",
                              mime="text/csv")

    st.markdown(f"<div class='ibm-section'>FULL INSIGHT REPORT (HTML)</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="insight-card" style="margin-bottom:12px;">
      <b style="color:{IBM_BLUE_LIGHT};">Generate Complete IBM Supply Chain Intelligence Report</b><br/>
      <span style="color:{IBM_GRAY_30};font-size:0.82rem;">
      Produces a professional IBM-branded HTML report with KPIs, critical stockout items,
      alert summary, supplier bottleneck analysis, delay impact, and actionable recommendations.
      </span>
    </div>""", unsafe_allow_html=True)
    if st.button("GENERATE FULL HTML REPORT"):
        with st.spinner("Generating IBM Supply Chain Intelligence Report..."):
            try:
                from reports.generate_report import generate_html_report
                report_path = generate_html_report()
                with open(report_path, "r", encoding="utf-8") as rf:
                    report_html = rf.read()
                st.download_button(
                    label="\u2b07 DOWNLOAD HTML REPORT",
                    data=report_html,
                    file_name=f"IBM_Supply_Chain_Report_{datetime.now():%Y%m%d_%H%M%S}.html",
                    mime="text/html"
                )
                st.success("Report generated! Click the button above to download.")
            except Exception as e:
                st.error(f"Report generation failed: {e}")

    st.markdown(f"""
    <div class="ibm-footer">
      IBM Supply Chain Intelligence Platform &nbsp;Â·&nbsp;
      Built on IBM Carbon Design System &nbsp;Â·&nbsp;
      Powered by Ridge Regression &amp; Statistical Risk Modelling &nbsp;Â·&nbsp;
      Â© {datetime.now().year} IBM Corporation
    </div>
    """, unsafe_allow_html=True)

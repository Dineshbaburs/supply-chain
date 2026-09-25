# Supply-Chain Visibility via Data Analytics
## Project 2 — IBM Supply Chain Dashboard

A comprehensive supply-chain monitoring and forecasting solution built with Python, Streamlit, and SQLite.

---

## Architecture

```
supply_chain/
├── setup.py                 # One-time setup: simulate data + run models
├── requirements.txt
├── data/
│   └── data_simulator.py    # Generates synthetic DataCo/Olist/M5-style data
├── database/
│   └── db_manager.py        # SQLite connection & CRUD helpers
├── pipeline/
│   └── analytics.py         # Query functions for all dashboard views
├── models/
│   ├── demand_forecast.py   # Ridge regression forecasting (30-day horizon)
│   └── stockout_risk.py     # Probabilistic stockout risk + bottleneck detection
├── alerts/
│   └── alert_system.py      # Alert generation for stockouts, delays, disruptions
├── dashboard/
│   └── app.py               # Streamlit multi-tab dashboard
└── reports/                 # Downloaded CSV reports saved here
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run data simulation & model setup (one-time)
```bash
python setup.py
```
This will:
- Initialize the SQLite database
- Simulate 2 years of supply chain data (50 products, 10 warehouses, 20 suppliers)
- Generate 5,000 orders with shipping & delays
- Calculate stockout risk for all product-warehouse combos
- Generate initial alerts

### 3. Launch the dashboard
```bash
streamlit run dashboard/app.py
```

---

## Features

### Dashboard Tabs
| Tab | Contents |
|-----|----------|
| Overview | KPI cards, weekly order trends, warehouse utilization |
| Inventory & Stockout | Stockout probability scatter, risk distribution, critical items |
| Shipments & Orders | Carrier performance, delay heatmap, lead-time box plots |
| Demand Forecast | Weekly trends, category heatmap, 30-day ML forecast |
| Supplier Analysis | Performance scatter, bottleneck detection, scorecard |
| Alerts | Alert center with severity filters and type breakdown |
| Insights & Report | Executive summary, health score gauge, recommendations, CSV downloads |

### Filters (Sidebar)
- Region, Category, Product, Warehouse, Supplier, Date range

### Predictive Analytics
- **Demand forecasting**: Ridge regression with seasonal features, lag features, rolling statistics
- **Stockout risk**: Statistical model — P(demand_over_lead_time > current_stock) using normal distribution
- **Bottleneck detection**: Supplier delay rate + reliability scoring
- **Lead time estimation**: Actual vs expected delivery analysis

### Alert Types
- `STOCKOUT_CRITICAL` — Stockout probability ≥ 70%
- `STOCKOUT_HIGH` — Stockout probability ≥ 40%
- `LOW_STOCK` — ≤ 7 days of stock remaining
- `SHIPMENT_DELAY` — Active delayed shipments
- `SUPPLIER_DISRUPTION` — Supplier delay rate ≥ 25%
- `DEMAND_SPIKE` — Recent demand 1.5× above baseline

---

## Data Sources (Simulated)

| Dataset | Source Inspiration | Usage |
|---------|-------------------|-------|
| Orders & Shipments | DataCo Smart Supply Chain | Shipment status, delays, fulfillment |
| Lead Time | Olist Brazilian E-Commerce | Purchase→delivery lead time analysis |
| Demand History | M5 Forecasting (Walmart) | Daily demand with seasonal patterns |
| Inventory | Simulated | Stock levels with reorder logic |

**Note**: All data is synthetically generated. Assumptions documented in `data_simulator.py`.

---

## Stockout Risk Formula

```
P(stockout) = P(demand_over_lead_time > available_stock)

Where:
  demand_over_lead_time ~ Normal(avg_daily_demand × L, demand_std × √L)
  L = lead_time_days (default: 14)

Z-score = (available_stock - expected_lead_demand) / demand_std
P(stockout) = 1 - Φ(Z)
```

---

## Technology Stack
- **Language**: Python 3.10+
- **Dashboard**: Streamlit + Plotly
- **Database**: SQLite (via SQLAlchemy)
- **ML**: scikit-learn (Ridge Regression)
- **Statistics**: SciPy, StatsModels
- **Data**: Pandas, NumPy
- **Simulation**: Faker

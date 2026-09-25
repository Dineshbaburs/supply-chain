# Supply-Chain Visibility via Data Analytics
## IBM Supply Chain Intelligence Platform — Enterprise Edition
**Academic & Industry Capstone Project — CHRIST (Deemed to be University) & IBM**

A real-time supply chain monitoring, predictive analytics, and forecasting solution designed to reduce lead times, mitigate shipment delays, and eliminate inventory stockouts.

---

## 1. Compliance & Dataset Citations (Ground Rules)

In strict accordance with the project guidelines:
- **No Personal Data**: All data ingested or simulated is either public or synthetically generated. No Personally Identifiable Information (PII) is included.
- **License Respect**: Inputs are derived from authorized public benchmark structures. Raw proprietary datasets requiring authentication are not distributed.
- **Zero Committed Credentials**: All Db2 database and IBM MQ connection parameters are managed via environment variables in `.env` (strictly ignored by `.gitignore`). A template `.env.example` with blank keys is committed.
- **Genuine Analytics**: Predictions are calculated in real time using Ridge Regression ML, probabilistic Normal CDF distributions, and composite supplier delay scoring.

### Dataset Citations

| Dataset Name | Source URL | License | Role in System |
|:---|:---|:---|:---|
| **DataCo Smart Supply Chain for Big Data Analysis** | [Kaggle Link](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis) | CC0: Public Domain | Supply chain operations, delivery delays, carrier routing, order fulfillment status, shipment tracking |
| **Brazilian E-Commerce Public Dataset by Olist** | [Kaggle Link](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) | CC BY-NC-SA 4.0 | Multi-echelon lead time distributions, seller performance, estimated vs actual delivery dates |
| **M5 Forecasting — Accuracy (Walmart)** | [Kaggle Link](https://www.kaggle.com/c/m5-forecasting-accuracy) | Kaggle Competition / Academic Use | Multi-product historical daily sales, day-of-week demand patterns, seasonality features for ML forecasting |

---

## 2. Architecture & Data Flow

```
                      ┌───────────────────────────────────────┐
                      │  Raw Static Datasets (CSV Benchmark)  │
                      └──────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       [Batch Ingestion Engine]                   [IBM MQ Live Replay Stream]
        setup_db2.py / setup.py                    pipeline/mq_publisher.py
      (Chunked loading: 5000 rows)                (Replay row-by-row at rate_hz)
                   │                                           │
                   ▼                                           ▼
      ┌─────────────────────────┐               ┌─────────────────────────────┐
      │   IBM Db2 (Cloud)  OR   │ ◄──────────── │   IBM MQ Message Consumer   │
      │   SQLite (Local Mode)   │               │   pipeline/mq_consumer.py   │
      └────────────┬────────────┘               └─────────────────────────────┘
                   │
                   ▼
      ┌─────────────────────────┐
      │  Predictive Analytics   │
      │  • Ridge Regression     │
      │  • P(Stockout) CDF      │
      │  • Bottleneck Scorer    │
      │  • Delay Impact Model   │
      └────────────┬────────────┘
                   │
                   ▼
      ┌─────────────────────────┐
      │  Alert Engine (452 alerts)
      │  CRITICAL / HIGH / MED  │
      └────────────┬────────────┘
                   │
       ┌───────────┴────────────────────────┐
       ▼                                    ▼
┌───────────────────────────────┐ ┌───────────────────────────────────┐
│ Streamlit Enterprise Dashboard│ │ IBM HTML Report Generator         │
│ (Carbon Design System, 7 tabs)│ │ reports/generate_report.py        │
└───────────────────────────────┘ └───────────────────────────────────┘
```

---

## 3. Project Directory Structure

```
supply_chain/
├── .env.example              # Template credentials file (NEVER commit .env)
├── .gitignore                # Excludes credentials, databases, cache, and logs
├── requirements.txt          # Python dependencies
├── setup.py                  # One-click local pipeline initialization
├── setup_db2.py              # IBM Db2 chunked data loader (company guide standard)
├── push.bat / push.ps1       # 1-click Git auto-commit & push helper scripts
│
├── data/
│   ├── data_simulator.py     # Generates 2-year realistic supply chain dataset
│   ├── supply_chain.db       # Embedded local SQLite database
│   └── raw/                  # Exported CSVs ready for IBM MQ replay streaming
│
├── database/
│   └── db_manager.py         # Dual-mode engine (IBM Db2 Cloud + SQLite Local fallback)
│
├── pipeline/
│   ├── analytics.py          # Unified KPI and filtering analytics query engine
│   ├── data_pipeline.py      # Background continuous streaming tick simulator
│   ├── mq_publisher.py       # Live stream publisher (replays CSVs to IBM MQ)
│   └── mq_consumer.py        # Stream consumer (reads MQ queue and inserts to DB)
│
├── models/
│   ├── demand_forecast.py    # Ridge Regression demand forecast (30-day horizon)
│   └── stockout_risk.py      # Probabilistic Normal CDF stockout risk + delay impact
│
├── alerts/
│   └── alert_system.py       # Multi-level alert generator (6 types, 4 severities)
│
├── dashboard/
│   └── app.py                # IBM Carbon-styled 7-tab Streamlit dashboard
│
└── reports/
    └── generate_report.py    # Generates standalone IBM-branded HTML intelligence reports
```

---

## 4. Quick Start (Local Development Mode)

### Step 1: Environment Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Step 2: Initialize Database & Run Models
```powershell
python setup.py
```
This automatically:
1. Simulates 2 years of logistics history (48 products, 10 warehouses, 20 suppliers, 5,000 orders, 4,300 shipments, 350,880 daily demand records).
2. Runs 30-day Ridge Regression demand forecasts.
3. Calculates stockout probability across all 480 SKU-locations.
4. Generates 450+ multi-tier operational alerts.
5. Exports raw CSV datasets to `data/raw/` for streaming replay.

### Step 3: Launch the Dashboard
```powershell
streamlit run dashboard/app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

## 5. Enterprise IBM Cloud & Db2 Setup

### Step 1: Configure Credentials
Copy `.env.example` to `.env` and fill in your team credentials:
```ini
# IBM Db2 Connection
DB2_HOST=dashdb-txn-sbox-yp-dal09-04.services.dal.bluemix.net
DB2_PORT=50000
DB2_DATABASE=BLUDB
DB2_USER=your_db2_user
DB2_PASSWORD=your_db2_password
DB2_SCHEMA=TEAM3

# IBM MQ Connection
MQ_HOST=mq-host.quantum.ibm.com
MQ_PORT=1414
MQ_QMGR=QM1
MQ_CHANNEL=DEV.APP.SVRCONN
MQ_USER=app
MQ_PASSWORD=your_mq_password
MQ_QUEUE=TEAM3.SUPPLYCHAIN

# Mode
DASHBOARD_MODE=cloud
```

### Step 2: Load Data into IBM Db2
```powershell
python setup_db2.py
```
This loads raw CSV data into Db2 using SQLAlchemy chunked execution (`chunksize=5000`) according to IBM guidelines.

---

## 6. Real-Time Streaming via IBM MQ Replay

To turn static datasets into a live stream (per company guidelines):

### 1. Start the Publisher (Sends messages to MQ)
```powershell
# Replay order stream at 2 rows per second in a continuous loop:
python pipeline/mq_publisher.py --dataset orders --rate 2.0 --loop

# Replay shipment tracking stream:
python pipeline/mq_publisher.py --dataset shipments --rate 1.0
```

### 2. Start the Consumer (Ingests MQ messages into Db2)
```powershell
python pipeline/mq_consumer.py
```
*(If IBM MQ hardware credentials are not present, both publisher and consumer seamlessly fall back to local in-memory simulation mode).*

---

## 7. Mathematical & Statistical Models

### 1. Probabilistic Stockout Risk Model
Calculates the probability of demand over the supplier lead time exceeding available stock:

$$\mu_L = \bar{D}_{\text{daily}} \times L$$

$$\sigma_L = \sigma_{\text{daily}} \times \sqrt{L}$$

$$Z = \frac{\text{Available Stock} - \mu_L}{\sigma_L}$$

$$P(\text{Stockout}) = 1 - \Phi(Z)$$

Where:
- $\bar{D}_{\text{daily}}$ = 30-day historical mean daily demand
- $\sigma_{\text{daily}}$ = standard deviation of daily demand
- $L$ = supplier lead time in days
- $\Phi(Z)$ = standard normal cumulative distribution function (CDF)

Risk Categories:
- **CRITICAL**: $P(\text{Stockout}) \ge 70\%$ or Days of Stock $\le 3$
- **HIGH**: $P(\text{Stockout}) \ge 40\%$ or Days of Stock $\le 7$
- **MEDIUM**: Days of Stock $\le 14$
- **LOW**: Sufficient coverage

### 2. Machine Learning Demand Forecast
- **Algorithm**: Ridge Regression (L2 Regularized Linear Model)
- **Features**: Day-of-week, month, quarter, weekend indicator, seasonal sine/cosine cycles, rolling 7-day and 28-day demand means, lag-1, lag-7, and lag-14 features.
- **Horizon**: 30 days ahead with 95% confidence intervals.

### 3. Supply Chain Bottleneck Detection
Composite bottleneck score combining:
- Supplier historical delay rate ($40\%$ weight)
- Average delay severity ($30\%$ weight)
- Inverse reliability score ($20\%$ weight)
- Lead time variability ($10\%$ weight)

---

## 8. Dashboard Features (7 Tabs)

1. **Overview**: Executive health score gauge (0-100), key metrics, order trends, warehouse capacity utilization.
2. **Inventory & Risk**: Probabilistic stockout scatter matrix, risk distribution donut, inventory category bars, critical SKU reorder table, delay impact estimation.
3. **Shipments**: Carrier performance comparisons, delivery delay heatmaps, lead-time distribution box plots, active shipment tracking table.
4. **Demand Forecast**: 30-day predictive demand charts with confidence bands, weekly pattern analysis, category demand distribution.
5. **Suppliers**: Supplier scorecard with color-coded delay rates, bottleneck radar/scatter, regional disruption analysis.
6. **Alerts**: Real-time operational incident center with severity filtering (Critical, High, Medium) and resolution acknowledgement.
7. **Insights & Report**: Actionable recommendations, lead-time reduction opportunities, CSV data exports, and 1-click **IBM HTML Report Generator**.

---

## 9. Technology Stack

- **Languages & Frameworks**: Python 3.11, Streamlit 1.56, Plotly 7.1
- **Enterprise Middleware**: IBM Db2, IBM MQ (`pymqi` / REST API), SQLAlchemy, `python-dotenv`
- **Machine Learning & Stats**: scikit-learn, SciPy, Statsmodels, Pandas, NumPy
- **Styling**: IBM Carbon Design System (Plex Sans & Plex Mono fonts, dark Carbon theme `#161616`)

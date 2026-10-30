# Supply-Chain Visibility via Data Analytics
## IBM Supply Chain Intelligence Platform — Enterprise Edition
**Academic & Industry Capstone Project — CHRIST (Deemed to be University) & IBM**

A real-time supply chain monitoring, predictive analytics, and forecasting solution designed to reduce lead times, mitigate shipment delays, and eliminate inventory stockouts.

---

## 1. Compliance & Dataset Citations (Ground Rules)

In strict accordance with the project guidelines:
- **No Personal Data**: All data ingested or simulated is either public or sanitized. No Personally Identifiable Information (PII) is included.
- **License Respect**: Inputs are derived from authorized public benchmark structures. Raw proprietary datasets requiring authentication are not distributed.
- **Zero Committed Credentials**: All Db2 database and IBM MQ connection parameters are managed via environment variables in `.env` (strictly ignored by `.gitignore`). A template `.env.example` with blank keys is committed.
- **Genuine Analytics**: Predictions are calculated in real time using Ridge Regression ML, probabilistic Normal CDF distributions, and composite supplier delay scoring.

### Dataset Citations (Official Company Assignment Links)

| Dataset Name | Source Link | License / Notes | Operational Role in Project |
|:---|:---|:---|:---|
| **DataCo Smart Supply Chain** | [Mendeley Data Link](https://data.mendeley.com/datasets/8gx2fvg2k6/5) | **CC BY 4.0** (No login needed) | 169,149 orders, 65,752 shipments, delivery delays (actual vs. scheduled shipping days), regional distribution, and fulfillment status across 118 authentic products. |
| **Olist Brazilian E-commerce** | [Kaggle Dataset](https://www.kaggle.com/datasets/olistbr/brazilianecommerce) | **CC BY-NC-SA 4.0** (~100k orders 2016-2018, Kaggle login) | Multi-echelon lead-time analysis (purchase date vs. delivery date vs. estimated delivery SLA), evaluating 1,864 authentic sellers with genuine lead days and on-time reliability scores. |
| **M5 Forecasting (Walmart)** | [Kaggle Competition](https://www.kaggle.com/c/m5-forecasting-accuracy) | **Kaggle Evaluation License** (Kaggle login & rules accepted) | Evaluates baseline (Seasonal-Naive lag-7 persistence) vs. Ridge Regression ML with Fourier calendar seasonality and rolling demand patterns. |

---

### Company "How to Use It" — 6-Point Implementation Matrix

| # | Company Instruction | Project Implementation | File / Feature |
|:---|:---|:---|:---|
| **1** | **DataCo for shipment status & delays**: Compare actual against scheduled shipping days, regions, fulfillment. | Ingests **169,149 order lines** and **65,752 shipments**. Calculates delay days ($T_{\text{actual}} - T_{\text{scheduled}}$), status categorization (`Delivered`, `In Transit`, `Delayed`, `Cancelled`), carrier breakdown, and regional tracking across 23 global regions. | [`pipeline/analytics.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/analytics.py)<br/>Tab 3 (`SHIPMENTS`) |
| **2** | **Olist for lead-time analysis**: Purchase date vs. delivery date vs. estimated delivery & supplier performance. | Evaluates **1,864 qualified Olist sellers** from 112,650 order items: computes actual lead times ($T_{\text{delivered}} - T_{\text{purchased}}$), on-time delivery rate ($T_{\text{delivered}} \le T_{\text{estimated}}$), reliability score ($0.40-1.0$), and bottleneck scoring. | [`models/stockout_risk.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/stockout_risk.py)<br/>Tab 5 (`SUPPLIERS`) |
| **3** | **M5 for demand forecasting**: Baseline (Seasonal-Naive) first, then better model. | Evaluates **Seasonal-Naive baseline (lag-7 persistence)** against **Ridge Regression ML** with Fourier seasonality and rolling metrics using an **85/15 chronological train/test split**. Reports MAE, RMSE, and +27.9% accuracy gain. | [`models/demand_forecast.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/demand_forecast.py)<br/>Tab 4 (`DEMAND FORECAST`) |
| **4** | **Simulate warehouse stock & inventory levels**: Document starting stock, replenishment rules, lead times. | Formulated in `data/ingest_real_data.py`: Starting stock based on 30-day moving average demand across 3 risk tiers (critical 15%, warning 15%, healthy 70%), continuous $(s, Q)$ replenishment policy, and supplier lead time variability across 1,416 SKU-locations. | [`data/ingest_real_data.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/data/ingest_real_data.py)<br/>Tab 2 (`INVENTORY & RISK`) |
| **5** | **Real-time MQ stream in date order**: Replay orders chronologically through MQ, update Db2. | Replays CSV data sorted chronologically by `order_date` via IBM MQ queue (`pipeline/mq_publisher.py`), consumed and inserted into Db2/SQLite in real time (`pipeline/mq_consumer.py`). | [`pipeline/mq_publisher.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/mq_publisher.py)<br/>[`pipeline/mq_consumer.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/mq_consumer.py) |
| **6** | **Stockout risk & high probability alerts**: Forecast demand over lead time vs. stock. | Evaluates $P(\text{Stockout}) = 1 - \Phi\left(\frac{\text{Stock} - \mu_L}{\sigma_L}\right)$. Generates 1,437 multi-level alerts: `STOCKOUT_CRITICAL` ($\ge 70\%$), `STOCKOUT_HIGH` ($\ge 40\%$), and `LOW_STOCK`. | [`models/stockout_risk.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/stockout_risk.py)<br/>Tab 6 (`ALERTS`) |

---

## 2. Architecture & Data Flow

```
                      ┌────────────────────────────────────────────────────────┐
                      │    Clean IBM Benchmarks (DataCo 169k + Olist 100k)     │
                      └───────────────────────────┬────────────────────────────┘
                                                  │
                            ┌─────────────────────┴─────────────────────┐
                            ▼                                           ▼
                [Batch Ingestion Engine]                   [IBM MQ Live Replay Stream]
               data/ingest_real_data.py                     pipeline/mq_publisher.py
             (Chunked loading: 5000 rows)                 (Replay row-by-row at rate_hz)
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
               │  • Ridge Regression ML  │
               │  • P(Stockout) CDF      │
               │  • Bottleneck Scorer    │
               │  • Delay Impact Model   │
               └────────────┬────────────┘
                            │
                            ▼
               ┌─────────────────────────┐
               │ Alert Engine (1,437)    │
               │ CRITICAL / HIGH / MED   │
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
├── setup.py                  # One-click local pipeline initialization (ingests clean datasets)
├── setup_db2.py              # IBM Db2 chunked data loader (company guide standard)
├── push.bat / push.ps1       # 1-click Git auto-commit & push helper scripts
│
├── Given_dataset/            # Clean benchmark source datasets provided by IBM
│   ├── DS1/processed/        # DataCo orders (169k), shipments (180k), products (118)
│   └── DS2/processed/        # Olist orders (99k), items (112k), sellers (3k)
│
├── data/
│   ├── ingest_real_data.py   # Primary ETL engine loading DataCo + Olist into relational SQL
│   ├── data_simulator.py     # Standalone synthetic simulation engine (fallback)
│   ├── supply_chain.db       # High-performance local SQLite database with indexed queries
│   └── raw/                  # Clean exported CSVs ready for IBM MQ replay streaming
│
├── database/
│   └── db_manager.py         # Dual-mode engine (IBM Db2 Cloud + SQLite Local fallback with indexes)
│
├── pipeline/
│   ├── analytics.py          # Unified KPI and filtering analytics query engine
│   ├── data_pipeline.py      # Background continuous streaming tick simulator
│   ├── mq_publisher.py       # Live stream publisher (replays CSVs to IBM MQ)
│   └── mq_consumer.py        # Stream consumer (reads MQ queue and inserts to DB)
│
├── models/
│   ├── demand_forecast.py    # Ridge Regression demand forecast vs. Seasonal-Naive baseline
│   └── stockout_risk.py      # Probabilistic Normal CDF stockout risk + delay impact
│
├── alerts/
│   └── alert_system.py       # Multi-level alert generator (4 types, 4 severities)
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
1. **Ingests Clean IBM Datasets**:
   - DataCo: 169,149 order lines, 65,752 shipments, 118 authentic products.
   - Olist: 1,864 qualified Brazilian sellers with calculated lead times and SLA reliability scores.
   - 12 Global Distribution Centers (Frankfurt, Singapore, Sao Paulo, Sydney, Mumbai, Shanghai, LA, NY, Dubai, etc.).
2. **Aggregates Real Demand History**: 38,655 daily historical demand records.
3. **Simulates Inventory State**: 1,416 SKU-warehouse pairs with continuous $(s, Q)$ review policy across 3 risk tiers (Critical 15%, Warning 15%, Healthy 70%).
4. **Trains Machine Learning Forecasts**: 30-day forward demand forecasts comparing Seasonal-Naive baseline vs. Ridge Regression ML.
5. **Calculates Stockout Risk**: Evaluates Normal CDF probabilities across all 1,416 SKU-locations.
6. **Generates Operational Alerts**: 1,437 multi-tier operational alerts stored in DB.
7. **Exports Clean CSVs**: Ready in `data/raw/` for IBM MQ streaming replay.

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
- **Features**: Day-of-week, month, quarter, weekend indicator, seasonal Fourier sine/cosine cycles ($\sin(2\pi \cdot \text{doy}/365)$, $\cos(2\pi \cdot \text{doy}/365)$), rolling 7-day, 14-day, and 28-day demand means, rolling 7-day std, and lag-7, lag-14, lag-21, and lag-28 features.
- **Train/Test Split Strategy**: 
  - In strict compliance with time-series evaluation principles (avoiding future data leakage), data is split **chronologically**: the first **85%** of historical observations serve as the training set, and the final **15%** serve as the holdout test set.
- **Baseline Comparison (M5 Specification)**:
  - Benchmark Model: **Seasonal-Naive (Lag-7 Persistence)**: $\hat{y}_t = y_{t-7}$.
  - Ridge Regression consistently outperforms the Seasonal-Naive baseline, yielding an average **+27.9% improvement in Root Mean Squared Error (RMSE)**.
- **Horizon**: 30 days forward with 95% confidence intervals ($\pm 1.96\sigma$).

### 3. Supply Chain Bottleneck Detection
Composite bottleneck score combining:
- Supplier historical delay rate ($50\%$ weight)
- Average delay severity ($30\%$ weight)
- Inverse reliability score ($20\%$ weight)

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

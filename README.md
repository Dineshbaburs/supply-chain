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
| **M5 Forecasting (Walmart)** | [Kaggle Competition](https://www.kaggle.com/c/m5-forecasting-accuracy) | **Kaggle Evaluation License** (Kaggle login & rules accepted) | Evaluates baseline (**Seasonal-Naive lag-7 persistence**) vs. **Ridge Regression ML** with Fourier calendar seasonality, SNAP food stamp indicators, and national event triggers across 1,913 days in `FOODS`, `HOBBIES`, and `HOUSEHOLD`. Precomputed into `m5_forecasts` table. |

---

### Company "How to Use It" — 6-Point Implementation Matrix

| # | Company Instruction | Project Implementation | File / Feature |
|:---|:---|:---|:---|
| **1** | **DataCo for shipment status & delays**: Compare actual against scheduled shipping days, regions, fulfillment. | Ingests **169,149 order lines** and **65,752 shipments**. Calculates delay days ($T_{\text{actual}} - T_{\text{scheduled}}$), status categorization (`Delivered`, `In Transit`, `Delayed`, `Cancelled`), carrier breakdown, and regional tracking across 23 global regions. | [`pipeline/analytics.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/analytics.py)<br/>Tab 3 (`SHIPMENTS`) |
| **2** | **Olist for lead-time analysis**: Purchase date vs. delivery date vs. estimated delivery & supplier performance. | Evaluates **1,864 qualified Olist sellers** from 112,650 order items: computes actual lead times ($T_{\text{delivered}} - T_{\text{purchased}}$), on-time delivery rate ($T_{\text{delivered}} \le T_{\text{estimated}}$), reliability score ($0.40-1.0$), and bottleneck scoring. | [`models/stockout_risk.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/stockout_risk.py)<br/>Tab 5 (`SUPPLIERS`) |
| **3** | **M5 for demand forecasting**: Baseline (Seasonal-Naive) first, then better model. | Evaluates **Seasonal-Naive baseline (lag-7 persistence)** against **Ridge Regression ML** with Fourier seasonality, SNAP flags, and event indicators on an **85/15 chronological train/test split**. Precomputes 1,320 benchmark forecasts achieving **+29.3% accuracy improvement** over baseline. | [`models/m5_forecaster.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/m5_forecaster.py)<br/>Tab 4 (`DEMAND FORECAST`) |
| **4** | **Simulate warehouse stock & inventory levels**: Document starting stock, replenishment rules, lead times. | Formulated in `data/ingest_real_data.py`: Starting stock based on 30-day moving average demand across 3 risk tiers (critical 15%, warning 15%, healthy 70%), continuous $(s, Q)$ replenishment policy, and supplier lead time variability across 1,416 SKU-locations. | [`data/ingest_real_data.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/data/ingest_real_data.py)<br/>Tab 2 (`INVENTORY & RISK`) |
| **5** | **Real-time MQ stream in date order**: Replay orders chronologically through MQ, update Db2. | Replays CSV data sorted chronologically by `order_date` via IBM MQ queue (`pipeline/mq_publisher.py`), consumed and inserted into Db2/SQLite in real time (`pipeline/mq_consumer.py`). | [`pipeline/mq_publisher.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/mq_publisher.py)<br/>[`pipeline/mq_consumer.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/pipeline/mq_consumer.py) |
| **6** | **Stockout risk & high probability alerts**: Forecast demand over lead time vs. stock. | Evaluates $P(\text{Stockout}) = 1 - \Phi\left(\frac{\text{Stock} - \mu_L}{\sigma_L}\right)$. Generates 1,437 multi-level alerts: `STOCKOUT_CRITICAL` ($\ge 70\%$), `STOCKOUT_HIGH` ($\ge 40\%$), and `LOW_STOCK`. | [`models/stockout_risk.py`](file:///C:/Users/rsddi/Desktop/OneDrive%20-%20CHRIST%20UNIVERSITY/IBM/IBM%20Project%20File/supply_chain/models/stockout_risk.py)<br/>Tab 6 (`ALERTS`) |

---

## 2. Architecture & Data Flow

```
                      ┌────────────────────────────────────────────────────────┐
                      │ Authentic Datasets: DataCo (169k) + Olist + Walmart M5 │
                      └───────────────────────────┬────────────────────────────┘
                                                  │
                            ┌─────────────────────┴─────────────────────┐
                            ▼                                           ▼
                [Batch Ingestion Engine]                   [IBM MQ Live Replay Stream]
                data/ingest_real_data.py                    pipeline/mq_publisher.py
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
                │  • DataCo Ridge Forecast│
                │  • M5 Benchmark Engine  │
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
├── setup.py                  # One-click pipeline setup (DataCo + Olist + M5 benchmarks)
├── setup_db2.py              # IBM Db2 chunked data loader (company guide standard)
├── push.bat / push.ps1       # 1-click Git auto-commit & push helper scripts
│
├── Given_dataset/            # Authentic datasets provided for the project
│   ├── DS1/processed/        # DataCo orders (169k), shipments (180k), products (118)
│   ├── DS2/processed/        # Olist orders (99k), items (112k), sellers (3k)
│   └── M5/                   # M5 Walmart cleaned calendar and sales train validation
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
│   ├── demand_forecast.py    # Ridge Regression demand forecast for DataCo supply chain
│   ├── m5_forecaster.py      # M5 Walmart Seasonal-Naive baseline vs Ridge ML benchmark
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
3. **Precomputes M5 Walmart Benchmarks (Instruction #3)**:
   - Ingests `cleaned_calendar.csv` and `cleaned_sales_train_validation.csv` (1,913 days).
   - Trains and evaluates Seasonal-Naive baseline vs. Ridge Regression ML across `FOODS`, `HOBBIES`, and `HOUSEHOLD`.
   - Stores 1,320 benchmark forecast records in `m5_forecasts` table (+29.3% RMSE accuracy gain).
4. **Simulates Inventory State**: 1,416 SKU-warehouse pairs with continuous $(s, Q)$ review policy across 3 risk tiers (Critical 15%, Warning 15%, Healthy 70%).
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

---

### 2. Machine Learning Demand Forecast (DataCo & M5 Walmart)
- **Algorithms**:
  - **Baseline Benchmark**: Seasonal-Naive model (Lag-7 weekly persistence): $\hat{y}_t = y_{t-7}$.
  - **Advanced ML Model**: Ridge Regression ($L_2$ regularized linear model with $\alpha=1.0$).
- **Engineered Features**:
  1. **Calendar Events**: National events (Super Bowl, Thanksgiving, Valentine's Day, Memorial Day, Easter) extracted from `calendar.csv`.
  2. **SNAP Assistance Flags**: Supplemental Nutrition Assistance Program benefit disbursement indicators (`snap_CA`, days 1-10 of month) driving grocery and household spikes.
  3. **Trigonometric Fourier Seasonality**: Annual ($\omega = \frac{2\pi}{365.25}$) and weekly ($\omega = \frac{2\pi}{7}$) harmonic sine and cosine pairs.
  4. **Multi-Horizon Lags & Rolling Windows**: $t-1, t-7, t-14, t-28$ lags plus 7-day rolling means and standard deviations.
- **Train/Test Split Strategy**:
  - Evaluated on an **85% chronological training window** and **15% out-of-sample holdout test window** (last 60 days) to prevent lookahead bias.
- **Benchmark Performance**:
  - **Ridge Regression ML achieves a +29.3% average RMSE reduction** over the Seasonal-Naive baseline across `FOODS`, `HOBBIES`, and `HOUSEHOLD` items.
  - Predicts **28-day forward out-of-sample projection** with a 95% Confidence Interval ($\pm 1.96 \sigma$).

---

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
4. **Demand Forecast**: Dual Analytics Engine:
   - **Supply Chain Products (DataCo)**: 30-day predictive demand charts with 95% confidence intervals, weekly pattern analysis, category intensity heatmaps.
   - **M5 Walmart Competition Benchmark (Instruction #3)**: Department selector (`FOODS`, `HOBBIES`, `HOUSEHOLD`), holdout test actuals vs. Ridge ML vs. Seasonal-Naive baseline, 28-day future projection, department accuracy leaderboard, and domain explanations for SNAP and Calendar events.
5. **Suppliers**: Supplier scorecard with color-coded delay rates, bottleneck radar/scatter, regional disruption analysis.
6. **Alerts**: Real-time operational incident center with severity filtering (Critical, High, Medium) and resolution acknowledgement.
7. **Insights & Report**: Actionable recommendations, lead-time reduction opportunities, CSV data exports (Stockout Risk, Alerts, Suppliers, M5 Benchmarks), and 1-click **IBM HTML Report Generator**.

---

## 9. Technology Stack

- **Languages & Frameworks**: Python 3.11, Streamlit 1.56, Plotly 7.1
- **Enterprise Middleware**: IBM Db2, IBM MQ (`pymqi` / REST API), SQLAlchemy, `python-dotenv`
- **Machine Learning & Stats**: scikit-learn, SciPy, Statsmodels, Pandas, NumPy
- **Styling**: IBM Carbon Design System (Plex Sans & Plex Mono fonts, dark Carbon theme `#161616`)

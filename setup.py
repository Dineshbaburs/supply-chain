"""
Supply Chain Setup Script
Initializes the database, ingests real datasets, runs forecasts (DataCo + M5), and generates alerts.
"""
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def main():
    print("=" * 60)
    print("  SUPPLY CHAIN VISIBILITY - SETUP & DATA PIPELINE")
    print("=" * 60)
    print()

    # Step 1: Ingest Clean IBM Datasets (DataCo + Olist)
    print("[1/5] Ingesting clean IBM datasets (DataCo & Olist)...")
    t0 = time.time()
    from data.ingest_real_data import main as ingest_clean_data
    ingest_clean_data()
    print(f"      Ingestion done in {time.time()-t0:.1f}s")
    print()

    # Step 2: Run demand forecasts (limited for speed)
    print("[2/5] Running demand forecasts (sample products)...")
    t0 = time.time()
    from models.demand_forecast import run_all_forecasts
    forecasts = run_all_forecasts(horizon=30, limit=10)
    print(f"      Done in {time.time()-t0:.1f}s")
    print()

    # Step 3: Run M5 Walmart competition benchmark (Company Instruction #3)
    print("[3/5] Precomputing M5 Walmart competition benchmarks (Instruction #3)...")
    t0 = time.time()
    try:
        from models.m5_forecaster import precompute_m5_benchmarks
        precompute_m5_benchmarks(per_cat=5)
        print(f"      M5 benchmarks ready in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"      M5 benchmarks skipped/error: {e}")
    print()

    # Step 4: Calculate stockout risk
    print("[4/5] Calculating stockout risk...")
    t0 = time.time()
    from models.stockout_risk import calculate_stockout_risk
    risk_df = calculate_stockout_risk(lead_time_days=14)
    print(f"      Done in {time.time()-t0:.1f}s")
    print()

    # Step 5: Generate alerts & Export CSVs
    print("[5/5] Generating alerts & exporting CSVs for IBM MQ replay streaming...")
    t0 = time.time()
    from alerts.alert_system import generate_alerts
    n_alerts = generate_alerts(stockout_df=risk_df)
    print(f"      {n_alerts} alerts generated in {time.time()-t0:.1f}s")
    try:
        from pipeline.mq_publisher import export_raw_csvs
        export_raw_csvs()
        print("      Raw CSV exports ready in data/raw/")
    except Exception as e:
        print(f"      CSV export skipped: {e}")
    print()

    print("=" * 60)
    print("  SETUP COMPLETE! Run the dashboard with:")
    print("  streamlit run dashboard/app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()

"""
IBM Supply Chain Intelligence Platform
setup_db2.py

Loads clean IBM supply chain datasets (DataCo + Olist) into IBM Db2 (or SQLite).
Follows the IBM company guide pattern for chunked CSV loading.

Usage:
    python setup_db2.py
"""
import os, sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    mode = os.getenv("DASHBOARD_MODE", "local").lower()
    print("=" * 60)
    print("  IBM SUPPLY CHAIN  -  Db2 Data Load")
    print("=" * 60)
    print(f"\nMode: {mode.upper()}")

    if mode != "cloud":
        print("\nTo load into IBM Db2:")
        print("  1. Set DASHBOARD_MODE=cloud in your .env")
        print("  2. Fill in DB2_HOST, DB2_DATABASE, DB2_USER, DB2_PASSWORD")
        print("  3. Re-run this script.\n")
        print("Running local SQLite setup instead...\n")

    # Step 1: Initialize DB
    from database.db_manager import init_db
    init_db()

    # Step 2: Ingest clean IBM data (DataCo + Olist)
    from data.ingest_real_data import main as ingest_real_data_main
    print("\n[1/4] Ingesting clean IBM datasets...")
    ingest_real_data_main()

    # Step 3: Export raw CSVs for MQ replay
    print("\n[2/4] Exporting raw CSVs for MQ streaming...")
    from pipeline.mq_publisher import export_raw_csvs
    export_raw_csvs()

    # Step 4: If cloud mode, load CSVs into Db2 using company guide pattern
    if mode == "cloud":
        print("\n[3/4] Loading data into IBM Db2...")
        from database.db_manager import get_engine
        engine = get_engine()
        raw_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
        table_map = {
            "products.csv":       "products",
            "orders.csv":         "orders",
            "inventory.csv":      "inventory",
            "shipments.csv":      "shipments",
            "demand.csv":         "demand_history",
            "suppliers.csv":      "suppliers",
        }
        schema = os.getenv("DB2_SCHEMA", None)
        for fname, table in table_map.items():
            fpath = os.path.join(raw_dir, fname)
            if not os.path.exists(fpath):
                print(f"  SKIP {fname} (not found)")
                continue
            df = pd.read_csv(fpath)
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            df.to_sql(table, engine,
                      if_exists="replace", index=False,
                      chunksize=5000, schema=schema)
            print(f"  Loaded {len(df):,} rows -> {schema or ''}.{table}")
    else:
        print("\n[3/4] Skipping Db2 load (local mode).")

    # Step 5: Run models and alerts
    print("\n[4/4] Running forecasts, M5 benchmarks, risk analysis, and alerts...")
    from models.demand_forecast import run_all_forecasts
    run_all_forecasts(horizon=30, limit=10)
    try:
        from models.m5_forecaster import precompute_m5_benchmarks
        precompute_m5_benchmarks(per_cat=5)
    except Exception as e:
        print(f"  M5 benchmark precomputation skipped: {e}")
    from models.stockout_risk import calculate_stockout_risk
    stockout_df = calculate_stockout_risk()
    from alerts.alert_system import generate_alerts
    generate_alerts(stockout_df=stockout_df)

    print("\n" + "=" * 60)
    print("  SETUP COMPLETE! Launch dashboard:")
    print("  streamlit run dashboard/app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()

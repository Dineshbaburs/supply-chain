"""
Supply Chain Setup Script
Initializes the database, simulates data, runs forecasts, and generates alerts.
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

    # Step 1: Simulate data
    print("[1/4] Running data simulation...")
    t0 = time.time()
    from data.data_simulator import run_simulation
    demand_df, orders_df, inventory_df = run_simulation()
    print(f"      Done in {time.time()-t0:.1f}s")
    print()

    # Step 2: Run demand forecasts (limited for speed)
    print("[2/4] Running demand forecasts (sample products)...")
    t0 = time.time()
    from models.demand_forecast import run_all_forecasts
    forecasts = run_all_forecasts(horizon=30, limit=10)
    print(f"      Done in {time.time()-t0:.1f}s")
    print()

    # Step 3: Calculate stockout risk
    print("[3/4] Calculating stockout risk...")
    t0 = time.time()
    from models.stockout_risk import calculate_stockout_risk
    risk_df = calculate_stockout_risk(lead_time_days=14)
    print(f"      Done in {time.time()-t0:.1f}s")
    print()

    # Step 4: Generate alerts
    print("[4/4] Generating alerts...")
    t0 = time.time()
    from alerts.alert_system import generate_alerts
    n_alerts = generate_alerts(stockout_df=risk_df)
    print(f"      {n_alerts} alerts generated in {time.time()-t0:.1f}s")
    # Step 5: Export raw CSVs for IBM MQ replay streaming
    print("[5/5] Exporting CSVs for IBM MQ streaming replay...")
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

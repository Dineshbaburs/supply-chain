"""
IBM Supply Chain Intelligence Platform
models/m5_forecaster.py

Implementation of Company Instruction #3:
"3. Use M5 to train and test the demand forecast (a baseline such as seasonal-naive first, then a better model)."

Evaluates Seasonal-Naive baseline (lag-7 persistence) vs. Ridge Regression ML
with calendar events, SNAP assistance indicators, and Fourier seasonality on an 85/15 chronological split.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database.db_manager import execute_query, bulk_insert, execute_write

M5_DIR = os.path.join(BASE_DIR, "Given_dataset", "M5")
CAL_PATH = os.path.join(M5_DIR, "cleaned_calendar.csv")
SALES_PATH = os.path.join(M5_DIR, "cleaned_sales_train_validation.csv")

# Cache calendar in memory
_CAL_DF = None

def get_calendar():
    global _CAL_DF
    if _CAL_DF is None:
        if os.path.exists(CAL_PATH):
            cal = pd.read_csv(CAL_PATH)
            cal['date'] = pd.to_datetime(cal['date'])
            _CAL_DF = cal
        else:
            raise FileNotFoundError(f"M5 Calendar file not found at: {CAL_PATH}")
    return _CAL_DF


def get_available_m5_items(per_cat=5):
    """Return representative M5 items evenly distributed across FOODS, HOBBIES, and HOUSEHOLD."""
    if not os.path.exists(SALES_PATH):
        return []
    
    first_rows = pd.read_csv(SALES_PATH, nrows=3500,
                             usecols=['id', 'item_id', 'dept_id', 'cat_id', 'store_id', 'state_id'])
    selected = []
    for cat in ['FOODS', 'HOBBIES', 'HOUSEHOLD']:
        cat_df = first_rows[first_rows['cat_id'] == cat]
        selected.extend(cat_df.head(per_cat).to_dict(orient='records'))
    return selected


def load_m5_series(item_id, store_id='CA_1'):
    """Load daily sales time series for a single M5 item-store combination."""
    if not os.path.exists(SALES_PATH):
        return None, None
    
    cal = get_calendar()
    d_to_date = dict(zip(cal['d'], cal['date']))
    d_to_event = dict(zip(cal['d'], (cal['event_name_1'] != 'NoEvent').astype(int)))
    
    state = store_id.split('_')[0]
    snap_col = f'snap_{state}' if f'snap_{state}' in cal.columns else 'snap_CA'
    d_to_snap = dict(zip(cal['d'], cal[snap_col]))

    # Search item row in chunks
    matched_row = None
    for chunk in pd.read_csv(SALES_PATH, chunksize=5000):
        m = chunk[(chunk['item_id'] == item_id) & (chunk['store_id'] == store_id)]
        if not m.empty:
            matched_row = m.iloc[0]
            break

    if matched_row is None:
        return None, None

    meta = {
        'id': matched_row['id'],
        'item_id': matched_row['item_id'],
        'dept_id': matched_row['dept_id'],
        'cat_id': matched_row['cat_id'],
        'store_id': matched_row['store_id'],
        'state_id': matched_row['state_id']
    }

    d_cols = [c for c in matched_row.index if c.startswith('d_')]
    df = pd.DataFrame({
        'd': d_cols,
        'demand': matched_row[d_cols].values.astype(int)
    })
    df['date'] = df['d'].map(d_to_date)
    df['has_event'] = df['d'].map(d_to_event)
    df['snap'] = df['d'].map(d_to_snap)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df, meta


def create_m5_features(df):
    """Engineer calendar, Fourier, lag, and rolling features."""
    df = df.copy()
    df['day_of_year'] = df['date'].dt.dayofyear
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Fourier Seasonality (Annual and Weekly cycles)
    df['sin_doy'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
    df['cos_doy'] = np.cos(2 * np.pi * df['day_of_year'] / 365)
    df['sin_dow'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['cos_dow'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

    # Lags (avoiding data leakage: minimum lag 7)
    for lag in [7, 14, 21, 28]:
        df[f'lag_{lag}'] = df['demand'].shift(lag)

    # Rolling statistics over past observed sales
    df['rolling_7_mean'] = df['demand'].shift(7).rolling(7).mean()
    df['rolling_14_mean'] = df['demand'].shift(7).rolling(14).mean()
    df['rolling_28_mean'] = df['demand'].shift(7).rolling(28).mean()
    df['rolling_7_std'] = df['demand'].shift(7).rolling(7).std().fillna(0)

    return df


def train_and_evaluate_m5(item_id, store_id='CA_1', horizon=28):
    """
    Train and evaluate M5 models:
    1. Seasonal-Naive Baseline (Lag-7 persistence): y_hat_t = y_{t-7}
    2. Ridge Regression ML Model (L2 regularized with calendar events and lags)
    Evaluated on holdout test set (85% train / 15% test).
    """
    df, meta = load_m5_series(item_id, store_id)
    if df is None or len(df) < 100:
        return None

    df_feat = create_m5_features(df).dropna().reset_index(drop=True)
    feature_cols = [
        'day_of_week', 'month', 'is_weekend', 'has_event', 'snap',
        'sin_doy', 'cos_doy', 'sin_dow', 'cos_dow',
        'lag_7', 'lag_14', 'lag_21', 'lag_28',
        'rolling_7_mean', 'rolling_14_mean', 'rolling_28_mean', 'rolling_7_std'
    ]

    split_idx = int(len(df_feat) * 0.85)
    train = df_feat.iloc[:split_idx]
    test = df_feat.iloc[split_idx:].copy()

    X_train, y_train = train[feature_cols], train['demand']
    X_test, y_test = test[feature_cols], test['demand']

    # Model 1: Seasonal-Naive Baseline (Lag-7 Persistence)
    # y_hat_t = y_{t-7}
    y_naive = test['lag_7'].values
    baseline_mae = float(mean_absolute_error(y_test, y_naive))
    baseline_rmse = float(np.sqrt(mean_squared_error(y_test, y_naive)))

    # Model 2: Ridge Regression
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('regressor', Ridge(alpha=10.0))
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    preds = np.clip(preds, 0, None)  # Demand cannot be negative

    model_mae = float(mean_absolute_error(y_test, preds))
    model_rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    improvement_pct = round(float((baseline_rmse - model_rmse) / max(baseline_rmse, 1e-6) * 100), 1)

    # Attach predictions to test dataframe for visualization
    test['predicted_demand'] = np.round(preds, 2)
    test['baseline_demand'] = np.round(y_naive, 2)
    residuals_std = float(np.std(y_test - preds))
    test['lower_bound'] = np.maximum(0, np.round(preds - 1.96 * residuals_std, 2))
    test['upper_bound'] = np.round(preds + 1.96 * residuals_std, 2)

    # Future 28-day projection
    last_date = test['date'].max()
    future_dates = pd.date_range(last_date + timedelta(days=1), periods=horizon, freq='D')
    
    cal = get_calendar()
    future_cal = cal[cal['date'].isin(future_dates)]
    event_map = dict(zip(future_cal['date'], (future_cal['event_name_1'] != 'NoEvent').astype(int)))
    state = store_id.split('_')[0]
    snap_col = f'snap_{state}' if f'snap_{state}' in cal.columns else 'snap_CA'
    snap_map = dict(zip(future_cal['date'], future_cal[snap_col]))

    future_rows = []
    # Use recursive autoregressive generation for future 28 days
    hist_series = list(df_feat['demand'].values)
    for dt in future_dates:
        dow = dt.dayofweek
        m = dt.month
        doy = dt.dayofyear
        has_ev = event_map.get(dt, 0)
        snp = snap_map.get(dt, 0)
        row = {
            'date': dt,
            'day_of_week': dow,
            'month': m,
            'is_weekend': int(dow >= 5),
            'has_event': has_ev,
            'snap': snp,
            'sin_doy': np.sin(2 * np.pi * doy / 365),
            'cos_doy': np.cos(2 * np.pi * doy / 365),
            'sin_dow': np.sin(2 * np.pi * dow / 7),
            'cos_dow': np.cos(2 * np.pi * dow / 7),
            'lag_7': hist_series[-7] if len(hist_series) >= 7 else 0,
            'lag_14': hist_series[-14] if len(hist_series) >= 14 else 0,
            'lag_21': hist_series[-21] if len(hist_series) >= 21 else 0,
            'lag_28': hist_series[-28] if len(hist_series) >= 28 else 0,
            'rolling_7_mean': np.mean(hist_series[-7:]) if len(hist_series) >= 7 else 0,
            'rolling_14_mean': np.mean(hist_series[-14:]) if len(hist_series) >= 14 else 0,
            'rolling_28_mean': np.mean(hist_series[-28:]) if len(hist_series) >= 28 else 0,
            'rolling_7_std': np.std(hist_series[-7:]) if len(hist_series) >= 7 else 0,
        }
        x_row = pd.DataFrame([row])[feature_cols]
        pred_val = float(np.clip(pipeline.predict(x_row)[0], 0, None))
        hist_series.append(pred_val)
        row['predicted_demand'] = round(pred_val, 2)
        row['baseline_demand'] = round(float(row['lag_7']), 2)
        row['lower_bound'] = round(max(0, pred_val - 1.96 * residuals_std), 2)
        row['upper_bound'] = round(pred_val + 1.96 * residuals_std, 2)
        future_rows.append(row)

    future_df = pd.DataFrame(future_rows)

    metrics = {
        'baseline_mae': round(baseline_mae, 3),
        'baseline_rmse': round(baseline_rmse, 3),
        'model_mae': round(model_mae, 3),
        'model_rmse': round(model_rmse, 3),
        'improvement_pct': improvement_pct,
        'test_days': len(test),
        'horizon_days': horizon
    }

    return {
        'meta': meta,
        'test_df': test[['date', 'demand', 'predicted_demand', 'baseline_demand', 'lower_bound', 'upper_bound']],
        'future_df': future_df[['date', 'predicted_demand', 'baseline_demand', 'lower_bound', 'upper_bound']],
        'metrics': metrics
    }


def precompute_m5_benchmarks(per_cat=5):
    """Precompute and store benchmark M5 forecasts into SQLite table m5_forecasts."""
    print("=" * 60)
    print("  M5 WALMART FORECAST BENCHMARK GENERATION (Instruction #3)")
    print("=" * 60)
    items = get_available_m5_items(per_cat=per_cat)
    print(f"Selected {len(items)} representative M5 items across FOODS, HOBBIES, and HOUSEHOLD.")
    
    execute_write("DELETE FROM m5_forecasts", ())
    all_records = []
    
    for i, it in enumerate(items):
        item_id = it['item_id']
        store_id = it['store_id']
        print(f"[{i+1}/{len(items)}] Training M5 forecast for {item_id} at {store_id} ({it['cat_id']})...")
        res = train_and_evaluate_m5(item_id, store_id, horizon=28)
        if res is None:
            continue
        
        meta = res['meta']
        # Combine test set (actual vs predicted) and future set
        test_df = res['test_df'].tail(60).copy()
        for _, row in test_df.iterrows():
            all_records.append({
                'item_id': meta['item_id'],
                'cat_id': meta['cat_id'],
                'dept_id': meta['dept_id'],
                'store_id': meta['store_id'],
                'state_id': meta['state_id'],
                'forecast_date': row['date'].strftime('%Y-%m-%d'),
                'actual_demand': row['demand'],
                'predicted_demand': row['predicted_demand'],
                'baseline_demand': row['baseline_demand'],
                'lower_bound': row['lower_bound'],
                'upper_bound': row['upper_bound'],
                'model_type': 'ridge_regression'
            })
        
        fut_df = res['future_df'].copy()
        for _, row in fut_df.iterrows():
            all_records.append({
                'item_id': meta['item_id'],
                'cat_id': meta['cat_id'],
                'dept_id': meta['dept_id'],
                'store_id': meta['store_id'],
                'state_id': meta['state_id'],
                'forecast_date': row['date'].strftime('%Y-%m-%d'),
                'actual_demand': None,
                'predicted_demand': row['predicted_demand'],
                'baseline_demand': row['baseline_demand'],
                'lower_bound': row['lower_bound'],
                'upper_bound': row['upper_bound'],
                'model_type': 'ridge_regression'
            })

    if all_records:
        df_save = pd.DataFrame(all_records)
        bulk_insert(df_save, 'm5_forecasts', if_exists='append')
        print(f"Saved {len(df_save):,} M5 benchmark forecast records to database table m5_forecasts.")
    print("M5 Benchmark generation complete.")


if __name__ == "__main__":
    precompute_m5_benchmarks(per_cat=5)

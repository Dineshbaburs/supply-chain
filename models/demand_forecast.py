import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error
from datetime import datetime, timedelta
import os
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_query, bulk_insert, execute_write

def create_features(df, date_col='date'):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df['day_of_year'] = df[date_col].dt.dayofyear
    df['day_of_week'] = df[date_col].dt.dayofweek
    df['month'] = df[date_col].dt.month
    df['quarter'] = df[date_col].dt.quarter
    df['week_of_year'] = df[date_col].dt.isocalendar().week.astype(int)
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['sin_doy'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
    df['cos_doy'] = np.cos(2 * np.pi * df['day_of_year'] / 365)
    df['sin_dow'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['cos_dow'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['t'] = (df[date_col] - df[date_col].min()).dt.days
    return df

def add_lag_features(df, target_col='demand', lags=[7, 14, 21, 28]):
    df = df.sort_values('date').copy()
    for lag in lags:
        df[f'lag_{lag}'] = df[target_col].shift(lag)
    df['rolling_7_mean'] = df[target_col].shift(1).rolling(7).mean()
    df['rolling_14_mean'] = df[target_col].shift(1).rolling(14).mean()
    df['rolling_28_mean'] = df[target_col].shift(1).rolling(28).mean()
    df['rolling_7_std'] = df[target_col].shift(1).rolling(7).std()
    return df

def train_forecast_model(product_id, warehouse_id, horizon=30):
    query = """
        SELECT date, demand FROM demand_history
        WHERE product_id = ? AND warehouse_id = ?
        ORDER BY date
    """
    df = execute_query(query, params=(product_id, warehouse_id))
    if df.empty or len(df) < 60:
        return None, None, None
    df = create_features(df)
    df = add_lag_features(df)
    df = df.dropna()
    feature_cols = ['day_of_year', 'day_of_week', 'month', 'quarter', 'week_of_year',
                    'is_weekend', 'sin_doy', 'cos_doy', 'sin_dow', 'cos_dow', 't',
                    'lag_7', 'lag_14', 'lag_21', 'lag_28',
                    'rolling_7_mean', 'rolling_14_mean', 'rolling_28_mean', 'rolling_7_std']
    X = df[feature_cols]
    y = df['demand']
    split = int(len(df) * 0.85)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('regressor', Ridge(alpha=1.0))
    ])
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    return model, df, {'mae': mae, 'rmse': rmse, 'feature_cols': feature_cols}

def generate_future_dates(last_date, horizon=30):
    return pd.date_range(pd.to_datetime(last_date) + timedelta(days=1), periods=horizon, freq='D')

def forecast_product_warehouse(product_id, warehouse_id, horizon=30):
    model, df, metrics = train_forecast_model(product_id, warehouse_id, horizon)
    if model is None:
        return None
    last_row = df.sort_values('date').tail(1).iloc[0]
    last_date = pd.to_datetime(last_row['date'])
    future_dates = generate_future_dates(last_date, horizon)
    future_df = pd.DataFrame({'date': future_dates})
    future_df = create_features(future_df)
    future_df['t'] = (future_df['date'] - df['date'].min()).dt.days
    last_demand_vals = df.sort_values('date')['demand'].values
    n = len(last_demand_vals)
    for i, row_idx in enumerate(future_df.index):
        for lag in [7, 14, 21, 28]:
            hist_idx = n - lag + i
            # clamp to valid range
            hist_idx = max(0, min(hist_idx, n - 1))
            future_df.loc[row_idx, f'lag_{lag}'] = last_demand_vals[hist_idx]
        future_df.loc[row_idx, 'rolling_7_mean'] = float(np.mean(last_demand_vals[max(0, n-7):]))
        future_df.loc[row_idx, 'rolling_14_mean'] = float(np.mean(last_demand_vals[max(0, n-14):]))
        future_df.loc[row_idx, 'rolling_28_mean'] = float(np.mean(last_demand_vals[max(0, n-28):]))
        future_df.loc[row_idx, 'rolling_7_std'] = float(np.std(last_demand_vals[max(0, n-7):]) + 1e-6)
    feature_cols = metrics['feature_cols']
    future_df_clean = future_df[feature_cols].bfill().ffill().fillna(0)
    predictions = model.predict(future_df_clean)
    predictions = np.maximum(predictions, 0)
    std = metrics['mae'] * 0.5
    results = []
    for i, (date, pred) in enumerate(zip(future_dates, predictions)):
        results.append({
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'forecast_date': date.date(),
            'predicted_demand': round(float(pred), 2),
            'lower_bound': round(max(0, float(pred) - 1.96 * std), 2),
            'upper_bound': round(float(pred) + 1.96 * std, 2),
            'created_at': datetime.now().isoformat()
        })
    return pd.DataFrame(results)

def run_all_forecasts(horizon=30, limit=None):
    print('Running demand forecasts...')
    products_q = "SELECT DISTINCT product_id FROM demand_history"
    warehouses_q = "SELECT DISTINCT warehouse_id FROM demand_history"
    products = execute_query(products_q)['product_id'].tolist()
    warehouses = execute_query(warehouses_q)['warehouse_id'].tolist()
    if limit:
        products = products[:limit]
    all_forecasts = []
    total = len(products) * len(warehouses)
    count = 0
    for pid in products:
        for wid in warehouses:
            count += 1
            if count % 20 == 0:
                print(f'  Forecasting {count}/{total}...')
            result = forecast_product_warehouse(pid, wid, horizon)
            if result is not None:
                all_forecasts.append(result)
    if all_forecasts:
        all_df = pd.concat(all_forecasts, ignore_index=True)
        execute_write("DELETE FROM forecasts", ())
        bulk_insert(all_df, 'forecasts', if_exists='append')
        print(f'  -> {len(all_df):,} forecast records saved')
        return all_df
    return pd.DataFrame()

def get_demand_forecast(product_id, warehouse_id):
    q = """
        SELECT forecast_date, predicted_demand, lower_bound, upper_bound
        FROM forecasts
        WHERE product_id = ? AND warehouse_id = ?
        ORDER BY forecast_date
    """
    return execute_query(q, params=(product_id, warehouse_id))

if __name__ == '__main__':
    run_all_forecasts(horizon=30, limit=5)

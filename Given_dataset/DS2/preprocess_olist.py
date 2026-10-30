from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "raw"
OUT = BASE / "processed"
OUT.mkdir(exist_ok=True)

def clean_text(df):
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        df[col] = df[col].replace("", pd.NA)
    return df

# Orders: required for lead-time/delivery analysis.
orders = pd.read_csv(RAW / "olist_orders_dataset.csv")
orders = orders[
    [
        "order_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
].copy()

for col in [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]:
    orders[col] = pd.to_datetime(orders[col], errors="coerce")

orders = clean_text(orders).drop_duplicates()

# Order items: required to connect orders to sellers and measure order value.
items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
items = items[
    [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ]
].copy()

items["shipping_limit_date"] = pd.to_datetime(
    items["shipping_limit_date"], errors="coerce"
)
items["price"] = pd.to_numeric(items["price"], errors="coerce")
items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce")
items["order_item_id"] = pd.to_numeric(
    items["order_item_id"], errors="coerce"
).astype("Int64")
items = clean_text(items).drop_duplicates()

# Sellers: required for seller performance analysis.
sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
sellers = sellers[
    [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ]
].copy()

sellers = clean_text(sellers)
sellers["seller_zip_code_prefix"] = (
    pd.to_numeric(sellers["seller_zip_code_prefix"], errors="coerce")
    .astype("Int64")
    .astype("string")
    .str.zfill(5)
)
sellers = sellers.drop_duplicates()

orders.to_csv(OUT / "orders_processed.csv", index=False)
items.to_csv(OUT / "order_items_processed.csv", index=False)
sellers.to_csv(OUT / "sellers_processed.csv", index=False)

print("DS2 Olist preprocessing completed.")

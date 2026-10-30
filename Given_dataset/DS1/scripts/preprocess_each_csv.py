import pandas as pd
import os

# ============================================================
# FILE PATHS
# ============================================================

orders_file = "orders_clean.csv"
products_file = "products_clean.csv"
shipments_file = "shipments_clean.csv"

output_folder = "processed"

# Create processed folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)


# ============================================================
# 1. LOAD FILES
# ============================================================

orders = pd.read_csv(orders_file)
products = pd.read_csv(products_file)
shipments = pd.read_csv(shipments_file)

print("Files loaded successfully.")

print("\nOriginal shapes:")
print("Orders:", orders.shape)
print("Products:", products.shape)
print("Shipments:", shipments.shape)


# ============================================================
# 2. REMOVE EXACT DUPLICATES
# ============================================================

print("\n--- DUPLICATE CHECK ---")

print("Orders duplicates:", orders.duplicated().sum())
print("Products duplicates:", products.duplicated().sum())
print("Shipments duplicates:", shipments.duplicated().sum())

orders = orders.drop_duplicates()
products = products.drop_duplicates()
shipments = shipments.drop_duplicates()


# ============================================================
# 3. STANDARDIZE COLUMN NAMES
# ============================================================

orders.columns = orders.columns.str.strip().str.lower()

products.columns = products.columns.str.strip().str.lower()

shipments.columns = shipments.columns.str.strip().str.lower()


# ============================================================
# 4. HANDLE MISSING VALUES - ORDERS
# ============================================================

print("\n--- MISSING VALUES: ORDERS ---")
print(orders.isnull().sum())

# Essential fields
orders = orders.dropna(
    subset=[
        "order_id",
        "product_id",
        "order_date"
    ]
)

# Categorical fields
order_categories = [
    "order_status",
    "region",
    "country",
    "state",
    "city"
]

for col in order_categories:
    if col in orders.columns:
        orders[col] = orders[col].fillna("Unknown")


# Quantity
orders["quantity"] = pd.to_numeric(
    orders["quantity"],
    errors="coerce"
)

orders = orders.dropna(subset=["quantity"])

# Quantity should be positive
orders = orders[orders["quantity"] > 0]


# ============================================================
# 5. HANDLE MISSING VALUES - PRODUCTS
# ============================================================

print("\n--- MISSING VALUES: PRODUCTS ---")
print(products.isnull().sum())

# Product ID is essential
products = products.dropna(
    subset=["product_id"]
)

# Text fields
products["product_name"] = (
    products["product_name"]
    .fillna("Unknown")
)

products["category"] = (
    products["category"]
    .fillna("Unknown")
)


# Product price
products["unit_price"] = pd.to_numeric(
    products["unit_price"],
    errors="coerce"
)

# Use median only where price is missing
median_price = products["unit_price"].median()

products["unit_price"] = (
    products["unit_price"]
    .fillna(median_price)
)

# Price cannot be negative
products = products[
    products["unit_price"] >= 0
]


# ============================================================
# 6. HANDLE MISSING VALUES - SHIPMENTS
# ============================================================

print("\n--- MISSING VALUES: SHIPMENTS ---")
print(shipments.isnull().sum())

# Order ID is required to link shipment to order
shipments = shipments.dropna(
    subset=["order_id"]
)

# Categorical fields
shipment_categories = [
    "shipping_mode",
    "delivery_status",
    "region",
    "country",
    "state"
]

for col in shipment_categories:
    if col in shipments.columns:
        shipments[col] = shipments[col].fillna("Unknown")


# ============================================================
# 7. CONVERT DATES
# ============================================================

orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    errors="coerce"
)

shipments["shipping_date"] = pd.to_datetime(
    shipments["shipping_date"],
    errors="coerce"
)

# Remove records with invalid/missing dates
orders = orders.dropna(
    subset=["order_date"]
)

shipments = shipments.dropna(
    subset=["shipping_date"]
)


# ============================================================
# 8. CONVERT NUMERIC SHIPMENT COLUMNS
# ============================================================

numeric_columns = [
    "actual_days",
    "scheduled_days",
    "late_delivery_risk"
]

for col in numeric_columns:
    shipments[col] = pd.to_numeric(
        shipments[col],
        errors="coerce"
    )


# ============================================================
# 9. HANDLE MISSING SHIPPING VALUES
# ============================================================

shipments = shipments.dropna(
    subset=["actual_days", "scheduled_days"]
)
# Late delivery risk
shipments["late_delivery_risk"] = (
    shipments["late_delivery_risk"]
    .fillna(0)
    .astype(int)
)


# ============================================================
# 10. REMOVE INVALID SHIPPING VALUES
# ============================================================

shipments = shipments[
    (shipments["actual_days"] >= 0) &
    (shipments["scheduled_days"] >= 0)
]

shipments = shipments[
    shipments["late_delivery_risk"].isin([0, 1])
]


# ============================================================
# 11. STANDARDIZE TEXT
# ============================================================

def clean_text(df, columns):

    for col in columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
            )

    return df


orders = clean_text(
    orders,
    [
        "order_status",
        "region",
        "country",
        "state",
        "city"
    ]
)

products = clean_text(
    products,
    [
        "product_name",
        "category"
    ]
)

shipments = clean_text(
    shipments,
    [
        "shipping_mode",
        "delivery_status",
        "region",
        "country",
        "state"
    ]
)


# ============================================================
# 12. CALCULATE DELAY
# ============================================================

shipments["delay_days"] = (
    shipments["actual_days"]
    - shipments["scheduled_days"]
)


# ============================================================
# 13. CREATE DELAY CATEGORY
# ============================================================

def classify_delay(days):

    if days > 0:
        return "Delayed"

    elif days == 0:
        return "On Time"

    else:
        return "Early"


shipments["delay_category"] = (
    shipments["delay_days"]
    .apply(classify_delay)
)


# ============================================================
# 14. CHECK ORDER IDS
# ============================================================

# Keep only shipments whose order exists
valid_orders = set(orders["order_id"])

shipments = shipments[
    shipments["order_id"].isin(valid_orders)
]


# ============================================================
# 15. FINAL DUPLICATE REMOVAL
# ============================================================

orders = orders.drop_duplicates()

products = products.drop_duplicates(
    subset=["product_id"]
)

shipments = shipments.drop_duplicates()


# ============================================================
# 16. FINAL VALIDATION
# ============================================================

print("\n==============================")
print("FINAL VALIDATION")
print("==============================")

print("\nOrders:")
print("Rows:", len(orders))
print("Missing values:")
print(orders.isnull().sum())

print("\nProducts:")
print("Rows:", len(products))
print("Missing values:")
print(products.isnull().sum())

print("\nShipments:")
print("Rows:", len(shipments))
print("Missing values:")
print(shipments.isnull().sum())


# ============================================================
# 17. DELAY SUMMARY
# ============================================================

print("\n==============================")
print("DELAY SUMMARY")
print("==============================")

print(
    shipments["delay_category"]
    .value_counts()
)

print("\nAverage delay:",
      round(shipments["delay_days"].mean(), 2),
      "days")


# ============================================================
# 18. SAVE PROCESSED FILES
# ============================================================

orders.to_csv(
    os.path.join(
        output_folder,
        "orders_processed.csv"
    ),
    index=False
)

products.to_csv(
    os.path.join(
        output_folder,
        "products_processed.csv"
    ),
    index=False
)

shipments.to_csv(
    os.path.join(
        output_folder,
        "shipments_processed.csv"
    ),
    index=False
)


# ============================================================
# 19. FINAL MESSAGE
# ============================================================

print("\n==============================")
print("PREPROCESSING COMPLETE")
print("==============================")

print("\nProcessed files created:")
print("processed/orders_processed.csv")
print("processed/products_processed.csv")
print("processed/shipments_processed.csv")
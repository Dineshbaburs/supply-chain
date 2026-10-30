import pandas as pd

# =========================
# 1. Load DataCo dataset
# =========================

file_path = "DataCoSupplyChainDataset.csv"

df = pd.read_csv(file_path, encoding="latin1")

print("Original shape:", df.shape)


# =========================
# 2. Columns required
# =========================

required_columns = [
    # Orders
    "Order Id",
    "Order Customer Id",
    "order date (DateOrders)",
    "Order Item Cardprod Id",
    "Order Item Quantity",
    "Order Status",
    "Order Region",
    "Order Country",
    "Order State",
    "Order City",

    # Products
    "Product Name",
    "Category Name",
    "Product Price",

    # Shipments
    "shipping date (DateOrders)",
    "Shipping Mode",
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Delivery Status",
    "Late_delivery_risk"
]


# =========================
# 3. Check columns
# =========================

missing = [col for col in required_columns if col not in df.columns]

if missing:
    print("Missing columns:")
    for col in missing:
        print(col)
else:
    print("All required columns found!")


# =========================
# 4. Extract required data
# =========================

data = df[required_columns].copy()


# =========================
# 5. Clean dates
# =========================

data["order date (DateOrders)"] = pd.to_datetime(
    data["order date (DateOrders)"],
    errors="coerce"
)

data["shipping date (DateOrders)"] = pd.to_datetime(
    data["shipping date (DateOrders)"],
    errors="coerce"
)


# =========================
# 6. Calculate delay
# =========================

data["delay_days"] = (
    data["Days for shipping (real)"]
    - data["Days for shipment (scheduled)"]
)


# =========================
# 7. Create Orders table
# =========================

orders = data[
    [
        "Order Id",
        "Order Customer Id",
        "order date (DateOrders)",
        "Order Item Cardprod Id",
        "Order Item Quantity",
        "Order Status",
        "Order Region",
        "Order Country",
        "Order State",
        "Order City"
    ]
].copy()

orders.columns = [
    "order_id",
    "customer_id",
    "order_date",
    "product_id",
    "quantity",
    "order_status",
    "region",
    "country",
    "state",
    "city"
]


# =========================
# 8. Create Shipments table
# =========================

shipments = data[
    [
        "Order Id",
        "shipping date (DateOrders)",
        "Shipping Mode",
        "Days for shipping (real)",
        "Days for shipment (scheduled)",
        "delay_days",
        "Delivery Status",
        "Late_delivery_risk",
        "Order Region",
        "Order Country",
        "Order State"
    ]
].copy()

shipments.columns = [
    "order_id",
    "shipping_date",
    "shipping_mode",
    "actual_days",
    "scheduled_days",
    "delay_days",
    "delivery_status",
    "late_delivery_risk",
    "region",
    "country",
    "state"
]

# Create shipment ID
shipments.insert(
    0,
    "shipment_id",
    ["SHIP" + str(i).zfill(6) for i in range(1, len(shipments) + 1)]
)


# =========================
# 9. Create Products table
# =========================

products = data[
    [
        "Order Item Cardprod Id",
        "Product Name",
        "Category Name",
        "Product Price"
    ]
].drop_duplicates().copy()

products.columns = [
    "product_id",
    "product_name",
    "category",
    "unit_price"
]


# =========================
# 10. Save CSV files
# =========================

orders.to_csv("orders_clean.csv", index=False)
shipments.to_csv("shipments_clean.csv", index=False)
products.to_csv("products_clean.csv", index=False)


# =========================
# 11. Display results
# =========================

print("\nFiles created successfully!")

print("\nOrders:")
print(orders.head())

print("\nShipments:")
print(shipments.head())

print("\nProducts:")
print(products.head())

print("\nFinal row counts:")
print("Orders:", len(orders))
print("Shipments:", len(shipments))
print("Products:", len(products))
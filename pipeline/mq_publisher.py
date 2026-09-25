"""
IBM Supply Chain Intelligence Platform
pipeline/mq_publisher.py

Replays static CSV datasets as live IBM MQ messages
(as specified in the IBM company guide).

Usage:
    python pipeline/mq_publisher.py --dataset orders --rate 2.0 --loop

Requires .env with MQ_* credentials.
Falls back to console print if MQ is unavailable (for local testing).
"""
import os, sys, json, time, argparse
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -- MQ Connection -------------------------------------------------------------
def get_mq_publisher():
    """
    Try to connect to IBM MQ. Returns a publish(msg) callable.
    Falls back to local console logging if MQ is not configured.
    """
    host    = os.getenv("MQ_HOST", "")
    port    = int(os.getenv("MQ_PORT", 1414))
    qmgr    = os.getenv("MQ_QMGR", "")
    channel = os.getenv("MQ_CHANNEL", "")
    user    = os.getenv("MQ_USER", "")
    pwd     = os.getenv("MQ_PASSWORD", "")
    queue   = os.getenv("MQ_QUEUE", "TEAM3.SUPPLYCHAIN")

    if not all([host, qmgr, channel]):
        print("[MQ] WARNING: MQ_HOST/MQ_QMGR/MQ_CHANNEL not set in .env")
        print("[MQ] Running in LOCAL mode  -  messages printed to console.")
        def _local_publish(msg):
            print(f"[LOCAL STREAM] {msg[:120]}")
        return _local_publish, None, None

    try:
        import pymqi
        cd = pymqi.CD()
        cd.ChannelName       = channel.encode()
        cd.ConnectionName    = f"{host}({port})".encode()
        cd.ChannelType       = pymqi.CMQC.MQCHT_CLNTCONN
        cd.TransportType     = pymqi.CMQC.MQXPT_TCP
        sco = pymqi.SCO()
        qmgr_obj = pymqi.connect(qmgr, cd, sco)
        q = pymqi.Queue(qmgr_obj, queue)
        print(f"[MQ] Connected to {host}:{port} / {qmgr} / Queue: {queue}")

        def _mq_publish(msg):
            md = pymqi.MD()
            q.put(msg.encode("utf-8"), md)

        return _mq_publish, q, qmgr_obj

    except ImportError:
        print("[MQ] pymqi not installed. Run: pip install pymqi")
        print("[MQ] Falling back to MQ REST API mode...")
        return _rest_publish_factory(host, port, qmgr, channel, queue, user, pwd), None, None
    except Exception as e:
        print(f"[MQ] Connection failed: {e}\n[MQ] Running in LOCAL mode.")
        def _local_publish(msg):
            print(f"[LOCAL STREAM] {msg[:120]}")
        return _local_publish, None, None


def _rest_publish_factory(host, port, qmgr, channel, queue, user, pwd):
    """IBM MQ REST Messaging API fallback."""
    import urllib.request, base64
    url = f"https://{host}:{port}/ibmmq/rest/v2/messaging/qmgr/{qmgr}/queue/{queue}/message"
    creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    headers = {
        "Content-Type": "text/plain",
        "Authorization": f"Basic {creds}",
        "ibm-mq-rest-csrf-token": ""
    }
    def _publish(msg):
        try:
            req = urllib.request.Request(url, msg.encode(), headers, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[MQ REST] Send failed: {e}")
    return _publish


# -- Replay engine (from IBM guide) --------------------------------------------
def replay(csv_path, publish, rate_hz=1.0, loop=False, dataset_name=""):
    """
    Replay a CSV file row-by-row as MQ messages at rate_hz rows/second.
    Implements the exact pattern from the IBM company guide.
    """
    print(f"[REPLAY] Loading {dataset_name} from {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Instruction 5: Sort strictly in chronological date order
    date_candidates = ["order_date", "date", "shipped_date", "last_updated"]
    for dc in date_candidates:
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc], errors="coerce")
            df = df.sort_values(dc, ascending=True).reset_index(drop=True)
            print(f"[REPLAY] Sorted chronologically by '{dc}' ({df[dc].min()} -> {df[dc].max()})")
            break

    total = len(df)
    print(f"[REPLAY] Streaming {total:,} rows at {rate_hz} Hz (loop={loop})")

    iteration = 0
    while True:
        iteration += 1
        for i, row in enumerate(df.to_dict(orient="records")):
            row["_stream_ts"]   = datetime.utcnow().isoformat()
            row["_dataset"]     = dataset_name
            row["_row_index"]   = i
            row["_iteration"]   = iteration
            publish(json.dumps(row, default=str))
            time.sleep(1.0 / rate_hz)
            if (i + 1) % 100 == 0:
                print(f"[REPLAY] {i+1:,}/{total:,} rows sent (iteration {iteration})")
        print(f"[REPLAY] Iteration {iteration} complete.")
        if not loop:
            break
    print("[REPLAY] Done.")


# -- Dataset paths -------------------------------------------------------------
DATASET_MAP = {
    "orders":    os.path.join(BASE_DIR, "data", "raw", "orders.csv"),
    "inventory": os.path.join(BASE_DIR, "data", "raw", "inventory.csv"),
    "shipments": os.path.join(BASE_DIR, "data", "raw", "shipments.csv"),
    "demand":    os.path.join(BASE_DIR, "data", "raw", "demand_history.csv"),
    "suppliers": os.path.join(BASE_DIR, "data", "raw", "suppliers.csv"),
}

def export_raw_csvs():
    """Export DB tables to raw CSVs so the MQ replay can stream them."""
    from database.db_manager import execute_query
    raw_dir = os.path.join(BASE_DIR, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    tables = {"orders":"orders","inventory":"inventory","shipments":"shipments",
              "demand":"demand_history","suppliers":"suppliers"}
    for name, table in tables.items():
        df = execute_query(f"SELECT * FROM {table}")
        path = os.path.join(raw_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"  Exported {len(df):,} rows -> {path}")
    print("Raw CSVs ready for MQ replay.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBM Supply Chain MQ Publisher")
    parser.add_argument("--dataset", default="orders",
                       choices=list(DATASET_MAP.keys()), help="Dataset to stream")
    parser.add_argument("--rate", type=float, default=1.0, help="Rows per second")
    parser.add_argument("--loop", action="store_true", help="Loop continuously")
    parser.add_argument("--export-raw", action="store_true", help="Export DB to raw CSVs first")
    args = parser.parse_args()

    if args.export_raw:
        export_raw_csvs()

    publish_fn, q_obj, qmgr_obj = get_mq_publisher()
    csv_path = DATASET_MAP[args.dataset]
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV not found: {csv_path}")
        print("[HINT] Run with --export-raw first to generate CSVs from the database.")
        sys.exit(1)

    try:
        replay(csv_path, publish_fn, rate_hz=args.rate, loop=args.loop, dataset_name=args.dataset)
    finally:
        if q_obj:
            q_obj.close()
        if qmgr_obj:
            qmgr_obj.disconnect()

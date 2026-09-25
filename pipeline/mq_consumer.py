"""
IBM Supply Chain Intelligence Platform
pipeline/mq_consumer.py

Reads messages from IBM MQ and stores them into Db2 (or SQLite in local mode).
Runs continuously — one thread per MQ queue.

Usage:
    python pipeline/mq_consumer.py
"""
import os, sys, json, time, threading
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import execute_write, bulk_insert, execute_query

# ── MQ Consumer ───────────────────────────────────────────────────────────────
class MQConsumer:
    """
    Reads JSON messages from IBM MQ and routes them to the correct DB table.
    Falls back to simulated in-memory queue if MQ is not configured.
    """

    TABLE_MAP = {
        "orders":    "orders",
        "inventory": "inventory",
        "shipments": "shipments",
        "demand":    "demand_history",
        "suppliers": "suppliers",
    }

    def __init__(self):
        self.host    = os.getenv("MQ_HOST", "")
        self.port    = int(os.getenv("MQ_PORT", 1414))
        self.qmgr    = os.getenv("MQ_QMGR", "")
        self.channel = os.getenv("MQ_CHANNEL", "")
        self.user    = os.getenv("MQ_USER", "")
        self.pwd     = os.getenv("MQ_PASSWORD", "")
        self.queue   = os.getenv("MQ_QUEUE", "TEAM3.SUPPLYCHAIN")
        self.running = False
        self._q_obj  = None
        self._qmgr_obj = None

    def connect(self):
        """Connect to IBM MQ. Returns True if connected, False for local mode."""
        if not all([self.host, self.qmgr, self.channel]):
            print("[MQ Consumer] MQ not configured — running in LOCAL simulation mode.")
            return False
        try:
            import pymqi
            cd = pymqi.CD()
            cd.ChannelName    = self.channel.encode()
            cd.ConnectionName = f"{self.host}({self.port})".encode()
            cd.ChannelType    = pymqi.CMQC.MQCHT_CLNTCONN
            cd.TransportType  = pymqi.CMQC.MQXPT_TCP
            sco = pymqi.SCO()
            self._qmgr_obj = pymqi.connect(self.qmgr, cd, sco)
            self._q_obj    = pymqi.Queue(self._qmgr_obj, self.queue)
            print(f"[MQ Consumer] Connected to {self.host}:{self.port} / {self.queue}")
            return True
        except Exception as e:
            print(f"[MQ Consumer] Connection failed: {e}. Local mode.")
            return False

    def process_message(self, raw_msg):
        """Parse a JSON MQ message and persist it to the database."""
        try:
            data = json.loads(raw_msg)
            dataset = data.pop("_dataset", "orders")
            data.pop("_stream_ts", None)
            data.pop("_row_index", None)
            data.pop("_iteration", None)
            table = self.TABLE_MAP.get(dataset, "orders")
            df = pd.DataFrame([data])
            bulk_insert(df, table, if_exists="append")
            return True
        except Exception as e:
            print(f"[MQ Consumer] Message processing error: {e}")
            return False

    def consume_mq(self, max_messages=None, timeout_ms=1000):
        """Read messages from IBM MQ in a loop."""
        import pymqi
        self.running = True
        count = 0
        print(f"[MQ Consumer] Listening on queue: {self.queue}")
        while self.running:
            try:
                gmo = pymqi.GMO()
                gmo.Options  = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
                gmo.WaitInterval = timeout_ms
                md  = pymqi.MD()
                msg = self._q_obj.get(None, md, gmo)
                self.process_message(msg.decode("utf-8"))
                count += 1
                if max_messages and count >= max_messages:
                    break
            except pymqi.MQMIError as e:
                if e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE:
                    continue
                print(f"[MQ Consumer] MQ error: {e}")
                break
        print(f"[MQ Consumer] Stopped. Processed {count} messages.")

    def consume_local_simulation(self, rate_hz=1.0, duration_seconds=60):
        """
        Local mode: Simulate reading from the pipeline data_pipeline.py ticker.
        Replays latest DB records as if they arrived via MQ.
        """
        from pipeline.data_pipeline import simulate_pipeline_tick
        self.running = True
        elapsed = 0
        interval = 1.0 / rate_hz
        print(f"[LOCAL Consumer] Simulating {rate_hz} msg/sec for {duration_seconds}s")
        while self.running and elapsed < duration_seconds:
            changes = simulate_pipeline_tick()
            for change in changes:
                print(f"  [MSG] {change}")
            time.sleep(interval)
            elapsed += interval
        print(f"[LOCAL Consumer] Simulation complete ({elapsed:.0f}s).")

    def start(self, simulation_duration=60):
        """Start the consumer (MQ or local simulation)."""
        connected = self.connect()
        if connected:
            t = threading.Thread(target=self.consume_mq, daemon=True)
            t.start()
            return t
        else:
            t = threading.Thread(
                target=self.consume_local_simulation,
                args=(float(os.getenv("STREAM_RATE_HZ", 1.0)), simulation_duration),
                daemon=True
            )
            t.start()
            return t

    def stop(self):
        self.running = False
        if self._q_obj:
            self._q_obj.close()
        if self._qmgr_obj:
            self._qmgr_obj.disconnect()


if __name__ == "__main__":
    consumer = MQConsumer()
    print("=== IBM Supply Chain MQ Consumer ===")
    print(f"Mode: {'IBM MQ' if os.getenv('MQ_HOST') else 'LOCAL simulation'}")
    thread = consumer.start(simulation_duration=300)  # Run for 5 minutes
    try:
        thread.join()
    except KeyboardInterrupt:
        consumer.stop()
        print("\n[Consumer] Stopped by user.")

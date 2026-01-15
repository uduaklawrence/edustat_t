import json
import pandas as pd
from redis_client import redis_client
from db_connection import create_connection

CACHE_KEY = "exam_candidates:v1"

print("🔄 Refreshing Redis exam dataset cache...")

engine = create_connection()

if engine is None:
    raise RuntimeError("❌ Could not connect to database.")

query = "SELECT * FROM exam_candidates"  # ⚠️ make sure this is the correct table

df = pd.read_sql(query, engine)

print("Rows fetched from DB:", len(df))

if df.empty:
    raise RuntimeError("❌ No data found in DB.")

# Precompute Age once here
if "DateOfBirth" in df.columns:
    df["DateOfBirth"] = pd.to_datetime(df["DateOfBirth"], errors="coerce")
    df["Age"] = pd.Timestamp.today().year - df["DateOfBirth"].dt.year

# ============================
# ✅ FORCE convert ALL Timestamp values
# ============================
def safe_json_value(x):
    if isinstance(x, (pd.Timestamp,)):
        return str(x)
    return x

df = df.applymap(safe_json_value)

records = df.to_dict(orient="records")

redis_client.set(CACHE_KEY, json.dumps(records))

print(f"✅ Cached {len(records):,} records into Redis under key '{CACHE_KEY}'")
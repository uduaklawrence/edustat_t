import json
import pandas as pd
from redis_client import redis_client

CACHE_KEY = "exam_candidates:v1"


def get_exam_dataset() -> pd.DataFrame:
    cached = redis_client.get(CACHE_KEY)

    if not cached:
        raise RuntimeError("❌ Exam dataset not found in Redis. Run admin cache refresh.")

    data = json.loads(cached)
    df = pd.DataFrame(data)

    # Precompute Age once
    if "DateOfBirth" in df.columns:
        dob = pd.to_datetime(df["DateOfBirth"], errors="coerce")
        df["Age"] = pd.Timestamp.today().year - dob.dt.year

    return df
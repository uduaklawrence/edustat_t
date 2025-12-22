import json
import hashlib
from redis_client import redis_client

CACHE_TTL = 60 * 60 * 6  # 6 hours


def make_cache_key(prefix: str, value: str) -> str:
    """
    Creates a safe Redis cache key.
    """
    raw_key = f"{prefix}:{value}"
    hashed = hashlib.md5(raw_key.encode()).hexdigest()
    return f"{prefix}:{hashed}"


def get_cached(key: str):
    """
    Get cached value from Redis.
    """
    value = redis_client.get(key)
    if value is None:
        return None
    return json.loads(value)


def set_cached(key: str, data, ttl: int = CACHE_TTL):
    """
    Save value to Redis with TTL.
    """
    redis_client.setex(key, ttl, json.dumps(data))


def delete_cached(key: str):
    """
    Delete a cached key (optional use later).
    """
    redis_client.delete(key)


def get_or_set_distinct_values(key, fetch_fn):
    """
    key: redis key string
    fetch_fn: function that fetches from DB if cache miss
    """
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    # Cache miss → fetch from DB
    data = fetch_fn()
    redis_client.setex(key, CACHE_TTL, json.dumps(data))
    return data
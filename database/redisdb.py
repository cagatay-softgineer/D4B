# database/redisdb.py

import redis
from contextlib import contextmanager
from config.settings import RedisSettings

_redis_settings = RedisSettings()  # Reads REDIS_* env vars if you import this module

@contextmanager
def get_connection():
    conn = redis.Redis(
        host=_redis_settings.host,
        port=_redis_settings.port,
        db=_redis_settings.db,
        password=_redis_settings.password if hasattr(_redis_settings, "password") else None,
        decode_responses=True,
    )
    try:
        yield conn
    finally:
        # Redis-py does not need explicit connection closing; but for consistency:
        try:
            conn.close()
        except Exception:
            pass

def check_database():
    try:
        with get_connection() as conn:
            # PING returns True if connection is healthy
            return conn.ping()
    except Exception as e:
        print(f"Redis health check failed: {e}")
        return False

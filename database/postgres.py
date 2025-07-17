# database/postgres.py

import psycopg2
from contextlib import contextmanager
from config.settings import PostgresSettings

_pg = PostgresSettings()   # only now reads POSTGRES_* if you import this module

@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=_pg.host,
        port=_pg.port,
        dbname=_pg.db,
        user=_pg.user,
        password=_pg.password
    )
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_connection_by_url():
    conn = psycopg2.connect(_pg.url)
    try:
        yield conn
    finally:
        conn.close()

def check_database():
    isUp = False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result =    cur.fetchone()
                isUp = True
                return result is not None and result[0] == 1
    except Exception as e:
        # Optional: log or print error
        print(f"Database health check failed: {e}")
        return False
    finally:
        return isUp
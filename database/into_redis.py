import json
import time
import sys
from decimal import Decimal
from datetime import datetime, date
from database.postgres import get_connection as Postgres
from database.redisdb import get_connection as Redis
from colorama import init, Fore, Style

init(autoreset=True)

SYSTEMS = [
    ('FUEL', 'teams'),
    ('CREW', 'team_members'),
    ('AIRLOCKS', 'users'),
    ('NAVIGATION', 'jobs'),
    ('CARGO', 'job_files'),
    ('TRACKING', 'job_status_history'),
    ('LOGS', 'activity_logs'),
    ('COMMS', 'notifications'),
    ('DIAGNOSTICS', 'job_metrics'),
    ('SECURITY', 'priority_distribution'),
    ('TELEMETRY', 'job_trends'),
    ('SETTINGS', 'settings'),
    ('LIFE_SUPPORT', 'system_health')
]

def to_redis_compatible(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    return str(value)

def get_primary_key(cur, table):
    """
    Returns the primary key column for the table, or first column as fallback.
    """
    cur.execute("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass AND i.indisprimary;
    """, (table,))
    result = cur.fetchone()
    if result:
        return result[0]
    # fallback to first column
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s ORDER BY ordinal_position LIMIT 1
    """, (table,))
    fallback = cur.fetchone()
    return fallback[0] if fallback else None

def get_table_columns(cur, table):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    return [row[0] for row in cur.fetchall()]

def clone_table(table, cur, redis_conn):
    columns = get_table_columns(cur, table)
    pk = get_primary_key(cur, table)
    if not columns or not pk:
        return (0, 0)  # no data
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    pipeline = redis_conn.pipeline()
    error_count = 0
    for row in rows:
        try:
            row_dict = dict(zip(columns, (to_redis_compatible(v) for v in row)))
            pk_value = row_dict.get(pk, None)
            if not pk_value:
                error_count += 1
                continue  # skip row
            key = f"pg:{table}:{pk_value}"
            pipeline.hset(key, mapping=row_dict)
            pipeline.set(f"{key}:json", json.dumps(row_dict, default=str))
        except Exception as _:
            error_count += 1
    pipeline.execute()
    return (len(rows), error_count)

def starship_print(msg, color=None, delay=0.1, end='\n'):
    if color:
        sys.stdout.write(color)
    sys.stdout.write(msg)
    if color:
        sys.stdout.write(Style.RESET_ALL)
    sys.stdout.write(end)
    sys.stdout.flush()
    time.sleep(delay)

def clone_postgres_to_redis():
    # Welcome Header
    starship_print("\n🚀  STARSHIP SYSTEMS INITIALIZATION", Fore.CYAN, 0.04)
    starship_print("──────────────────────────────────────", Fore.CYAN, 0.03)
    with Postgres() as pg:
        with pg.cursor() as cur:
            with Redis() as redis_conn:
                # Check which tables exist and match to SYSTEMS
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                found_tables = {r[0] for r in cur.fetchall()}
                success = True
                total_tables = 0
                total_rows = 0
                total_errors = 0
                for subsystem, table in SYSTEMS:
                    if table not in found_tables:
                        starship_print(f"[✗] {subsystem:<14}: Table '{table}' not found", Fore.RED, 0.12)
                        success = False
                        continue
                    try:
                        row_count, error_count = clone_table(table, cur, redis_conn)
                        total_tables += 1
                        total_rows += row_count
                        total_errors += error_count
                        if row_count == 0:
                            starship_print(f"[!] {subsystem:<14}: Table '{table}' - EMPTY", Fore.YELLOW, 0.08)
                        elif error_count == 0:
                            starship_print(f"[✓] {subsystem:<14}: Table '{table}' - {row_count} records loaded", Fore.GREEN, 0.12)
                        else:
                            starship_print(f"[!] {subsystem:<14}: Table '{table}' - {row_count} records, {error_count} errors", Fore.YELLOW, 0.16)
                    except Exception as e:
                        starship_print(f"[✗] {subsystem:<14}: Table '{table}' - ERROR: {e}", Fore.RED, 0.15)
                        success = False
    starship_print("──────────────────────────────────────", Fore.CYAN, 0.03)
    if success:
        starship_print(f"ALL SYSTEMS GO. {total_tables} tables, {total_rows} records loaded. READY FOR LAUNCH! 🚀", Fore.GREEN, 0.05)
    else:
        starship_print(f"SYSTEM CHECK PARTIAL: {total_tables} tables, {total_rows} records, {total_errors} errors. LAUNCH ABORTED. ✗", Fore.RED, 0.06)
    starship_print("", None, 0)

if __name__ == "__main__":
    clone_postgres_to_redis()

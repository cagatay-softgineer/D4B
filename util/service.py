from datetime import datetime, timezone
from database.postgres import get_connection

def save_system_health(uptime, response_time, data_accuracy, user_satisfaction, period_start=None, period_end=None):
    """
    Insert a new record into the system_health table.
    """
    now = datetime.now(timezone.utc)
    period_start = period_start or now
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_health (
                    uptime, response_time, data_accuracy, user_satisfaction,
                    period_start, period_end, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uptime,
                    response_time,
                    data_accuracy,
                    user_satisfaction,
                    period_start,
                    period_end,
                    now,
                ),
            )
            conn.commit()

def close_last_system_health_period():
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE system_health SET period_end = %s WHERE period_end IS NULL",
                (now,)
            )
            conn.commit()

def on_app_start():
    close_last_system_health_period()
    save_system_health(
        uptime=0,
        response_time=0,
        data_accuracy=0,
        user_satisfaction=0,
    )
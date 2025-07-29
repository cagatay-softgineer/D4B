from datetime import datetime, date, timezone
from database.postgres import get_connection
import json

def _json_serializer(obj):
    """
    JSON serializer for objects not serializable by default (e.g. datetime, date).
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # Fallback: convert anything else to string
    return str(obj)

def log_activity(action, type_, user_id=None, details=None, duration=None):
    """
    Inserts a row into activity_logs, JSON-encoding 'details' (with datetimes → ISO strings)
    and recording 'duration' (in ms).
    """
    ts = datetime.now(timezone.utc)
    # Safely dump details, converting datetimes to ISO strings
    if details is not None:
        try:
            details_str = json.dumps(details, default=_json_serializer, ensure_ascii=False)
        except Exception:
            # Last-resort: just stringify the whole object
            details_str = json.dumps(str(details), ensure_ascii=False)
    else:
        details_str = None

    duration_ms = duration if duration is not None else 2

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO activity_logs
                  (action, type, user_id, details, timestamp, duration)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (action, type_, user_id, details_str, ts, duration_ms)
            )
            conn.commit()

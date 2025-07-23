from datetime import datetime, timezone
from database.postgres import get_connection
import json

def log_activity(action, type_, user_id=None, details=None, duration=None):
    ts = datetime.now(timezone.utc)
    details_str = json.dumps(details, ensure_ascii=False) if details else None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO activity_logs (action, type, user_id, details, timestamp, duration) VALUES (%s, %s, %s, %s, %s, %s)",
                (action, type_, user_id, details_str, ts, duration)
            )
            conn.commit()

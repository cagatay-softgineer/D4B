# database/reports_queries.py

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Tuple
from database.postgres import get_connection

def _parse_time_range(tr: str) -> Tuple[datetime, datetime]:
    """
    Accepts:
      - "7d"               → last 7 days
      - "24h"              → last 24 hours
      - "last-30-days"     → last 30 days
      - "last-12-hours"    → last 12 hours
      - "start_iso/end_iso"
      - "iso"              → from iso to now
    """
    now = datetime.now(timezone.utc)
    tr = tr.strip().lower()

    # last-N-days / last-N-hours
    m = re.match(r"last-(\d+)-(days|hours)", tr)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        if unit == "days":
            return now - timedelta(days=amount), now
        else:
            return now - timedelta(hours=amount), now

    # shorthand 7d / 24h
    if tr.endswith("d") and tr[:-1].isdigit():
        return now - timedelta(days=int(tr[:-1])), now
    if tr.endswith("h") and tr[:-1].isdigit():
        return now - timedelta(hours=int(tr[:-1])), now

    # ISO start/end
    if "/" in tr:
        start_s, end_s = tr.split("/", 1)
        return datetime.fromisoformat(start_s), datetime.fromisoformat(end_s)

    # single ISO → to now
    try:
        start = datetime.fromisoformat(tr)
        return start, now
    except ValueError:
        # fallback to last 24h if completely unparseable
        return now - timedelta(hours=24), now


def get_job_metrics(time_range: str) -> Dict[str, Any]:
    start, end = _parse_time_range(time_range)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH period_jobs AS (
                  SELECT * FROM jobs
                  WHERE created_at BETWEEN %s AND %s
                )
                SELECT
                  COUNT(*) AS total_jobs,
                  ROUND(100.0 * COUNT(*) FILTER (WHERE status='completed')
                        / NULLIF(COUNT(*),0), 2) AS completion_rate,
                  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/3600)
                        FILTER (WHERE completed_at IS NOT NULL), 2)
                    AS avg_resolution_time,
                  COUNT(*) FILTER (WHERE status='open')         AS open_jobs,
                  COUNT(*) FILTER (WHERE status='in_progress')  AS in_progress_jobs,
                  COUNT(*) FILTER (WHERE status='completed')    AS completed_jobs,
                  COUNT(*) FILTER (WHERE status='closed')       AS closed_jobs
                FROM period_jobs
                """,
                (start, end),
            )
            row = cur.fetchone()
    keys = [
        "total_jobs",
        "completion_rate",
        "avg_resolution_time",
        "open_jobs",
        "in_progress_jobs",
        "completed_jobs",
        "closed_jobs",
    ]
    return dict(zip(keys, row))


def get_team_performance(start: datetime, end: datetime):
    """
    Returns a list of dicts:
      { team_id, team_name, completed, pending, total, efficiency }
    Even if there are no teams, returns [].
    """
    sql = """
    SELECT
      t.id           AS team_id,
      t.name         AS team_name,
      COALESCE(SUM((j.status = 'completed')::int), 0)                 AS completed,
      COALESCE(SUM((j.status IN ('open','in_progress'))::int),  0)     AS pending,
      COALESCE(COUNT(j.id), 0)                                        AS total,
      t.efficiency                                               
    FROM teams t
    LEFT JOIN jobs j
      ON j.team_id = t.id
     AND j.created_at BETWEEN %s AND %s
    GROUP BY t.id, t.name, t.efficiency
    ORDER BY t.name
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (start, end))
            rows = cur.fetchall()
    # rows will be empty list rather than None
    return [
        {
            "teamId":      row[0],
            "teamName":    row[1],
            "completed":   row[2],
            "pending":     row[3],
            "total":       row[4],
            "efficiency":  float(row[5] or 0),
        }
        for row in rows
    ]

def get_priority_distribution(time_range: str) -> List[Dict[str, Any]]:
    start, end = _parse_time_range(time_range)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH pd AS (
                  SELECT priority, COUNT(*) AS cnt
                  FROM jobs
                  WHERE created_at BETWEEN %s AND %s
                  GROUP BY priority
                )
                SELECT
                  priority,
                  cnt   AS count,
                  ROUND(100.0 * cnt / NULLIF((SELECT SUM(cnt) FROM pd),0), 2)
                    AS percentage
                FROM pd
                ORDER BY priority
                """,
                (start, end),
            )
            cols = ["priority", "count", "percentage"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_trend_data(start: datetime, end: datetime, granularity: str):
    """
    Returns a list of dicts:
      { period, total_jobs, completed_jobs, pending_jobs, avg_resolution_time }
    Even if there’s no data, returns [].
    """
    sql = """
    SELECT
      to_char(j.created_at, %s)                               AS period,
      COUNT(*)                                               AS total_jobs,
      SUM((j.status = 'completed')::int)                     AS completed_jobs,
      SUM((j.status IN ('open','in_progress'))::int)         AS pending_jobs,
      AVG(EXTRACT(EPOCH FROM coalesce(j.completed_at, j.created_at) - j.created_at)/3600) 
                                                             AS avg_resolution_time
    FROM jobs j
    WHERE j.created_at BETWEEN %s AND %s
    GROUP BY to_char(j.created_at, %s)
    ORDER BY to_char(j.created_at, %s)
    """
    # choose date format pattern based on granularity
    pattern = {
      "daily":   "YYYY-MM-DD",
      "weekly":  "IYYY-IW",       # ISO week
      "monthly": "YYYY-MM",
    }[granularity]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pattern, start, end, pattern, pattern))
            rows = cur.fetchall()
    return [
        {
            "period":               row[0],
            "totalJobs":            row[1],
            "completedJobs":        row[2],
            "pendingJobs":          row[3],
            "avgResolutionTime":    float(row[4] or 0),
        }
        for row in rows
    ]


def get_activity_log(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  al.id,
                  al.action,
                  al.type,
                  al.user_id,
                  u.name AS user_name,
                  al.details,
                  al.timestamp
                FROM activity_logs al
                LEFT JOIN users u ON al.user_id = u.id
                ORDER BY al.timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            cols = ["id", "action", "type", "user_id", "user_name", "details", "timestamp"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_system_health() -> Dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  uptime,
                  response_time,
                  data_accuracy,
                  user_satisfaction,
                  period_start,
                  period_end,
                  last_updated
                FROM v_current_system_health
                """
            )
            row = cur.fetchone()
            cols = [
                "uptime",
                "response_time",
                "data_accuracy",
                "user_satisfaction",
                "period_start",
                "period_end",
                "last_updated",
            ]
            return dict(zip(cols, row))


def export_report_csv(time_range: str, options: dict) -> bytes:
    """
    Builds a single CSV string containing:
      - job_metrics
      - team_performance
      - priority_distribution
      - job_trends
      - activity_log
      - system_health
    """
    import csv
    from io import StringIO

    m      = get_job_metrics(time_range)
    tp     = get_team_performance(time_range)
    pdist  = get_priority_distribution(time_range)
    trends = get_trend_data(time_range, options.get("granularity", "daily"))
    alog   = get_activity_log(options.get("limit", 10))
    sh     = get_system_health()

    buf = StringIO()
    writer = csv.writer(buf)

    # Job Metrics
    writer.writerow(["Job Metrics"])
    for k, v in m.items():
        writer.writerow([k, v])
    writer.writerow([])

    # Team Performance
    writer.writerow(["Team Performance"])
    writer.writerow(list(tp[0].keys()) if tp else [])
    for row in tp:
        writer.writerow(row.values())
    writer.writerow([])

    # Priority Distribution
    writer.writerow(["Priority Distribution"])
    writer.writerow(list(pdist[0].keys()) if pdist else [])
    for row in pdist:
        writer.writerow(row.values())
    writer.writerow([])

    # Trends
    writer.writerow(["Trend Data"])
    writer.writerow(list(trends[0].keys()) if trends else [])
    for row in trends:
        writer.writerow(row.values())
    writer.writerow([])

    # Activity Log
    writer.writerow(["Activity Log"])
    writer.writerow(list(alog[0].keys()) if alog else [])
    for row in alog:
        writer.writerow(row.values())
    writer.writerow([])

    # System Health
    writer.writerow(["System Health"])
    for k, v in sh.items():
        writer.writerow([k, v])

    return buf.getvalue().encode("utf-8")


def refresh_reports_data() -> Dict[str, Any]:
    """
    Stub: you can insert into job_metrics, job_trends, etc. here.
    """
    # e.g. snapshot current metrics into job_metrics table...
    return {"refreshed": True}

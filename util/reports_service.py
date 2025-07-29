# util/reports_service.py

from typing import Any, Dict, List, Tuple
from database.reports_queries import (
    get_job_metrics     as db_get_job_metrics,
    get_team_performance       as db_get_team_performance,
    get_priority_distribution   as db_get_priority_distribution,
    get_trend_data      as db_get_trend_data,
    get_activity_log    as db_get_activity_log,
    get_system_health   as db_get_system_health,
    export_report_csv   as db_export_report_csv,
    refresh_reports_data as db_refresh_reports_data,
)

def get_job_metrics(time_range: str) -> Dict[str, Any]:
    raw = db_get_job_metrics(time_range)
    return {
        "totalJobs":           raw["total_jobs"],
        "completionRate":      raw["completion_rate"],
        "avgResolutionTime":   raw["avg_resolution_time"],
        "openJobs":            raw["open_jobs"],
        "inProgressJobs":      raw["in_progress_jobs"],
        "completedJobs":       raw["completed_jobs"],
        "closedJobs":          raw["closed_jobs"],
    }

def get_team_performance(time_range: str) -> List[Dict[str, Any]]:
    rows = db_get_team_performance(time_range)
    return [
        {
            "teamId":             r["team_id"],
            "teamName":           r["team_name"],
            "avgResolutionTime":  r["avg_resolution_time"],
            "completedJobs":      r["completed_jobs"],
        }
        for r in rows
    ]

def get_priority_distribution(time_range: str) -> List[Dict[str, Any]]:
    rows = db_get_priority_distribution(time_range)
    # keys are already priority, count, percentage
    return rows

def get_trend_data(time_range: str, granularity: str = "daily") -> List[Dict[str, Any]]:
    rows = db_get_trend_data(time_range, granularity)
    return [
        {
            "period":              r["period"],
            "totalJobs":           r["total_jobs"],
            "completedJobs":       r["completed_jobs"],
            "pendingJobs":         r["pending_jobs"],
            "avgResolutionTime":   r["avg_resolution_time"],
        }
        for r in rows
    ]

def get_activity_log(limit: int = 10) -> List[Dict[str, Any]]:
    rows = db_get_activity_log(limit)
    return [
        {
            "id":           r["id"],
            "action":       r["action"],
            "type":         r["type"],
            "userId":       r["user_id"],
            "userName":     r["user_name"],
            "details":      r["details"],
            "timestamp":    r["timestamp"],
        }
        for r in rows
    ]

def get_system_health() -> Dict[str, Any]:
    raw = db_get_system_health()
    return {
        "uptime":           raw["uptime"],
        "responseTime":     raw["response_time"],
        "dataAccuracy":     raw["data_accuracy"],
        "userSatisfaction": raw["user_satisfaction"],
        "periodStart":      raw["period_start"],
        "periodEnd":        raw["period_end"],
        "lastUpdated":      raw["last_updated"],
    }

def export_report_bytes(fmt: str, time_range: str, options: dict) -> Tuple[bytes, str, str]:
    # still uses CSV exporter under the hood
    csv_bytes = db_export_report_csv(time_range, options)
    return csv_bytes, "text/csv", "csv"

def refresh_reports_data() -> Dict[str, Any]:
    return db_refresh_reports_data()

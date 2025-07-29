# blueprints/reports.py

from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from util.reports_service import (
    get_job_metrics,
    get_team_performance,
    get_priority_distribution,
    get_trend_data,
    get_activity_log,
    get_system_health,
    export_report_bytes,
    refresh_reports_data,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/metrics", methods=["GET"])
@jwt_required()
def metrics():
    time_range = request.args.get("timeRange", "")
    try:
        data = get_job_metrics(time_range)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/teams", methods=["GET"])
@jwt_required()
def teams():
    time_range = request.args.get("timeRange", "")
    try:
        data = get_team_performance(time_range)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/priority", methods=["GET"])
@jwt_required()
def priority():
    time_range = request.args.get("timeRange", "")
    try:
        data = get_priority_distribution(time_range)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/trends", methods=["GET"])
@jwt_required()
def trends():
    time_range = request.args.get("timeRange", "")
    granularity = request.args.get("granularity", "daily")
    try:
        data = get_trend_data(time_range, granularity)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/activity", methods=["GET"])
@jwt_required()
def activity():
    limit = int(request.args.get("limit", 10))
    try:
        data = get_activity_log(limit)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/system-health", methods=["GET"])
@jwt_required()
def system_health():
    try:
        data = get_system_health()
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/export", methods=["POST"])
@jwt_required()
def export():
    """
    Expects JSON:
      { format: "csv" | "xlsx", timeRange: string, options: {...} }
    Returns a file download.
    """
    body = request.get_json() or {}
    fmt = body.get("format", "csv")
    time_range = body.get("timeRange", "")
    options = body.get("options", {})

    try:
        blob_bytes, mime, ext = export_report_bytes(fmt, time_range, options)
        return send_file(
            BytesIO(blob_bytes),
            mimetype=mime,
            as_attachment=True,
            download_name=f"report_{time_range}.{ext}",
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@reports_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh():
    """
    Trigger a back-end refresh of cached report data.
    """
    try:
        result = refresh_reports_data()
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

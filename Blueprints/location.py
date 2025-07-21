from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request_optional, get_jwt_identity
from datetime import datetime, timezone
from pydantic import ValidationError
from database.location_ops import insert_location
from util.models import LocationPayload
from helper.error import logger

location_bp = Blueprint("location", __name__)

@location_bp.route("/location", methods=["POST"])
def save_location():
    """
    Receives job_id, latitude & longitude, saves with timestamp and user_id (optional).
    Example payload:
    {
        "job_id": 123,
        "latitude": 39.000,
        "longitude": 35.000
    }
    """
    try:
        payload = LocationPayload.parse_obj(request.get_json())
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    # Try to get user_id if JWT present; else, set as None
    try:
        verify_jwt_in_request_optional()
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    timestamp = datetime.now(timezone.utc)

    # Save to DB
    try:
        insert_location(
            job_id=payload.job_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            user_id=user_id,
            timestamp=timestamp
        )
        print(f"Job {payload.job_id}, User {user_id}: ({payload.latitude}, {payload.longitude}) at {timestamp}")
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Failed to save location"}), 500

    return jsonify({
        "message": "Location saved",
        "job_id": payload.job_id,
        "user_id": user_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "timestamp": timestamp.isoformat()
    }), 201

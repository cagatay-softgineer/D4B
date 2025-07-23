from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.postgres import get_connection
from database.user_queries import get_user_id_by_email
from util.activity_logger import log_activity
from pydantic import BaseModel, ValidationError, Field
from psycopg2.extras import RealDictCursor

locations_bp = Blueprint("locations", __name__)

class LocationCreateRequest(BaseModel):
    job_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    user_id: int | None = None

class LocationUpdateRequest(BaseModel):
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

# --- Endpoint: Create Location ---
@locations_bp.route("/", methods=["POST"])
@jwt_required()
def create_location():
    try:
        payload = LocationCreateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Validate job_id exists
            cur.execute("SELECT id FROM jobs WHERE id = %s", (payload.job_id,))
            if not cur.fetchone():
                return jsonify({"error": "Invalid job_id"}), 404

            # Validate user_id if provided
            if payload.user_id is not None:
                cur.execute("SELECT id FROM users WHERE id = %s", (payload.user_id,))
                if not cur.fetchone():
                    return jsonify({"error": "Invalid user_id"}), 404

            cur.execute(
                """INSERT INTO locations (job_id, user_id, latitude, longitude, timestamp)
                   VALUES (%s, %s, %s, %s, NOW())
                   RETURNING id, job_id, user_id, latitude, longitude, timestamp
                """,
                (payload.job_id, payload.user_id, payload.latitude, payload.longitude)
            )
            location = cur.fetchone()
            conn.commit()

    log_activity("Location created", "location", user_id=get_user_id_by_email(get_jwt_identity()), details=location)
    return jsonify(location), 201

# --- Endpoint: Update Location ---
@locations_bp.route("/<int:location_id>", methods=["PATCH"])
@jwt_required()
def update_location(location_id):
    try:
        payload = LocationUpdateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    update_fields = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_fields:
        return jsonify({"error": "No updatable fields provided"}), 400

    set_expr = ", ".join(f"{k}=%s" for k in update_fields)
    values = list(update_fields.values()) + [location_id]
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""UPDATE locations SET {set_expr}, timestamp=NOW()
                    WHERE id=%s RETURNING id, job_id, user_id, latitude, longitude, timestamp
                """, values
            )
            location = cur.fetchone()
            if not location:
                return jsonify({"error": "Location not found"}), 404
            conn.commit()

    log_activity("Location updated", "location", user_id=get_user_id_by_email(get_jwt_identity()), details=location)
    return jsonify(location)

# --- Endpoint: Get Locations (Paginated/Filtered) ---
@locations_bp.route("/", methods=["GET"])
@jwt_required()
def get_locations():
    job_id = request.args.get("job_id")
    user_id = request.args.get("user_id")
    start = request.args.get("start")
    end = request.args.get("end")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset = (page - 1) * page_size

    where = []
    params = []
    if job_id:
        where.append("job_id = %s")
        params.append(job_id)
    if user_id:
        where.append("user_id = %s")
        params.append(user_id)
    if start:
        where.append("timestamp >= %s")
        params.append(start)
    if end:
        where.append("timestamp <= %s")
        params.append(end)

    where_clause = "WHERE " + " AND ".join(where) if where else ""

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""SELECT id, job_id, user_id, latitude, longitude, timestamp
                    FROM locations
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """, (*params, page_size, offset)
            )
            results = cur.fetchall()

    return jsonify(results)

# --- Endpoint: Get Single Location ---
@locations_bp.route("/<int:location_id>", methods=["GET"])
@jwt_required()
def get_location(location_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, job_id, user_id, latitude, longitude, timestamp FROM locations WHERE id=%s",
                (location_id,)
            )
            location = cur.fetchone()
    if not location:
        return jsonify({"error": "Location not found"}), 404
    return jsonify(location)

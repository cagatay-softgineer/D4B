from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import BaseModel, Field, ValidationError
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from database.postgres import get_connection
from database.user_queries import get_user_id_by_email, get_user_role_by_email
from util.activity_logger import log_activity
from Blueprints.notifications import send_notification

jobs_bp = Blueprint("jobs", __name__)

class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2)
    description: str | None = None
    priority: str = Field("Medium", regex="^(Critical|High|Medium|Low)$")
    location: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    team_id: int | None = None
    assignee_id: int | None = None

class JobUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = Field(None, regex="^(Critical|High|Medium|Low)$")
    location: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    status: str | None = Field(None, regex="^(open|in_progress|completed|closed)$")
    team_id: int | None = None
    assignee_id: int | None = None

# --- Create a Job ---
@jobs_bp.route("/", methods=["POST"])
@jwt_required()
def create_job():
    try:
        payload = JobCreateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    reporter_id = get_user_id_by_email(get_jwt_identity())
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO jobs (
                  title, description, priority,
                  location, latitude, longitude,
                  reporter_id, team_id, assignee_id, status
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open'
                )
                RETURNING id, title, status, created_at
                """,
                (
                    payload.title,
                    payload.description,
                    payload.priority,
                    payload.location,
                    payload.latitude,
                    payload.longitude,
                    reporter_id,
                    payload.team_id,
                    payload.assignee_id,
                )
            )
            job = cur.fetchone()
            conn.commit()

    log_activity("Job created", "job", user_id=reporter_id, details=job)
    return jsonify(job), 201

# --- Update a Job ---
@jobs_bp.route("/<int:job_id>", methods=["PATCH"])
@jwt_required()
def update_job(job_id):
    try:
        payload = JobUpdateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    updatable = {k: v for k, v in payload.dict().items() if v is not None}
    if not updatable:
        return jsonify({"error": "No updatable fields provided"}), 400

    # Build safe SET clause
    cols = [sql.Identifier(k) for k in updatable.keys()]
    set_clause = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(col) for col in cols
    )
    params = list(updatable.values()) + [job_id]

    query = sql.SQL(
        """
        UPDATE jobs
        SET {set_clause}, updated_at = NOW()
        WHERE id = %s
        RETURNING id, title, status, updated_at
        """
    ).format(set_clause=set_clause)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            job = cur.fetchone()
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if "status" in updatable:
                cur.execute(
                    """
                    INSERT INTO job_status_history (
                      job_id, old_status, new_status, changed_by
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        request.json.get("old_status"),
                        updatable["status"],
                        get_jwt_identity(),
                    )
                )
            conn.commit()
    send_notification(get_user_id_by_email(get_jwt_identity()), job_id, f"Your Intanded job is Updated by {get_user_role_by_email(get_jwt_identity())[0].upper()}!")
    log_activity("Job updated", "job", user_id=get_user_id_by_email(get_jwt_identity()), details=job)
    return jsonify(job)

# --- List/Filter/Search Jobs ---
@jobs_bp.route("/", methods=["GET"])
@jwt_required()
def list_jobs():
    # Filters
    filters = [
        ("status", request.args.get("status")),
        ("priority", request.args.get("priority")),
        ("team_id", request.args.get("team_id")),
        ("assignee_id", request.args.get("assignee_id")),
        ("reporter_id", request.args.get("reporter_id")),
    ]
    conditions = []
    params = []

    for col, val in filters:
        if val is not None:
            conditions.append(
                sql.SQL("{} = %s").format(sql.Identifier(col))
            )
            params.append(val)

    search = request.args.get("search")
    if search:
        conditions.append(
            sql.SQL("(title ILIKE %s OR description ILIKE %s)")
        )
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = (
        sql.SQL("WHERE ") + sql.SQL(" AND ").join(conditions)
        if conditions else sql.SQL("")
    )

    page      = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset    = (page - 1) * page_size
    params.extend([page_size, offset])

    query = sql.SQL(
        """
        SELECT *
          FROM jobs
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
    ).format(where=where_clause)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            jobs = cur.fetchall()

    return jsonify(jobs)

# --- Get Single Job Details ---
@jobs_bp.route("/<int:job_id>", methods=["GET"])
@jwt_required()
def get_job(job_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM jobs WHERE id = %s", (job_id,)
            )
            job = cur.fetchone()
            if not job:
                return jsonify({"error": "Job not found"}), 404

            cur.execute(
                "SELECT * FROM job_status_history WHERE job_id = %s ORDER BY changed_at", (job_id,)
            )
            job["status_history"] = cur.fetchall()

    return jsonify(job)

# --- Close Job ---
@jobs_bp.route("/<int:job_id>/close", methods=["PATCH"])
@jwt_required()
def close_job(job_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'completed', completed_at = NOW()
                WHERE id = %s AND status != 'completed'
                RETURNING id, status, completed_at
                """,
                (job_id,)
            )
            job = cur.fetchone()
            if not job:
                return jsonify({"error": "Job not found or already completed"}), 404

            cur.execute(
                """
                INSERT INTO job_status_history (
                  job_id, old_status, new_status, changed_by
                ) VALUES (%s, %s, %s, %s)
                """,
                (job_id, "in_progress", "completed", get_jwt_identity())
            )
            conn.commit()

    log_activity("Job closed", "job", user_id=get_user_id_by_email(get_jwt_identity()), details=job)
    return jsonify(job)

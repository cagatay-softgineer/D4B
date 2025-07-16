from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from util.authlib import requires_scope
from database.postgres import get_connection
from pydantic import BaseModel, ValidationError
from util.activity_logger import log_activity

teams_bp = Blueprint("teams", __name__)

class TeamCreateRequest(BaseModel):
    name: str
    description: str | None = None

class TeamUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    efficiency: float | None = None

@teams_bp.route("/", methods=["POST"])
@jwt_required()
@requires_scope("admin")
def create_team():
    try:
        payload = TeamCreateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (name, description, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) RETURNING id, name, description",
                (payload.name, payload.description),
            )
            team = cur.fetchone()
    log_activity("Team created", "team", user_id=get_jwt_identity(), details=payload.dict())
    return jsonify({"team": dict(zip(["id", "name", "description"], team))}), 201

@teams_bp.route("/", methods=["GET"])
@jwt_required()
def list_teams():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset = (page - 1) * page_size
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, efficiency FROM teams ORDER BY name LIMIT %s OFFSET %s", (page_size, offset))
            teams = cur.fetchall()
    return jsonify([
        dict(zip(["id", "name", "description", "efficiency"], row)) for row in teams
    ])

@teams_bp.route("/<int:team_id>", methods=["PATCH"])
@jwt_required()
@requires_scope("admin")
def update_team(team_id):
    try:
        payload = TeamUpdateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    fields = {k: v for k, v in payload.dict().items() if v is not None}
    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400

    set_expr = ", ".join(f"{k}=%s" for k in fields)
    params = list(fields.values()) + [team_id]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE teams SET {set_expr}, updated_at=NOW() WHERE id=%s RETURNING id, name, description, efficiency",
                params
            )
            team = cur.fetchone()
            if not team:
                return jsonify({"error": "Team not found"}), 404

    log_activity("Team updated", "team", user_id=get_jwt_identity(), details=fields)
    return jsonify({"team": dict(zip(["id", "name", "description", "efficiency"], team))})

@teams_bp.route("/<int:team_id>", methods=["DELETE"])
@jwt_required()
@requires_scope("admin")
def delete_team(team_id):
    # Check for team members before delete
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM team_members WHERE team_id=%s", (team_id,))
            member_count = cur.fetchone()[0]
            if member_count > 0:
                return jsonify({"error": "Cannot delete team with members"}), 409
            cur.execute("DELETE FROM teams WHERE id=%s RETURNING id", (team_id,))
            deleted = cur.fetchone()
            if not deleted:
                return jsonify({"error": "Team not found"}), 404
    log_activity("Team deleted", "team", user_id=get_jwt_identity(), details={"team_id": team_id})
    return jsonify({"message": "Team deleted", "team_id": team_id})

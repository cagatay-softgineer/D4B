from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from database.user_queries import get_user_id_by_email
from util.authlib import requires_scope
from database.postgres import get_connection
from util.activity_logger import log_activity

team_members_bp = Blueprint("team_members", __name__)

@team_members_bp.route("/<int:team_id>/members", methods=["POST"])
@jwt_required()
@requires_scope("admin")
def assign_member(team_id):
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO team_members (team_id, user_id, joined_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING",
                (team_id, user_id)
            )
    log_activity("User assigned to team", "team_members", user_id=get_jwt_identity(), details={"team_id": team_id, "user_id": user_id})
    return jsonify({"message": "User assigned to team", "team_id": team_id, "user_id": user_id})

@team_members_bp.route("/<int:team_id>/members/<int:user_id>", methods=["DELETE"])
@jwt_required()
@requires_scope("admin")
def remove_member(team_id, user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM team_members WHERE team_id=%s AND user_id=%s RETURNING user_id",
                (team_id, user_id)
            )
            deleted = cur.fetchone()
            if not deleted:
                return jsonify({"error": "Assignment not found"}), 404
    log_activity("User removed from team", "team_members", user_id=get_user_id_by_email(get_jwt_identity()), details={"team_id": team_id, "user_id": user_id})
    return jsonify({"message": "User removed from team", "team_id": team_id, "user_id": user_id})

@team_members_bp.route("/<int:team_id>/members", methods=["GET"])
@jwt_required()
def list_team_members(team_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.name, u.email, u.role FROM team_members tm JOIN users u ON tm.user_id = u.id WHERE tm.team_id=%s",
                (team_id,)
            )
            members = cur.fetchall()
    return jsonify([
        dict(zip(["id", "name", "email", "role"], row)) for row in members
    ])

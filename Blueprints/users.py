from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address
from config.settings import settings
from database.user_queries import get_all_users, get_one_user_by_email
from util.activity_logger import log_activity
from util.authlib import requires_scope
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.postgres import get_connection
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import Forbidden

users_bp = Blueprint("users", __name__)
limiter = Limiter(key_func=get_remote_address)

# Enable CORS for all routes in this blueprint
CORS(users_bp, resources=settings.CORS_resource_allow_all)


# Add /healthcheck to each blueprint
@users_bp.before_request
def log_user_requests():
    print("User blueprint request received.")


# Add /healthcheck to each blueprint
@users_bp.route("/healthcheck", methods=["GET"])
def user_healthcheck():
    print("User Service healthcheck requested")
    return jsonify({"status": "ok", "service": "User Service"}), 200


@users_bp.route("/get_all_users", methods=["GET"])
@requires_scope("admin")
def get_all():
    # Get pagination params from query string
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    users, total = get_all_users(page, page_size)
    return jsonify({
        "users": users,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total // page_size) + (1 if total % page_size else 0),
    })

@users_bp.route("/get_one_user", methods=["GET"])
@requires_scope("admin")
def get_one():
    # Get pagination params from query string
    try:
        user_email = str(request.args.get("email"))
    except ValueError:
        return jsonify({"error": "Invalid parameters"}), 400

    user = get_one_user_by_email(user_email)
    return jsonify({
        "user" : user,
    })

class UserUpdateRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    status: str | None = None

def user_is_admin(jwt_claims):
    return "admin" in jwt_claims.get("scopes", [])

def user_can_edit(target_user_id, current_user_id, jwt_claims):
    return user_is_admin(jwt_claims) or (target_user_id == current_user_id)

@users_bp.route("/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
    current_user = get_jwt_identity()
    jwt_claims = request.jwt_user_claims if hasattr(request, "jwt_user_claims") else {}
    # Only allow admin or self
    if not user_can_edit(user_id, current_user, jwt_claims):
        raise Forbidden("Not authorized to update this user")

    try:
        payload = UserUpdateRequest.parse_obj(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    fields = {k: v for k, v in payload.dict().items() if v is not None}
    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400

    set_expr = ", ".join(f"{k}=%s" for k in fields)
    params = list(fields.values()) + [user_id]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {set_expr}, updated_at=NOW() WHERE id=%s RETURNING id, email, name, avatar_url, status, role",
                params
            )
            user = cur.fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 404

    log_activity("User profile updated", "user", user_id=current_user, details=fields)
    return jsonify({"user": dict(zip(["id", "email", "name", "avatar_url", "status", "role"], user))})

@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
@requires_scope("admin")
def delete_user(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status='deleted', updated_at=NOW() WHERE id=%s RETURNING email", (user_id,))
            deleted = cur.fetchone()
            if not deleted:
                return jsonify({"error": "User not found"}), 404
    log_activity("User soft-deleted", "user", user_id=get_jwt_identity(), details={"target_user_id": user_id})
    return jsonify({"message": "User deleted (soft delete)", "user_id": user_id})

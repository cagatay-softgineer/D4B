from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address
from config.settings import settings
from database.user_queries import get_all_users, get_one_user_by_email
from util.authlib import requires_scope

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

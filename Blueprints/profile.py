from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address
from config.settings import settings
from database.user_queries import (
    get_current_user_by_email
)
from util.authlib import requires_scope

profile_bp = Blueprint("profile", __name__)
limiter = Limiter(key_func=get_remote_address)

# Enable CORS for all routes in this blueprint
CORS(profile_bp, resources=settings.CORS_resource_allow_all)


# Add /healthcheck to each blueprint
@profile_bp.before_request
def log_user_requests():
    print("User blueprint request received.")


# Add /healthcheck to each blueprint
@profile_bp.route("/healthcheck", methods=["GET"])
def user_healthcheck():
    print("User Service healthcheck requested")
    return jsonify({"status": "ok", "service": "User Service"}), 200


@profile_bp.route("/view", methods=["POST"])
@jwt_required()
@requires_scope("user")
def view_profile():
    current_user = get_jwt_identity()
    rows = get_current_user_by_email(current_user)
    print(rows)
    return jsonify(rows), 200

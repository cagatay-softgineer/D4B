from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address
import bcrypt
from database import user_queries as db
from util.activity_logger import log_activity
from util.models import RegisterRequest, LoginRequest
from pydantic import ValidationError
from util.authlib import role_scopes
from config.settings import settings
from database.user_queries import get_user_id_by_email

auth_bp = Blueprint("auth", __name__)
limiter = Limiter(key_func=get_remote_address)
CORS(auth_bp, resources=settings.CORS_resource_allow_all, supports_credentials=True)


@auth_bp.before_request
def log_auth_requests():
    print("Auth blueprint request received.")


@auth_bp.route("/healthcheck", methods=["GET"])
def auth_healthcheck():
    return jsonify({"status": "ok", "service": "Auth Service"}), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        payload = RegisterRequest.parse_obj(request.get_json())
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    success = False
    error_text = None
    error_type = None
    user_id = None

    try:
        user_id = db.insert_user(payload.email, payload.password)
        success = True
        return jsonify({"message": "User registered successfully", "user_id": user_id}), 201
    except Exception as e:
        error_text = str(e)
        error_type = "registration_exception"
        return jsonify({"error": "Registration failed"}), 500
    finally:
        log_activity(
            "User registration",
            "auth",
            user_id=user_id,
            details={"success": success, "error_type": error_type, "error": error_text},
        )


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        payload = LoginRequest.parse_obj(request.get_json())
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    success = False
    error_text = None
    error_type = None
    user_id = None

    try:
        status = db.get_user_status_by_email(payload.email)[0]
        user_id = get_user_id_by_email(payload.email)

        if status in ("deactivate", "banned", "timeout"):
            error_type = "inactive_or_banned"
            return jsonify({"error": "Account is inactive or banned"}), 403

        hashed = db.get_user_password_by_email(payload.email)[0]
        if not bcrypt.checkpw(payload.password.encode(), hashed.encode()):
            error_type = "wrong_password"
            return jsonify({"error": "Invalid credentials"}), 401

        role = db.get_user_role_by_email(payload.email)[0]
        claims = {"scopes": role_scopes[role]}
        access = create_access_token(identity=payload.email, expires_delta=timedelta(days=7), additional_claims=claims)
        refresh = create_refresh_token(identity=payload.email, expires_delta=timedelta(days=30))

        success = True
        return jsonify({"access_token": access, "refresh_token": refresh, "user_id": user_id}), 200

    except Exception as e:
        error_text = str(e)
        error_type = "authentication_exception"
        return jsonify({"error": "Authentication failed"}), 500
    finally:
        log_activity(
            "User login",
            "auth",
            user_id=user_id,
            details={"success": success, "error_type": error_type, "error": error_text},
        )


@auth_bp.route("/admin", methods=["POST"])
def admin_login():
    start_time = datetime.now(timezone.utc)
    try:
        payload = LoginRequest.parse_obj(request.get_json())
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    success = False
    error_text = None
    error_type = None
    user_id = None

    try:
        status = db.get_user_status_by_email(payload.email)[0]
        user_id = get_user_id_by_email(payload.email)

        if status in ("deactivate", "banned", "timeout"):
            error_type = "inactive_or_banned"
            return jsonify({"error": "Account is inactive or banned"}), 403

        role = db.get_user_role_by_email(payload.email)[0]
        if role != "admin":
            error_type = "insufficient_role"
            return jsonify({"error": "Insufficient permissions"}), 401

        hashed = db.get_user_password_by_email(payload.email)[0]
        if not bcrypt.checkpw(payload.password.encode(), hashed.encode()):
            error_type = "wrong_password"
            return jsonify({"error": "Invalid credentials"}), 401

        claims = {"scopes": role_scopes[role]}
        access = create_access_token(identity=payload.email, expires_delta=timedelta(days=7), additional_claims=claims)
        refresh = create_refresh_token(identity=payload.email, expires_delta=timedelta(days=30))

        success = True
        return jsonify({"access_token": access, "refresh_token": refresh, "user_id": user_id}), 200

    except Exception as e:
        error_text = str(e)
        error_type = "admin_authentication_exception"
        return jsonify({"error": "Admin authentication failed"}), 500
    finally:
        try:
            delta = datetime.now(timezone.utc) - start_time
            duration_ms = int(delta.total_seconds() * 1000)
        except Exception:
            duration_ms = None
        finally:
            log_activity(
                "Admin login",
                "auth",
                user_id=user_id,
                details={"success": success, "error_type": error_type, "error": error_text},
                duration=duration_ms
            )


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    start_time = datetime.now(timezone.utc)
    success = False
    error_text = None
    error_type = None
    user_id = None

    try:
        identity = get_jwt_identity()
        user_id = get_user_id_by_email(identity)
        role = db.get_user_role_by_email(identity)[0]
        claims = {"scopes": role_scopes[role]}

        new_access = create_access_token(identity=identity, expires_delta=timedelta(days=7), additional_claims=claims)
        success = True
        return jsonify({"access_token": new_access}), 200

    except Exception as e:
        error_text = str(e)
        error_type = "refresh_exception"
        return jsonify({"error": "Token refresh failed"}), 500
    finally:
        try:
            delta = datetime.now(timezone.utc) - start_time
            duration_ms = int(delta.total_seconds() * 1000)
        except Exception:
            duration_ms = None
        finally:
            log_activity(
                "Token refresh",
                "auth",
                user_id=user_id,
                details={"success": success, "error_type": error_type, "error": error_text},
                duration=duration_ms
            )


@auth_bp.route("/test", methods=["POST"])
def test():
    try:
        payload = LoginRequest.parse_obj(request.get_json())
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 400

    success = False
    error_text = None
    error_type = None
    user_id = None

    try:
        role = db.get_user_role_by_email(payload.email)[0]
        claims = {"scopes": role_scopes[role]}
        access = create_access_token(identity=payload.email, expires_delta=timedelta(days=7), additional_claims=claims)
        refresh = create_refresh_token(identity=payload.email, expires_delta=timedelta(days=30))
        user_id = get_user_id_by_email(payload.email)

        success = True
        return jsonify({"access_token": access, "refresh_token": refresh, "user_id": user_id}), 200

    except Exception as e:
        error_text = str(e)
        error_type = "test_exception"
        return jsonify({"error": "Test token issuance failed"}), 500
    finally:
        log_activity(
            "Test tokens",
            "auth",
            user_id=user_id,
            details={"success": success, "error_type": error_type, "error": error_text},
        )

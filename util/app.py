from config.settings import settings
from flask import Flask, jsonify, request, g
from flask_talisman import Talisman
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_cors import CORS
from util.blueprints import register_blueprints
from util.logit import get_logger
from util.error_handlers import register_error_handlers
from util.service import on_app_start
from datetime import datetime, timezone
from database.postgres import get_connection

def create_app(app: Flask, _start_time:any, testing=False):

    logger = get_logger("logs", "Main Service")

    Talisman(app,
             strict_transport_security=True,
             strict_transport_security_max_age=31536000,
             strict_transport_security_include_subdomains=True,
             strict_transport_security_preload=True,
             content_security_policy=settings.csp_allow_all)

    jwt = JWTManager(app)  # noqa: F841
    limiter = Limiter(app)  # noqa: F841

    app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
    app.config["SWAGGER_URL"] = "/api/docs"
    app.config["API_URL"] = "/static/swagger.json"
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["PREFERRED_URL_SCHEME"] = "https"
    app.config["TESTING"] = testing

    # Turn off Flask’s strict‐slash behavior
    app.url_map.strict_slashes = False

    CORS(app, resources=settings.CORS_resource_allow_all, supports_credentials=True)

    # Middleware to log all requests

    def log_request():
        """
        Logs each incoming HTTP request to both the application logger and the activity_logs table.
        Attempts to log user_id if authenticated, otherwise logs as 'anonymous'.
        """
        # Log to application log
        logger.info(f"Request received: {request.method} {request.url}")

        # Try to get user info from Flask context if available (JWT, session, etc.)
        user_id = getattr(g, "user_id", None)  # Example: set g.user_id after auth middleware

        # Optionally, determine action/type from the request
        action = f"HTTP {request.method}"
        type_ = "api"

        # Compose details
        details = {
            "url": request.url,
            "remote_addr": request.remote_addr,
            "args": request.args.to_dict(),
        }

        # Save to database
        ts = datetime.now(timezone.utc)
        import json
        details_str = json.dumps(details, ensure_ascii=False)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO activity_logs (action, type, user_id, details, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (action, type_, user_id, details_str, ts)
                )
                conn.commit()

    app.before_request(log_request)

    app = register_blueprints(app)
    app = register_error_handlers(app)

    # Add /healthcheck to each blueprint
    @app.route("/healthcheck", methods=["GET"])
    def app_healthcheck():
        logger.info("Main Service healthcheck requested")
        return jsonify({"status": "ok", "service": "Main Service"}), 200

    on_app_start(_start_time)

    return app

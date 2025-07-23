from config.settings import settings
from flask import Flask, json, jsonify, request, g
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

    def start_timer():
        """
        Record the start time of each request for duration measurement.
        """
        g.start_time = datetime.now(timezone.utc)


    def log_request(response):
        """
        After-request handler that logs HTTP request and response details,
        including duration, user context, and request metadata, to both
        the application logger and the activity_logs table.

        Strips sensitive fields (e.g., passwords) from JSON bodies.

        Should be registered with Flask's after_request decorator.
        """
        # Compute duration
        try:
            delta = datetime.now(timezone.utc) - g.start_time
            duration_ms = int(delta.total_seconds() * 1000)
        except Exception:
            duration_ms = None

        # User context
        user_id = getattr(g, "user_id", None)

        # Action and type
        action = f"{request.method} {request.path}"
        type_ = "api"

        # Compose details
        details = {
            "url": request.url,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "query_params": request.args.to_dict(),
        }

        # Include JSON body if present, stripping sensitive keys
        if request.is_json:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                body.pop("password", None)
            details["json_body"] = body

        # Application logger (structured)
        logger.info(
            f"Request {action} completed with status {response.status_code}",
            extra={"details": details}
        )

        # Persist to DB
        try:
            ts = datetime.now(timezone.utc)
            payload = json.dumps(details, ensure_ascii=False)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO activity_logs
                            (action, type, user_id, details, timestamp)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (action, type_, user_id, payload, ts),
                    )
                    conn.commit()
        except Exception as db_err:
            logger.error("Failed to write request log to DB", exc_info=db_err)

        return response


    app.before_request(start_timer)
    app.after_request(log_request)

    app = register_blueprints(app)
    app = register_error_handlers(app)

    # Add /healthcheck to each blueprint
    @app.route("/healthcheck", methods=["GET"])
    def app_healthcheck():
        logger.info("Main Service healthcheck requested")
        return jsonify({"status": "ok", "service": "Main Service"}), 200

    on_app_start(_start_time)

    return app

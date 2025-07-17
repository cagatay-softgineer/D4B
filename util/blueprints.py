from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from Blueprints.auth import auth_bp
from database.postgres import check_database
from datetime import datetime
import time
from Blueprints.users import user_bp
from Blueprints.profile import profile_bp
from Blueprints.jobs import jobs_bp
from Blueprints.attachments import attachments_bp
from Blueprints.locations import locations_bp
from Blueprints.notifications import notifications_bp
from Blueprints.teams import teams_bp
from Blueprints.team_members import team_members_bp


def register_blueprints(app: Flask, testing=False):
    # Swagger documentation setup
    swaggerui_blueprint = get_swaggerui_blueprint(
        app.config["SWAGGER_URL"],
        app.config["API_URL"],
        config={"app_name": "Micro Service"},
    )

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/admin")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(attachments_bp, url_prefix="/file")
    app.register_blueprint(locations_bp, url_prefix="/geo")
    app.register_blueprint(notifications_bp, url_prefix="/notify")
    app.register_blueprint(teams_bp, url_prefix="/teams")
    app.register_blueprint(team_members_bp, url_prefix="/team_members")
    app.register_blueprint(swaggerui_blueprint, url_prefix=app.config["SWAGGER_URL"])

    @app.route("/health", methods=["GET"])
    def health_check():
        start_time = time.time()

        # Basic status (add more checks as needed)
        db_ok = check_database()
        is_healthy = db_ok  # Add more logic for full stack

        response = {
            "success": is_healthy,
            "isApiAvailable": is_healthy,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "responseTime": int((time.time() - start_time) * 1000),  # in ms
            "message": "API is healthy" if is_healthy else "API is not healthy"
        }

        # You can include details per your JS client needs
        return jsonify(response), 200 if is_healthy else 503

    return app

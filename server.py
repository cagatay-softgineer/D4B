from flask import Flask
import argparse
from database.into_redis import clone_postgres_to_redis
from util.loading_sequence import main_starship_check
from util.app import create_app
from datetime import datetime, timezone

if __name__ == "__main__":

    start_time = datetime.now(timezone.utc)

    main_starship_check()
    clone_postgres_to_redis()

    parser = argparse.ArgumentParser(
        description="Run Flask on a specific port.")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the Flask app."
    )
    args = parser.parse_args()
    app = Flask(__name__)
    app = create_app(app, start_time)
    # app.run(
    #     host="0.0.0.0", port=args.port
    # )
    # Create OpenSSH certificates for HTTPS
    app.run(
        host="0.0.0.0", port=args.port, ssl_context="adhoc"
    )

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from util.utils import obfuscate


def requires_scope(required_scope):
    """
    Decorator to enforce that a valid JWT is present and it contains the required scope.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify that the JWT exists in the request
            verify_jwt_in_request()
            claims = get_jwt()
            # Assume that the scopes are stored as a list in the "scopes"
            # claim.
            token_scopes = claims.get("scopes", [])
            # If scopes were added as a space-delimited string, split it:
            if isinstance(token_scopes, str):
                token_scopes = token_scopes.split()
            if required_scope not in token_scopes:
                return (
                    jsonify(
                        {
                            "error": "Missing required scope",
                            "required": f"{required_scope[:8]}_{obfuscate(required_scope)[:4]}",
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# All Scopes
all_scopes = [
    "maint",
    "user",
    "guest",
    "admin"]

default_user = ["guest"]

role_scopes = {
    "admin": ["admin", "maint", "user"],
    "maintenance": ["maint", "user"],
    "user": ["user"],
    "guest": ["guest"],
}

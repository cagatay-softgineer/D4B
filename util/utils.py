from datetime import datetime, timezone
from cmd_gui_kit import CmdGUI
import hashlib
from config.settings import settings
from database.postgres import check_database

OAUTHLIB_INSECURE_TRANSPORT = 1

# Initialize CmdGUI for visual feedback
gui = CmdGUI()


def obfuscate(column_name: str) -> str:
    """
    Obfuscates a given column name by hashing it with a salt value and returning the first 12 characters in uppercase.

    Parameters:
    column_name (str): The column name to be obfuscated.

    Returns:
    str: The obfuscated column name, consisting of the first 12 characters of the hashed value in uppercase.
    """
    salt = settings.SALT  # Replace with your own secret salt value.
    hash_value = hashlib.sha256(
        (salt + column_name).encode("utf-8")).hexdigest()
    return f"{hash_value[:12].upper()}"


def get_email_username(email: str) -> str:
    """
    Extracts and returns the part of an email address before the '@' symbol.

    Parameters:
        email (str): The email address.

    Returns:
        str: The part of the email before the '@'. Returns None if '@' is not found.
    """
    if "@" in email:
        return email.split("@")[0]
    else:
        return None

def health_check():
    start_time = datetime.now(timezone.utc)

    # Basic status (add more checks as needed)
    _ = check_database()

    # You can include details per your JS client needs
    return int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

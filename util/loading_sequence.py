import random
from mailjet_rest import Client
import sys
import time
import os
from colorama import init
from pydantic import ValidationError
from database.into_redis import clone_postgres_to_redis
from database.postgres import check_database as checkDB
from util.braille.logo import render_image_as_braille_banner
from util.braille.progress_bar import animate_multiple_braille_bars
from util.logit import get_logger
from config.settings import (
    settings,
    PostgresSettings,
    RedisSettings,
    SQLiteSettings,
    MySQLSettings,
    MongoSettings,
    FirebaseSettings,
    SMTPSettings,
)

init(autoreset=True)

logger = get_logger("logs", "Loading Services")


def clear_output():
    os.system("cls" if os.name == "nt" else "clear")


COLORSET = [
    "\033[91m",  # Red
    "\033[92m",  # Green
    "\033[93m",  # Yellow
    "\033[94m",  # Blue
    "\033[95m",  # Magenta
    "\033[96m",  # Cyan
    "\033[97m",  # White
    "\033[90m",  # Bright Black (Gray)
]
RESET = "\033[0m"
COLS = 80
LINE_COUNT = 5

# Define various pattern sets
PATTERN_SETS = [
    # ['\\', '/'],
    # ['─', '│', '┌', '┐', '└', '┘', '┼', '├', '┤', '┬', '┴'],
    [chr(i) for i in range(0x2800, 0x28FF)],  # Braille
]


def print_pattern(lines=LINE_COUNT, cols=COLS):
    for _ in range(lines):
        # Randomly choose a pattern for this line
        pattern_chars = random.choice(PATTERN_SETS)
        for _ in range(cols):
            char = random.choice(pattern_chars)
            color = random.choice(COLORSET)
            sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.write("\n")
    sys.stdout.flush()


COLORS = {
    "ok": "\033[92m",  # Green
    "fail": "\033[91m",  # Red
    "warn": "\033[93m",  # Yellow
    "info": "\033[96m",  # Cyan
    "title": "\033[95m",  # Magenta
    "reset": "\033[0m",
    "label": "\033[97m",  # White
}
SPINNER = ["|", "/", "-", "\\"]
RESET = COLORS["reset"]

BANNER = r"""
        ____________________________________________________
       |                                                    |
       |  🚀   D4B Starship - System Startup Sequence   🚀  |
       |____________________________________________________|
"""

SYSTEMS = [
    {"name": "Database", "type": "critical", "check": lambda: check_database()},
    {"name": "Cache/Redis", "type": "core", "check": lambda: check_redis()},
    {"name": "Cloud Storage", "type": "core", "check": lambda: check_storage()},
    {"name": "Email Service", "type": "optional", "check": lambda: check_email()},
    {
        "name": "Notification Service",
        "type": "core",
        "check": lambda: check_notification(),
    },
    {
        "name": "Background Jobs",
        "type": "core",
        "check": lambda: check_background_jobs(),
    },
    {
        "name": "External APIs",
        "type": "optional",
        "check": lambda: check_external_apis(),
    },
    {
        "name": "Security & Secrets",
        "type": "critical",
        "check": lambda: check_secrets(),
    },
    {"name": "Logger & Audit", "type": "core", "check": lambda: check_logger()},
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    print("\n")
    print(COLORS["title"] + BANNER + RESET)
    print("\n")


def animated_check(name, status="OK", duration=0.8, label_color=None):
    if not label_color:
        label_color = COLORS["label"]
    spinner_idx = 0
    start = time.time()
    while time.time() - start < duration:
        sys.stdout.write(
            f"\r{label_color}[{SPINNER[spinner_idx % len(SPINNER)]}] {name} ... "
        )
        sys.stdout.flush()
        spinner_idx += 1
        time.sleep(0.07)
    sys.stdout.write("\r")
    if status == "OK":
        sys.stdout.write(f"{label_color}[✓] {name:<22} {COLORS['ok']}OK{RESET}\n")
    elif status == "WARN":
        sys.stdout.write(f"{label_color}[!] {name:<22} {COLORS['warn']}WARN{RESET}\n")
    else:
        sys.stdout.write(f"{label_color}[X] {name:<22} {COLORS['fail']}FAIL{RESET}\n")
    sys.stdout.flush()
    time.sleep(0.05)


# -------------------------------------------
# Implement these check functions for your real environment!
# Return "OK", "WARN", or "FAIL"
def check_database():
    # Example: PostgreSQL ping
    try:
        if checkDB():
            return "OK"
        else:
            return "FAIL"
    except Exception:
        return "FAIL"


def check_redis():
    # Example: Try import and ping redis
    try:
        import redis

        r = redis.StrictRedis(
            host="localhost", port=6379, db=0, socket_connect_timeout=2
        )
        r.ping()
        return "OK"
    except Exception:
        return "FAIL"


def check_storage():
    # Example: Google Cloud Storage or local storage check
    try:
        # from google.cloud import storage
        # storage.Client()...
        return "OK"  # or "WARN" if partial
    except Exception:
        return "FAIL"


def check_email():
    """
    Mailjet health check via the mailjet_rest Client.
    Calls GET /v3/REST/contactmetadata and returns:
      - "OK"   if status_code == 200
      - "WARN" if 200 < status_code < 300
      - "FAIL" otherwise, or on exception
    """
    smtp = SMTPSettings()
    if not smtp.ID or not smtp.SECRET:
        logger.error(
            "Missing Mailjet credentials (MJ_APIKEY_PUBLIC / MJ_APIKEY_PRIVATE)"
        )
        return "FAIL"

    try:
        mailjet = Client(auth=(smtp.ID, smtp.SECRET), version="v3")
        # The wrapper exposes the resource as .contactmetadata
        res = mailjet.contactmetadata.get()
        code = res.status_code

        if code == 200:
            return "OK"
        elif 200 < code < 300:
            logger.warning(f"Mailjet health returned {code}")
            return "WARN"
        else:
            logger.error(f"Mailjet health failed with code {code}")
            return "FAIL"

    except Exception:
        logger.exception("Mailjet health check exception")
        return "FAIL"


def check_notification():
    try:
        # Custom notification provider logic
        return "OK"
    except Exception:
        return "WARN"


def check_background_jobs():
    try:
        # e.g. ping Celery, RQ, etc.
        return "OK"
    except Exception:
        return "WARN"


def check_external_apis():
    try:
        # Ping an external API you depend on
        return "OK"
    except Exception:
        return "WARN"


def check_secrets():
    """
    Validate that all required environment‐backed settings are present:
      - AppSettings (JWT_SECRET_KEY, SALT, etc.)
      - The chosen DB backend (POSTGRES, REDIS, SQLITE, MYSQL, MONGODB or FIREBASE)
      - SMTP credentials
    Returns "OK" if all settings validate, else "FAIL".
    """
    try:
        # 1) Core app settings are already loaded into `settings`
        #    Pydantic would have raised on missing JWT_SECRET_KEY or SALT at import time.
        #    We trust `settings` here, but you could re-validate if desired.

        # 2) Validate the configured database settings
        if settings.DATABASE_URL:
            # One-URL fallback—no further check
            pass
        else:
            db_type = settings.DB_TYPE.lower()
            if db_type == "postgres":
                PostgresSettings()
            elif db_type == "redis":
                RedisSettings()
            elif db_type == "sqlite":
                SQLiteSettings()
            elif db_type == "mysql":
                MySQLSettings()
            elif db_type in ("mongodb", "mongo"):
                MongoSettings()
            elif db_type == "firebase":
                FirebaseSettings()
            else:
                logger.error(f"Unknown DB_TYPE: {settings.DB_TYPE!r}")
                return "FAIL"

        # 3) Validate SMTP settings
        SMTPSettings()

        # If we got this far, everything required is present
        return "OK"

    except ValidationError as e:
        # One of the BaseSettings was missing a required field or had invalid type
        logger.error("Configuration validation error", exc_info=e)
        return "FAIL"
    except Exception as e:
        # Any other unexpected problem
        logger.exception("Unexpected error during secrets/config validation", e)
        return "FAIL"


def check_logger():
    """Test writing to your log system."""
    try:
        logger.debug("Logger health check")
        # Flush any handlers to force I/O
        for handler in logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass
        return "OK"
    except Exception:
        logger.exception("Logger health check failed")
        return "FAIL"


# -------------------------------------------
SYSTEMS = [
    {"name": "Database",             "type": "critical", "check": check_database},
    {"name": "Cache/Redis",          "type": "core",     "check": check_redis},
    {"name": "Cloud Storage",        "type": "core",     "check": check_storage},
    {"name": "Email Service",        "type": "optional", "check": check_email},
    {"name": "Notification Service", "type": "core",     "check": check_notification},
    {"name": "Background Jobs",      "type": "core",     "check": check_background_jobs},
    {"name": "External APIs",        "type": "optional", "check": check_external_apis},
    {"name": "Security & Secrets",   "type": "critical", "check": check_secrets},
    {"name": "Logger & Audit",       "type": "core",     "check": check_logger},
]

# ── Main startup sequence ──────────────────────────────────────────────────────

def main_starship_check():
    clear_output()
    # Path to your logo image (PNG preferred):
    logo_path = os.path.join(os.path.dirname(__file__), "braille", "logo", "db.png")
    font_path = os.path.join(os.path.dirname(__file__), "braille", "fonts", "DejaVuSansMono.ttf")
    render_image_as_braille_banner(logo_path, banner_width=190, logo_and_banner_split_size=10, logo_cols=40, title_cols=150, title_text="Dörtyöl Belediyesi", threshold=240, invert=True, dither=False, border=False, title_font_path=font_path)
    time.sleep(5.0)
    clear_output()
    sys.stdout.write("\nInitializing D4B System Resources...\n\n")
    sys.stdout.flush()

    # 1) Run all checks
    system_status = []
    for s in SYSTEMS:
        res = s["check"]()
        system_status.append({
            "name": s["name"],
            "type": s["type"],
            "status": res
        })

    # 2) Animate all bars in parallel
    services = [
        {"name": ss["name"], "status": ss["status"], "target_progress": 1.0}
        for ss in system_status
    ]
    animate_multiple_braille_bars(services, bar_length=18, delay=0.04, min_frames=30, max_frames=90, finish_effect_frames=20)
    print()

    # 3) Summary and potential clone
    critical_failed = any(x["type"]=="critical" and x["status"]!="OK" for x in system_status)
    if critical_failed:
        print(f"\033[91mSystem Startup ABORTED: Critical systems FAILED.{RESET}")
        return system_status

    if any(x["status"]=="FAIL" for x in system_status):
        print(f"\033[93mStartup: Non‑critical failures. Limited functionality.{RESET}")
    elif any(x["status"]=="WARN" for x in system_status):
        print(f"\033[93mStartup: Warnings present. Monitor closely.{RESET}")
    else:
        print(f"\033[92mAll systems nominal. D4B LAUNCHED! 🚀{RESET}\n")

    # 4) Clone if Database & Redis OK
    db = next((x for x in system_status if x["name"]=="Database"), None)
    rd = next((x for x in system_status if x["name"]=="Cache/Redis"), None)
    if db and rd and db["status"]=="OK" and rd["status"]=="OK":
        clone_postgres_to_redis()
    else:
        print("\n\033[91mCRITICAL: Skipping clone_postgres_to_redis()—DB/Redis offline.\033[0m")

    return system_status

if __name__ == "__main__":
    main_starship_check()

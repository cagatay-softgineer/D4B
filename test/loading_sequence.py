import sys
import time
import os
from colorama import init
from database.postgres import get_connection

init(autoreset=True)

COLORS = {
    'ok': '\033[92m',        # Green
    'fail': '\033[91m',      # Red
    'warn': '\033[93m',      # Yellow
    'info': '\033[96m',      # Cyan
    'title': '\033[95m',     # Magenta
    'reset': '\033[0m',
    'label': '\033[97m',     # White
}
SPINNER = ["|", "/", "-", "\\"]
RESET = COLORS['reset']

BANNER = r"""
        ____________________________________________________
       |                                                    |
       |   🚀   D4B Starship - System Startup Sequence   🚀   |
       |____________________________________________________|
"""

SYSTEMS = [
    {"name": "Database", "type": "critical", "check": lambda: check_database()},
    {"name": "Cache/Redis", "type": "core", "check": lambda: check_redis()},
    {"name": "Cloud Storage", "type": "core", "check": lambda: check_storage()},
    {"name": "Email Service", "type": "optional", "check": lambda: check_email()},
    {"name": "Notification Service", "type": "core", "check": lambda: check_notification()},
    {"name": "Background Jobs", "type": "core", "check": lambda: check_background_jobs()},
    {"name": "External APIs", "type": "optional", "check": lambda: check_external_apis()},
    {"name": "Security & Secrets", "type": "critical", "check": lambda: check_secrets()},
    {"name": "Logger & Audit", "type": "core", "check": lambda: check_logger()},
]

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(COLORS['title'] + BANNER + RESET)

def animated_check(name, status="OK", duration=0.8, label_color=None):
    if not label_color:
        label_color = COLORS['label']
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
    time.sleep(0.12)

# -------------------------------------------
# Implement these check functions for your real environment!
# Return "OK", "WARN", or "FAIL"
def check_database():
    # Example: PostgreSQL ping
    try:
        get_connection()
        return "OK"
    except Exception:
        return "FAIL"

def check_redis():
    # Example: Try import and ping redis
    try:
        import redis
        r = redis.StrictRedis(host="localhost", port=6379, db=0, socket_connect_timeout=2)
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
    # Example: Try connecting to SMTP server or checking email config
    try:
        # import smtplib
        # ...
        return "OK"
    except Exception:
        return "WARN"

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
    try:
        # Ensure secrets/config are loaded
        return "OK"
    except Exception:
        return "FAIL"

def check_logger():
    try:
        # Try writing to your log file or system
        return "OK"
    except Exception:
        return "WARN"
# -------------------------------------------

def main_starship_check():
    clear()
    print_banner()
    sys.stdout.write("\nInitializing D4B System Resources...\n\n")
    sys.stdout.flush()
    system_status = []
    for s in SYSTEMS:
        result = s["check"]()
        animated_check(s["name"], status=result)
        system_status.append({"name": s["name"], "type": s["type"], "status": result})
    sys.stdout.write("\n")

    critical_failed = any(x["type"] == "critical" and x["status"] != "OK" for x in system_status)
    if critical_failed:
        print(f"{COLORS['fail']}System Startup ABORTED: One or more critical systems FAILED.{RESET}")
        sys.exit(1)
    elif any(x["status"] == "FAIL" for x in system_status):
        print(f"{COLORS['warn']}Startup: Some non-critical systems failed. Running with limited functionality.{RESET}")
    elif any(x["status"] == "WARN" for x in system_status):
        print(f"{COLORS['warn']}Startup: Some warnings present. Monitor systems closely.{RESET}")
    else:
        print(f"{COLORS['ok']}All systems nominal. D4B is LAUNCHED! 🚀{RESET}\n")

if __name__ == "__main__":
    main_starship_check()
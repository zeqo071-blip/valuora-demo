import os
from pathlib import Path

BASE = Path(__file__).parent
DEV_SECRET = "dev-secret-change-me"
SECRET = os.getenv("VALUORA_SECRET", DEV_SECRET)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
DB_PATH = os.getenv("VALUORA_DB", "./valuora.db")

if COOKIE_SECURE and SECRET == DEV_SECRET:
    raise RuntimeError("COOKIE_SECURE=1 olduqda VALUORA_SECRET məcburidir")

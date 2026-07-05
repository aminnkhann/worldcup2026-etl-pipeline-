import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

# ── football-data.org ──────────────────────────────────────────
API_KEY  = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
HEADERS  = {"X-Auth-Token": API_KEY}
WC_CODE  = os.getenv("WC_CODE", "WC")

# ── PostgreSQL ────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "worldcup2026"),
    "user":     os.getenv("DB_USER", "worldcup"),
    "password": os.getenv("DB_PASSWORD", ""),
}

if not API_KEY:
    raise ValueError("FOOTBALL_API_KEY is missing. Add it to your .env file.")

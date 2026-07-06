import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

load_dotenv(ENV_PATH)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str
    wc_code: str
    request_delay: int
    scorers_limit: int
    football_data_season: str | None
    fetch_match_details: bool
    store_raw_responses: bool
    raw_data_dir: Path
    db_config: dict[str, Any]


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("FOOTBALL_API_KEY"),
        base_url=os.getenv("FOOTBALL_BASE_URL", "https://api.football-data.org/v4"),
        wc_code=os.getenv("WC_CODE", "WC"),
        request_delay=_env_int("REQUEST_DELAY", 6),
        scorers_limit=_env_int("SCORERS_LIMIT", 1000),
        football_data_season=os.getenv("FOOTBALL_DATA_SEASON"),
        fetch_match_details=_env_bool("FETCH_MATCH_DETAILS", True),
        store_raw_responses=_env_bool("STORE_RAW_RESPONSES", True),
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", DEFAULT_RAW_DATA_DIR)),
        db_config={
            "host": os.getenv("DB_HOST", "localhost"),
            "port": _env_int("DB_PORT", 5432),
            "dbname": os.getenv("DB_NAME", "worldcup2026"),
            "user": os.getenv("DB_USER", "worldcup"),
            "password": os.getenv("DB_PASSWORD", ""),
        },
    )


def football_headers(settings: Settings | None = None) -> dict[str, str]:
    settings = settings or get_settings()
    return {"X-Auth-Token": settings.api_key or ""}


def match_detail_headers(settings: Settings | None = None) -> dict[str, str]:
    return {
        **football_headers(settings),
        "X-Unfold-Lineups": "true",
        "X-Unfold-Bookings": "true",
        "X-Unfold-Subs": "true",
        "X-Unfold-Goals": "true",
    }


def validate_runtime_config(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    missing = []
    if not settings.api_key:
        missing.append("FOOTBALL_API_KEY")
    for env_name, value in (
        ("DB_HOST", settings.db_config["host"]),
        ("DB_PORT", settings.db_config["port"]),
        ("DB_NAME", settings.db_config["dbname"]),
        ("DB_USER", settings.db_config["user"]),
    ):
        if value in (None, ""):
            missing.append(env_name)
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Missing required runtime configuration: {names}.")

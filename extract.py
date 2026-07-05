"""
extract.py - HTTP access to the football-data.org API.

All functions here return raw JSON structures exactly as the API
returns them; no reshaping happens here (see transform.py for that).
"""

import logging
import os
import time
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import BASE_URL, HEADERS, WC_CODE

logger = logging.getLogger(__name__)

REQUEST_DELAY = int(os.getenv("REQUEST_DELAY", "6"))
SCORERS_LIMIT = int(os.getenv("SCORERS_LIMIT", "1000"))
FOOTBALL_DATA_SEASON = os.getenv("FOOTBALL_DATA_SEASON")
FETCH_MATCH_DETAILS = os.getenv("FETCH_MATCH_DETAILS", "true").lower() in {"1", "true", "yes", "on"}

MATCH_DETAIL_HEADERS = {
    **HEADERS,
    "X-Unfold-Lineups": "true",
    "X-Unfold-Bookings": "true",
    "X-Unfold-Subs": "true",
    "X-Unfold-Goals": "true",
}


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


_SESSION = _make_session()


def _get(endpoint: str, *, headers: dict | None = None) -> dict:
    url = f"{BASE_URL}{endpoint}"
    logger.info("GET %s", url)
    last_exc = None
    for attempt in range(1, 6):
        try:
            response = _SESSION.get(url, headers=headers or HEADERS, timeout=30)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited - waiting %ds", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return response.json()
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            wait = 2 ** attempt
            logger.warning("Network error attempt %d/5 - retrying in %ds: %s", attempt, wait, exc)
            time.sleep(wait)
    raise RuntimeError(f"Failed to GET {url} after 5 attempts: {last_exc}")


def _competition_params(extra: dict | None = None) -> str:
    params = {}
    if FOOTBALL_DATA_SEASON:
        params["season"] = FOOTBALL_DATA_SEASON
    if extra:
        params.update(extra)
    return f"?{urlencode(params)}" if params else ""


def fetch_matches() -> list:
    endpoint = f"/competitions/{WC_CODE}/matches{_competition_params()}"
    return _get(endpoint, headers=MATCH_DETAIL_HEADERS).get("matches", [])


def fetch_match_detail(match_id: int) -> dict:
    payload = _get(f"/matches/{match_id}", headers=MATCH_DETAIL_HEADERS)
    return payload.get("match") or payload


def fetch_teams() -> list:
    endpoint = f"/competitions/{WC_CODE}/teams{_competition_params()}"
    return _get(endpoint).get("teams", [])


def fetch_standings() -> list:
    endpoint = f"/competitions/{WC_CODE}/standings{_competition_params()}"
    return _get(endpoint).get("standings", [])


def fetch_scorers(limit: int = SCORERS_LIMIT) -> list:
    endpoint = f"/competitions/{WC_CODE}/scorers{_competition_params({'limit': limit})}"
    try:
        return _get(endpoint).get("scorers", [])
    except requests.exceptions.HTTPError:
        if limit > 100:
            logger.warning("Scorers limit=%s failed; retrying with limit=100", limit)
            return fetch_scorers(100)
        raise


def fetch_squad(team_id: int) -> dict:
    return _get(f"/teams/{team_id}")


def enrich_match_details(raw_matches: list) -> list:
    if not FETCH_MATCH_DETAILS:
        logger.info("Skipping per-match detail fetch because FETCH_MATCH_DETAILS=false")
        return raw_matches

    enriched = []
    for idx, match in enumerate(raw_matches, start=1):
        match_id = match.get("id")
        if match_id is None:
            enriched.append(match)
            continue
        logger.info("Match detail %d/%d - match_id=%s", idx, len(raw_matches), match_id)
        detail = fetch_match_detail(match_id)
        merged = {**match, **detail}
        enriched.append(merged)
    return enriched

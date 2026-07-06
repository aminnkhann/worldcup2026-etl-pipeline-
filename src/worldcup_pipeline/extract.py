"""
HTTP access to the football-data.org API.

All functions here return raw JSON structures exactly as the API returns
them; no reshaping happens here. Optional raw-response staging writes API
payloads to local JSON files for auditability without changing the database.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings, football_headers, get_settings, match_detail_headers

logger = logging.getLogger(__name__)


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


def _safe_endpoint_name(endpoint: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", endpoint).strip("_")
    return name or "root"


def _stage_raw_response(endpoint: str, payload: dict, settings: Settings) -> None:
    if not settings.store_raw_responses:
        return

    fetched_at = datetime.now(UTC).isoformat()
    filename = f"{fetched_at.replace(':', '').replace('+', 'Z')}_{_safe_endpoint_name(endpoint)}.json"
    envelope = {
        "fetched_at": fetched_at,
        "endpoint": endpoint,
        "payload": payload,
    }
    try:
        settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
        (settings.raw_data_dir / filename).write_text(
            json.dumps(envelope, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not stage raw API response for %s: %s", endpoint, exc)


def _get(endpoint: str, *, headers: dict[str, str] | None = None) -> dict:
    settings = get_settings()
    url = f"{settings.base_url}{endpoint}"
    logger.info("GET %s", url)
    last_exc = None
    for attempt in range(1, 6):
        try:
            response = _SESSION.get(url, headers=headers or football_headers(settings), timeout=30)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited - waiting %ds", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            payload = response.json()
            _stage_raw_response(endpoint, payload, settings)
            time.sleep(settings.request_delay)
            return payload
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning("Network error attempt %d/5 - retrying in %ds: %s", attempt, wait, exc)
            time.sleep(wait)
    raise RuntimeError(f"Failed to GET {url} after 5 attempts: {last_exc}")


def _competition_params(settings: Settings, extra: dict | None = None) -> str:
    params = {}
    if settings.football_data_season:
        params["season"] = settings.football_data_season
    if extra:
        params.update(extra)
    return f"?{urlencode(params)}" if params else ""


def fetch_matches() -> list:
    settings = get_settings()
    endpoint = f"/competitions/{settings.wc_code}/matches{_competition_params(settings)}"
    return _get(endpoint, headers=match_detail_headers(settings)).get("matches", [])


def fetch_match_detail(match_id: int) -> dict:
    payload = _get(f"/matches/{match_id}", headers=match_detail_headers())
    return payload.get("match") or payload


def fetch_teams() -> list:
    settings = get_settings()
    endpoint = f"/competitions/{settings.wc_code}/teams{_competition_params(settings)}"
    return _get(endpoint).get("teams", [])


def fetch_standings() -> list:
    settings = get_settings()
    endpoint = f"/competitions/{settings.wc_code}/standings{_competition_params(settings)}"
    return _get(endpoint).get("standings", [])


def fetch_scorers(limit: int | None = None) -> list:
    settings = get_settings()
    limit = limit or settings.scorers_limit
    endpoint = f"/competitions/{settings.wc_code}/scorers{_competition_params(settings, {'limit': limit})}"
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
    settings = get_settings()
    if not settings.fetch_match_details:
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

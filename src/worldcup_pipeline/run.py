"""
FIFA World Cup 2026 ETL: football-data.org -> PostgreSQL.

Two modes:

  python run.py              full sync: dimensions (teams, players) + facts
  python run.py --facts-only facts only, with minimal FK-safe dimensions
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import validate_runtime_config
from .extract import (
    enrich_match_details,
    fetch_matches,
    fetch_scorers,
    fetch_squad,
    fetch_standings,
    fetch_teams,
)
from .load import (
    apply_schema,
    load_group_standings,
    load_matches,
    load_players,
    load_teams,
    load_top_scorers,
)
from .quality import validate_dimensions, validate_facts
from .run_tracking import RunTracker
from .transform import build_group_standings, build_matches, build_players, build_teams, build_top_scorers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _teams_from_standings(raw_standings: list) -> list[dict]:
    teams = []
    for block in raw_standings:
        for entry in block.get("table", []):
            team = entry.get("team") or {}
            if team.get("id") is not None:
                teams.append(team)
    return teams


def _ids(rows: list[dict], key: str) -> set[int]:
    return {row[key] for row in rows if row.get(key) is not None}


def sync_dimensions(raw_matches: list, raw_scorers: list) -> tuple[list, list]:
    raw_teams = fetch_teams()
    seed_teams = build_teams(raw_teams, raw_matches, raw_scorers, {})
    team_ids = sorted({t["team_id"] for t in seed_teams if t["team_id"] is not None})

    logger.info("Fetching squads for %d teams", len(team_ids))
    squad_payloads: dict[int, dict] = {}
    for idx, team_id in enumerate(team_ids, start=1):
        logger.info("Squad %d/%d - team_id=%s", idx, len(team_ids), team_id)
        squad_payloads[team_id] = fetch_squad(team_id)

    teams = build_teams(raw_teams, raw_matches, raw_scorers, squad_payloads)
    players = build_players(squad_payloads, raw_scorers)
    validate_dimensions(teams, players)

    load_teams(teams)
    load_players(players)
    return teams, players


def sync_minimal_dimensions(raw_matches: list, raw_standings: list, raw_scorers: list) -> tuple[list, list]:
    raw_teams = _teams_from_standings(raw_standings)
    teams = build_teams(raw_teams, raw_matches, raw_scorers, {})
    players = build_players({}, raw_scorers)
    validate_dimensions(teams, players)

    logger.info("facts-only run - loading minimal FK-safe teams/players without squad refresh")
    load_teams(teams)
    load_players(players)
    return teams, players


def sync_facts(
    raw_matches: list,
    raw_standings: list,
    raw_scorers: list,
    *,
    team_ids: set[int],
    player_ids: set[int],
) -> tuple[list, list, list]:
    matches = build_matches(raw_matches)
    standings = build_group_standings(raw_standings)
    scorers = build_top_scorers(raw_scorers)
    validate_facts(matches, standings, scorers, team_ids=team_ids, player_ids=player_ids)

    load_matches(matches)
    load_group_standings(standings)
    load_top_scorers(scorers)
    return matches, standings, scorers


def run(facts_only: bool = False) -> None:
    mode = "facts-only" if facts_only else "full"
    tracker = RunTracker(mode=mode)
    counts: dict[str, int] = {}

    try:
        validate_runtime_config()

        logger.info("=" * 60)
        logger.info("FIFA World Cup 2026 - pipeline starting (mode=%s)", mode)
        logger.info("=" * 60)

        apply_schema()

        raw_matches = enrich_match_details(fetch_matches())
        raw_standings = fetch_standings()
        raw_scorers = fetch_scorers()

        if facts_only:
            teams, players = sync_minimal_dimensions(raw_matches, raw_standings, raw_scorers)
        else:
            teams, players = sync_dimensions(raw_matches, raw_scorers)

        matches, standings, scorers = sync_facts(
            raw_matches,
            raw_standings,
            raw_scorers,
            team_ids=_ids(teams, "team_id"),
            player_ids=_ids(players, "player_id"),
        )

        finished = [m for m in raw_matches if m.get("status") == "FINISHED"]
        counts = {
            "teams": len(teams),
            "players": len(players),
            "matches": len(matches),
            "finished_matches": len(finished),
            "standings": len(standings),
            "scorers": len(scorers),
        }
        tracker.finish("success", counts)

        logger.info("=" * 60)
        logger.info("Pipeline complete")
        logger.info(
            "Teams: %d | Players: %d | Matches: %d (%d finished) | Standings rows: %d | Scorer rows: %d",
            counts["teams"],
            counts["players"],
            counts["matches"],
            counts["finished_matches"],
            counts["standings"],
            counts["scorers"],
        )
        logger.info("=" * 60)
    except Exception as exc:
        tracker.finish("failed", counts, error=str(exc))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 ETL pipeline")
    parser.add_argument(
        "--facts-only",
        action="store_true",
        help="skip squad refresh and only refresh FK-safe fact tables",
    )
    args = parser.parse_args()
    run(facts_only=args.facts_only)


if __name__ == "__main__":
    main()

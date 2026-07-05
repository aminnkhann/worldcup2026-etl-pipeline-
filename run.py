"""
run.py - FIFA World Cup 2026 ETL: football-data.org -> PostgreSQL.

Orchestrates extract.py / transform.py / load.py. Two modes:

  python run.py              full sync: dimensions (teams, players) + facts
  python run.py --facts-only facts only (matches, standings, top scorers)

Dimensions (teams/players/squads) rarely change once the tournament has
started, and re-fetching a squad per team is the slowest, most
rate-limit-sensitive part of a run. --facts-only skips that and only
refreshes the tables that actually change every matchday.
"""

import argparse
import logging
import sys

from extract import (
    enrich_match_details,
    fetch_matches,
    fetch_scorers,
    fetch_squad,
    fetch_standings,
    fetch_teams,
)
from load import (
    apply_schema,
    load_group_standings,
    load_matches,
    load_players,
    load_teams,
    load_top_scorers,
)
from transform import build_group_standings, build_matches, build_players, build_teams, build_top_scorers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run")


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

    load_teams(teams)
    load_players(players)
    return teams, players


def sync_facts(raw_matches: list, raw_standings: list, raw_scorers: list) -> tuple[list, list, list]:
    matches = build_matches(raw_matches)
    standings = build_group_standings(raw_standings)
    scorers = build_top_scorers(raw_scorers)

    load_matches(matches)
    load_group_standings(standings)
    load_top_scorers(scorers)
    return matches, standings, scorers


def run(facts_only: bool = False):
    logger.info("=" * 60)
    logger.info("FIFA World Cup 2026 - pipeline starting (facts_only=%s)", facts_only)
    logger.info("=" * 60)

    apply_schema()

    raw_matches = enrich_match_details(fetch_matches())
    raw_standings = fetch_standings()
    raw_scorers = fetch_scorers()

    teams, players = ([], [])
    if facts_only:
        logger.info("facts-only run - skipping team/squad refresh")
    else:
        teams, players = sync_dimensions(raw_matches, raw_scorers)

    matches, standings, scorers = sync_facts(raw_matches, raw_standings, raw_scorers)

    finished = [m for m in raw_matches if m.get("status") == "FINISHED"]
    logger.info("=" * 60)
    logger.info("Pipeline complete")
    logger.info(
        "Teams: %d | Players: %d | Matches: %d (%d finished) | Standings rows: %d | Scorer rows: %d",
        len(teams),
        len(players),
        len(raw_matches),
        len(finished),
        len(standings),
        len(scorers),
    )
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 ETL pipeline")
    parser.add_argument(
        "--facts-only",
        action="store_true",
        help="skip teams/players (dimensions) and only refresh matches/standings/scorers (facts)",
    )
    args = parser.parse_args()
    run(facts_only=args.facts_only)


if __name__ == "__main__":
    main()

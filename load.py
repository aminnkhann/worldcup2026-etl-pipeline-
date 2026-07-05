"""
load.py - apply schema.sql and upsert row dicts into PostgreSQL.

Every load_* function takes the row dicts produced by transform.py and
upserts them with ON CONFLICT ... DO UPDATE, so re-running the pipeline
is always safe.
"""

import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG
from transform import _json

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _connect():
    return psycopg2.connect(**DB_CONFIG)


def apply_schema():
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info("Schema applied")
    finally:
        conn.close()


def _upsert(sql: str, rows: list[tuple], table: str):
    if not rows:
        logger.info("No rows to load into %s", table)
        return
    conn = _connect()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows, page_size=500)
        conn.commit()
        logger.info("Upserted %d rows into %s", len(rows), table)
    except Exception:
        conn.rollback()
        logger.exception("Failed loading %s", table)
        raise
    finally:
        conn.close()


def load_teams(rows: list[dict]):
    records = [
        (
            r["team_id"], r["team_name"], r["short_name"], r["tla"], r["group_name"],
            r["country_name"], r["country_code"], r["flag_url"], r["crest_url"],
            r["area_id"], r["area_name"], r["area_code"], r["area_flag"], r["address"],
            r["website"], r["founded"], r["club_colors"], r["venue"], r["coach_id"],
            r["coach_name"], r["coach_nationality"], r["last_updated"], _json(r["raw_team"]),
            _json(r["raw_area"]), _json(r["raw_coach"]), _json(r["raw_squad"]),
            _json(r["raw_running_competitions"]),
        )
        for r in rows
    ]
    sql = """
    INSERT INTO teams (
        team_id, team_name, short_name, tla, group_name,
        country_name, country_code, flag_url, crest_url,
        area_id, area_name, area_code, area_flag, address, website, founded,
        club_colors, venue, coach_id, coach_name, coach_nationality, last_updated,
        raw_team, raw_area, raw_coach, raw_squad, raw_running_competitions
    )
    VALUES %s
    ON CONFLICT (team_id) DO UPDATE SET
        team_name = EXCLUDED.team_name,
        short_name = EXCLUDED.short_name,
        tla = EXCLUDED.tla,
        group_name = COALESCE(EXCLUDED.group_name, teams.group_name),
        country_name = EXCLUDED.country_name,
        country_code = EXCLUDED.country_code,
        flag_url = EXCLUDED.flag_url,
        crest_url = EXCLUDED.crest_url,
        area_id = EXCLUDED.area_id,
        area_name = EXCLUDED.area_name,
        area_code = EXCLUDED.area_code,
        area_flag = EXCLUDED.area_flag,
        address = EXCLUDED.address,
        website = EXCLUDED.website,
        founded = EXCLUDED.founded,
        club_colors = EXCLUDED.club_colors,
        venue = EXCLUDED.venue,
        coach_id = EXCLUDED.coach_id,
        coach_name = EXCLUDED.coach_name,
        coach_nationality = EXCLUDED.coach_nationality,
        last_updated = EXCLUDED.last_updated,
        raw_team = EXCLUDED.raw_team,
        raw_area = EXCLUDED.raw_area,
        raw_coach = EXCLUDED.raw_coach,
        raw_squad = EXCLUDED.raw_squad,
        raw_running_competitions = EXCLUDED.raw_running_competitions,
        updated_at = NOW()
    """
    _upsert(sql, records, "teams")


def load_players(rows: list[dict]):
    records = [
        (
            r["player_id"], r["player_name"], r["first_name"], r["last_name"], r["position"],
            r["date_of_birth"], r["country_of_birth"], r["nationality"], r["shirt_number"],
            r["last_updated"], r["team_id"], r["contract_start"], r["contract_until"],
            r["source"], _json(r["raw_player"]), _json(r["raw_current_team"]), _json(r["raw_contract"]),
        )
        for r in rows if r["player_id"] is not None
    ]
    sql = """
    INSERT INTO players (
        player_id, player_name, first_name, last_name, position, date_of_birth,
        country_of_birth, nationality, shirt_number, last_updated, team_id,
        contract_start, contract_until, source, raw_player, raw_current_team, raw_contract
    )
    VALUES %s
    ON CONFLICT (player_id) DO UPDATE SET
        player_name = EXCLUDED.player_name,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        position = EXCLUDED.position,
        date_of_birth = EXCLUDED.date_of_birth,
        country_of_birth = EXCLUDED.country_of_birth,
        nationality = EXCLUDED.nationality,
        shirt_number = EXCLUDED.shirt_number,
        last_updated = EXCLUDED.last_updated,
        team_id = EXCLUDED.team_id,
        contract_start = EXCLUDED.contract_start,
        contract_until = EXCLUDED.contract_until,
        source = EXCLUDED.source,
        raw_player = EXCLUDED.raw_player,
        raw_current_team = EXCLUDED.raw_current_team,
        raw_contract = EXCLUDED.raw_contract,
        updated_at = NOW()
    """
    _upsert(sql, records, "players")


def load_matches(rows: list[dict]):
    records = [
        (
            r["match_id"], r["status"], r["matchday"], r["stage"], r["group_name"], r["utc_date"],
            r["match_date"], r["home_team_id"], r["away_team_id"], r["winner_team_id"], r["venue_name"],
            r["home_score_ft"], r["away_score_ft"], r["home_score_ht"], r["away_score_ht"],
            r["total_goals"], r["referee_name"], r["referee_nationality"],
            r["area_id"], r["area_name"], r["competition_id"], r["competition_name"], r["competition_code"],
            r["season_id"], r["season_start_date"], r["season_end_date"], r["current_matchday"],
            r["score_winner"], r["score_duration"], r["home_score_regular"], r["away_score_regular"],
            r["home_score_extra"], r["away_score_extra"], r["home_score_penalties"], r["away_score_penalties"],
            r["minute"], r["injury_time"], r["attendance"], r["last_updated"], r["referees_count"],
            r["goals_count"], r["bookings_count"], r["substitutions_count"], r["penalties_count"],
            r["home_formation"], r["away_formation"], _json(r["raw_match"]), _json(r["raw_area"]),
            _json(r["raw_competition"]), _json(r["raw_season"]), _json(r["raw_score"]),
            _json(r["raw_home_team"]), _json(r["raw_away_team"]), _json(r["raw_referees"]),
            _json(r["raw_goals"]), _json(r["raw_bookings"]), _json(r["raw_substitutions"]),
            _json(r["raw_penalties"]), _json(r["raw_odds"]),
        )
        for r in rows
    ]
    sql = """
    INSERT INTO matches (
        match_id, status, matchday, stage, group_name, utc_date, match_date,
        home_team_id, away_team_id, winner_team_id, venue_name,
        home_score_ft, away_score_ft, home_score_ht, away_score_ht,
        total_goals, referee_name, referee_nationality,
        area_id, area_name, competition_id, competition_name, competition_code,
        season_id, season_start_date, season_end_date, current_matchday,
        score_winner, score_duration, home_score_regular, away_score_regular,
        home_score_extra, away_score_extra, home_score_penalties, away_score_penalties,
        minute, injury_time, attendance, last_updated, referees_count,
        goals_count, bookings_count, substitutions_count, penalties_count,
        home_formation, away_formation, raw_match, raw_area, raw_competition,
        raw_season, raw_score, raw_home_team, raw_away_team, raw_referees,
        raw_goals, raw_bookings, raw_substitutions, raw_penalties, raw_odds
    )
    VALUES %s
    ON CONFLICT (match_id) DO UPDATE SET
        status = EXCLUDED.status,
        matchday = EXCLUDED.matchday,
        stage = EXCLUDED.stage,
        group_name = EXCLUDED.group_name,
        utc_date = EXCLUDED.utc_date,
        match_date = EXCLUDED.match_date,
        home_team_id = EXCLUDED.home_team_id,
        away_team_id = EXCLUDED.away_team_id,
        winner_team_id = EXCLUDED.winner_team_id,
        venue_name = EXCLUDED.venue_name,
        home_score_ft = EXCLUDED.home_score_ft,
        away_score_ft = EXCLUDED.away_score_ft,
        home_score_ht = EXCLUDED.home_score_ht,
        away_score_ht = EXCLUDED.away_score_ht,
        total_goals = EXCLUDED.total_goals,
        referee_name = EXCLUDED.referee_name,
        referee_nationality = EXCLUDED.referee_nationality,
        area_id = EXCLUDED.area_id,
        area_name = EXCLUDED.area_name,
        competition_id = EXCLUDED.competition_id,
        competition_name = EXCLUDED.competition_name,
        competition_code = EXCLUDED.competition_code,
        season_id = EXCLUDED.season_id,
        season_start_date = EXCLUDED.season_start_date,
        season_end_date = EXCLUDED.season_end_date,
        current_matchday = EXCLUDED.current_matchday,
        score_winner = EXCLUDED.score_winner,
        score_duration = EXCLUDED.score_duration,
        home_score_regular = EXCLUDED.home_score_regular,
        away_score_regular = EXCLUDED.away_score_regular,
        home_score_extra = EXCLUDED.home_score_extra,
        away_score_extra = EXCLUDED.away_score_extra,
        home_score_penalties = EXCLUDED.home_score_penalties,
        away_score_penalties = EXCLUDED.away_score_penalties,
        minute = EXCLUDED.minute,
        injury_time = EXCLUDED.injury_time,
        attendance = EXCLUDED.attendance,
        last_updated = EXCLUDED.last_updated,
        referees_count = EXCLUDED.referees_count,
        goals_count = EXCLUDED.goals_count,
        bookings_count = EXCLUDED.bookings_count,
        substitutions_count = EXCLUDED.substitutions_count,
        penalties_count = EXCLUDED.penalties_count,
        home_formation = EXCLUDED.home_formation,
        away_formation = EXCLUDED.away_formation,
        raw_match = EXCLUDED.raw_match,
        raw_area = EXCLUDED.raw_area,
        raw_competition = EXCLUDED.raw_competition,
        raw_season = EXCLUDED.raw_season,
        raw_score = EXCLUDED.raw_score,
        raw_home_team = EXCLUDED.raw_home_team,
        raw_away_team = EXCLUDED.raw_away_team,
        raw_referees = EXCLUDED.raw_referees,
        raw_goals = EXCLUDED.raw_goals,
        raw_bookings = EXCLUDED.raw_bookings,
        raw_substitutions = EXCLUDED.raw_substitutions,
        raw_penalties = EXCLUDED.raw_penalties,
        raw_odds = EXCLUDED.raw_odds,
        updated_at = NOW()
    """
    _upsert(sql, records, "matches")


def load_group_standings(rows: list[dict]):
    records = [
        (
            r["group_name"], r["stage"], r["position"], r["team_id"], r["played"], r["won"],
            r["draw"], r["lost"], r["goals_for"], r["goals_against"], r["goal_difference"],
            r["points"], r["form"], _json(r["raw_standing"]), _json(r["raw_team"]),
        )
        for r in rows if r["team_id"] is not None
    ]
    sql = """
    INSERT INTO group_standings (
        group_name, stage, position, team_id, played, won, draw, lost,
        goals_for, goals_against, goal_difference, points,
        form, raw_standing, raw_team
    )
    VALUES %s
    ON CONFLICT (group_name, team_id) DO UPDATE SET
        stage = EXCLUDED.stage,
        position = EXCLUDED.position,
        played = EXCLUDED.played,
        won = EXCLUDED.won,
        draw = EXCLUDED.draw,
        lost = EXCLUDED.lost,
        goals_for = EXCLUDED.goals_for,
        goals_against = EXCLUDED.goals_against,
        goal_difference = EXCLUDED.goal_difference,
        points = EXCLUDED.points,
        form = EXCLUDED.form,
        raw_standing = EXCLUDED.raw_standing,
        raw_team = EXCLUDED.raw_team,
        updated_at = NOW()
    """
    _upsert(sql, records, "group_standings")


def load_top_scorers(rows: list[dict]):
    records = [
        (
            r["player_id"], r["team_id"], r["goals"], r["assists"], r["penalties"], r["played_matches"],
            r["player_name"], r["player_first_name"], r["player_last_name"], r["player_date_of_birth"],
            r["player_country_of_birth"], r["player_nationality"], r["player_position"],
            r["team_name"], r["team_short_name"], r["team_tla"], _json(r["raw_scorer"]),
            _json(r["raw_player"]), _json(r["raw_team"]),
        )
        for r in rows if r["player_id"] is not None and r["team_id"] is not None
    ]
    sql = """
    INSERT INTO top_scorers (
        player_id, team_id, goals, assists, penalties, played_matches,
        player_name, player_first_name, player_last_name, player_date_of_birth,
        player_country_of_birth, player_nationality, player_position,
        team_name, team_short_name, team_tla, raw_scorer, raw_player, raw_team
    )
    VALUES %s
    ON CONFLICT (player_id, team_id) DO UPDATE SET
        goals = EXCLUDED.goals,
        assists = EXCLUDED.assists,
        penalties = EXCLUDED.penalties,
        played_matches = EXCLUDED.played_matches,
        player_name = EXCLUDED.player_name,
        player_first_name = EXCLUDED.player_first_name,
        player_last_name = EXCLUDED.player_last_name,
        player_date_of_birth = EXCLUDED.player_date_of_birth,
        player_country_of_birth = EXCLUDED.player_country_of_birth,
        player_nationality = EXCLUDED.player_nationality,
        player_position = EXCLUDED.player_position,
        team_name = EXCLUDED.team_name,
        team_short_name = EXCLUDED.team_short_name,
        team_tla = EXCLUDED.team_tla,
        raw_scorer = EXCLUDED.raw_scorer,
        raw_player = EXCLUDED.raw_player,
        raw_team = EXCLUDED.raw_team,
        updated_at = NOW()
    """
    _upsert(sql, records, "top_scorers")

"""
transform.py - reshape raw football-data.org payloads into row dicts
matching the Power BI table schema (see schema.sql).

Every function here is a pure function: same input always produces the
same output, no network or database calls. That makes them cheap to
unit test (see tests/test_transform.py).
"""

import logging

from psycopg2.extras import Json

logger = logging.getLogger(__name__)

# FIFA 3-letter -> ISO 2-letter, for flagcdn.com image URLs.
# The API never returns an actual flag image - only this kind of code.
# Extend this dict as more teams confirm qualification.
FLAG_CODE_MAP = {
    "GER": "de", "BRA": "br", "ARG": "ar", "FRA": "fr", "ENG": "gb-eng",
    "ESP": "es", "POR": "pt", "NED": "nl", "USA": "us", "MEX": "mx",
    "CAN": "ca", "JPN": "jp", "MAR": "ma", "SEN": "sn", "NGA": "ng",
    "GHA": "gh", "AUS": "au", "KOR": "kr", "IRN": "ir", "KSA": "sa",
    "BEL": "be", "SUI": "ch", "CRO": "hr", "DEN": "dk", "URU": "uy",
    "COL": "co", "ECU": "ec", "CHI": "cl", "WAL": "gb-wls", "SCO": "gb-sct",
    "IRL": "ie", "ITA": "it", "POL": "pl", "SRB": "rs", "CZE": "cz",
    "TUN": "tn", "EGY": "eg", "CMR": "cm", "CIV": "ci", "QAT": "qa",
    "IRQ": "iq", "JOR": "jo", "UZB": "uz", "NZL": "nz", "PAN": "pa",
    "CRC": "cr", "JAM": "jm", "HAI": "ht", "CPV": "cv", "RSA": "za",
}


def flag_url_for(code: str | None, fallback: str | None) -> str | None:
    key = (code or fallback or "").upper()
    if not key:
        return None
    two_letter = FLAG_CODE_MAP.get(key, key[:2].lower())
    return f"https://flagcdn.com/w160/{two_letter}.png"


def _date_only(value: str | None) -> str | None:
    return value[:10] if value else None


def _json(value):
    return Json(value) if value is not None else None


def _display_name(person: dict) -> str | None:
    if not person:
        return None
    if person.get("name"):
        return person.get("name")
    return " ".join(part for part in (person.get("firstName"), person.get("lastName")) if part) or None


def _winner_team_id(match: dict) -> int | None:
    winner = (match.get("score") or {}).get("winner")
    home_id = (match.get("homeTeam") or {}).get("id")
    away_id = (match.get("awayTeam") or {}).get("id")
    if winner == "HOME_TEAM":
        return home_id
    if winner == "AWAY_TEAM":
        return away_id
    return None


def _score_side(score_block: dict, period: str, side: str) -> int | None:
    return (score_block.get(period) or {}).get(side)


def _merge_dict(existing: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if value is not None or existing.get(key) is None:
            existing[key] = value
    return existing


def build_teams(
    raw_teams: list,
    raw_matches: list,
    raw_scorers: list,
    squad_payloads: dict[int, dict],
) -> list[dict]:
    rows: dict[int, dict] = {}

    def ensure_team(team_id: int, team_payload: dict | None = None) -> dict:
        if team_id not in rows:
            rows[team_id] = {
                "team_id": team_id,
                "team_name": None,
                "short_name": None,
                "tla": None,
                "group_name": None,
                "country_name": None,
                "country_code": None,
                "flag_url": None,
                "crest_url": None,
                "area_id": None,
                "area_name": None,
                "area_code": None,
                "area_flag": None,
                "address": None,
                "website": None,
                "founded": None,
                "club_colors": None,
                "venue": None,
                "coach_id": None,
                "coach_name": None,
                "coach_nationality": None,
                "last_updated": None,
                "raw_team": None,
                "raw_area": None,
                "raw_coach": None,
                "raw_squad": None,
                "raw_running_competitions": None,
            }
        if team_payload:
            area = team_payload.get("area") or {}
            coach = team_payload.get("coach") or {}
            _merge_dict(rows[team_id], {
                "team_name": team_payload.get("name"),
                "short_name": team_payload.get("shortName"),
                "tla": team_payload.get("tla"),
                "country_name": area.get("name"),
                "country_code": area.get("code"),
                "crest_url": team_payload.get("crest"),
                "area_id": area.get("id"),
                "area_name": area.get("name"),
                "area_code": area.get("code"),
                "area_flag": area.get("flag"),
                "address": team_payload.get("address"),
                "website": team_payload.get("website"),
                "founded": team_payload.get("founded"),
                "club_colors": team_payload.get("clubColors"),
                "venue": team_payload.get("venue"),
                "coach_id": coach.get("id"),
                "coach_name": _display_name(coach),
                "coach_nationality": coach.get("nationality"),
                "last_updated": team_payload.get("lastUpdated"),
                "raw_team": team_payload,
                "raw_area": area or None,
                "raw_coach": coach or None,
                "raw_squad": team_payload.get("squad"),
                "raw_running_competitions": team_payload.get("runningCompetitions"),
            })
        return rows[team_id]

    for team in raw_teams:
        team_id = team.get("id")
        if team_id is not None:
            ensure_team(team_id, team)

    for match in raw_matches:
        group = match.get("group")
        for side in ("homeTeam", "awayTeam"):
            team = match.get(side) or {}
            team_id = team.get("id")
            if team_id is None:
                continue
            row = ensure_team(team_id, team)
            if group and not row["group_name"]:
                row["group_name"] = group

    for scorer in raw_scorers:
        team = scorer.get("team") or {}
        team_id = team.get("id")
        if team_id is not None:
            ensure_team(team_id, team)

    for team_id, payload in squad_payloads.items():
        ensure_team(team_id, payload)

    for row in rows.values():
        row["flag_url"] = row.get("area_flag") or flag_url_for(row["country_code"], row["tla"])

    logger.info("Built %d teams", len(rows))
    return list(rows.values())


def _player_row(player: dict, team_id: int | None, source: str) -> dict:
    current_team = player.get("currentTeam") or {}
    contract = current_team.get("contract") or player.get("contract") or {}
    return {
        "player_id": player.get("id"),
        "player_name": _display_name(player),
        "first_name": player.get("firstName"),
        "last_name": player.get("lastName"),
        "position": player.get("position"),
        "date_of_birth": _date_only(player.get("dateOfBirth")),
        "country_of_birth": player.get("countryOfBirth"),
        "nationality": player.get("nationality"),
        "shirt_number": player.get("shirtNumber"),
        "last_updated": player.get("lastUpdated"),
        "team_id": team_id or current_team.get("id"),
        "contract_start": _date_only(contract.get("start")),
        "contract_until": _date_only(contract.get("until")),
        "source": source,
        "raw_player": player,
        "raw_current_team": current_team or None,
        "raw_contract": contract or None,
    }


def build_players(squad_payloads: dict[int, dict], raw_scorers: list) -> list[dict]:
    rows: dict[int, dict] = {}

    def add(row: dict):
        player_id = row.get("player_id")
        if player_id is None:
            return
        if player_id not in rows:
            rows[player_id] = row
            return
        existing = rows[player_id]
        for key, value in row.items():
            if value is not None and (existing.get(key) is None or key.startswith("raw_")):
                existing[key] = value
        if existing.get("source") != row.get("source"):
            existing["source"] = "squad+scorers"

    for team_id, payload in squad_payloads.items():
        for player in payload.get("squad", []):
            add(_player_row(player, team_id, "squad"))

    for scorer in raw_scorers:
        player = scorer.get("player") or {}
        team = scorer.get("team") or {}
        add(_player_row(player, team.get("id"), "scorers"))

    logger.info("Built %d players", len(rows))
    return list(rows.values())


def build_matches(raw_matches: list) -> list[dict]:
    rows = []
    for match in raw_matches:
        score = match.get("score") or {}
        full_time = score.get("fullTime") or {}
        half_time = score.get("halfTime") or {}
        area = match.get("area") or {}
        competition = match.get("competition") or {}
        season = match.get("season") or {}
        home_team = match.get("homeTeam") or {}
        away_team = match.get("awayTeam") or {}
        referees = match.get("referees") or []
        referee = referees[0] if referees else {}
        goals = match.get("goals") or []
        bookings = match.get("bookings") or []
        substitutions = match.get("substitutions") or []
        penalties = match.get("penalties") or []
        home_ft, away_ft = full_time.get("home"), full_time.get("away")

        rows.append({
            "match_id": match["id"],
            "status": match.get("status"),
            "matchday": match.get("matchday"),
            "stage": match.get("stage"),
            "group_name": match.get("group"),
            "utc_date": match.get("utcDate"),
            "match_date": _date_only(match.get("utcDate")),
            "home_team_id": home_team.get("id"),
            "away_team_id": away_team.get("id"),
            "winner_team_id": _winner_team_id(match),
            "venue_name": match.get("venue") or None,
            "home_score_ft": home_ft,
            "away_score_ft": away_ft,
            "home_score_ht": half_time.get("home"),
            "away_score_ht": half_time.get("away"),
            "total_goals": (home_ft or 0) + (away_ft or 0),
            "referee_name": referee.get("name"),
            "referee_nationality": referee.get("nationality"),
            "area_id": area.get("id"),
            "area_name": area.get("name"),
            "competition_id": competition.get("id"),
            "competition_name": competition.get("name"),
            "competition_code": competition.get("code"),
            "season_id": season.get("id"),
            "season_start_date": _date_only(season.get("startDate")),
            "season_end_date": _date_only(season.get("endDate")),
            "current_matchday": season.get("currentMatchday"),
            "score_winner": score.get("winner"),
            "score_duration": score.get("duration"),
            "home_score_regular": _score_side(score, "regularTime", "home"),
            "away_score_regular": _score_side(score, "regularTime", "away"),
            "home_score_extra": _score_side(score, "extraTime", "home"),
            "away_score_extra": _score_side(score, "extraTime", "away"),
            "home_score_penalties": _score_side(score, "penalties", "home"),
            "away_score_penalties": _score_side(score, "penalties", "away"),
            "minute": match.get("minute"),
            "injury_time": match.get("injuryTime"),
            "attendance": match.get("attendance"),
            "last_updated": match.get("lastUpdated"),
            "referees_count": len(referees),
            "goals_count": len(goals),
            "bookings_count": len(bookings),
            "substitutions_count": len(substitutions),
            "penalties_count": len(penalties),
            "home_formation": home_team.get("formation"),
            "away_formation": away_team.get("formation"),
            "raw_match": match,
            "raw_area": area or None,
            "raw_competition": competition or None,
            "raw_season": season or None,
            "raw_score": score or None,
            "raw_home_team": home_team or None,
            "raw_away_team": away_team or None,
            "raw_referees": referees or None,
            "raw_goals": goals or None,
            "raw_bookings": bookings or None,
            "raw_substitutions": substitutions or None,
            "raw_penalties": penalties or None,
            "raw_odds": match.get("odds"),
        })
    logger.info("Built %d matches", len(rows))
    return rows


def build_group_standings(raw_standings: list) -> list[dict]:
    rows = []
    for block in raw_standings:
        group_name = block.get("group")
        stage = block.get("stage")
        for entry in block.get("table", []):
            team = entry.get("team") or {}
            rows.append({
                "group_name": group_name,
                "stage": stage,
                "position": entry.get("position"),
                "team_id": team.get("id"),
                "played": entry.get("playedGames"),
                "won": entry.get("won"),
                "draw": entry.get("draw"),
                "lost": entry.get("lost"),
                "goals_for": entry.get("goalsFor"),
                "goals_against": entry.get("goalsAgainst"),
                "goal_difference": entry.get("goalDifference"),
                "points": entry.get("points"),
                "form": entry.get("form"),
                "raw_standing": entry,
                "raw_team": team or None,
            })
    logger.info("Built %d group-standings rows", len(rows))
    return rows


def build_top_scorers(raw_scorers: list) -> list[dict]:
    rows = []
    for scorer in raw_scorers:
        player = scorer.get("player") or {}
        team = scorer.get("team") or {}
        rows.append({
            "player_id": player.get("id"),
            "team_id": team.get("id"),
            "goals": scorer.get("goals") or 0,
            "assists": scorer.get("assists") or 0,
            "penalties": scorer.get("penalties") or 0,
            "played_matches": scorer.get("playedMatches") or 0,
            "player_name": _display_name(player),
            "player_first_name": player.get("firstName"),
            "player_last_name": player.get("lastName"),
            "player_date_of_birth": _date_only(player.get("dateOfBirth")),
            "player_country_of_birth": player.get("countryOfBirth"),
            "player_nationality": player.get("nationality"),
            "player_position": player.get("position"),
            "team_name": team.get("name"),
            "team_short_name": team.get("shortName"),
            "team_tla": team.get("tla"),
            "raw_scorer": scorer,
            "raw_player": player or None,
            "raw_team": team or None,
        })
    logger.info("Built %d top-scorer rows", len(rows))
    return rows

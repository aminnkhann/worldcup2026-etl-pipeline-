"""
Unit tests for transform.py.

These only exercise pure functions (no network, no database), so they
run instantly and don't need a .env file or a running Postgres.
"""

from worldcup_pipeline.transform import (
    _date_only,
    _display_name,
    _score_side,
    _winner_team_id,
    build_group_standings,
    build_matches,
    build_players,
    build_teams,
    build_top_scorers,
    flag_url_for,
)


def make_match(**overrides):
    match = {
        "id": 1001,
        "status": "FINISHED",
        "matchday": 1,
        "stage": "GROUP_STAGE",
        "group": "Group A",
        "utcDate": "2026-06-11T18:00:00Z",
        "venue": "Estadio Azteca",
        "homeTeam": {"id": 1, "name": "Mexico", "formation": "4-3-3"},
        "awayTeam": {"id": 2, "name": "Canada", "formation": "4-4-2"},
        "score": {
            "winner": "HOME_TEAM",
            "duration": "REGULAR",
            "fullTime": {"home": 2, "away": 1},
            "halfTime": {"home": 1, "away": 0},
            "regularTime": {"home": 2, "away": 1},
        },
        "referees": [{"name": "Referee One", "nationality": "Brazil"}],
        "goals": [{"minute": 10}, {"minute": 55}, {"minute": 70}],
        "bookings": [],
        "substitutions": [],
        "penalties": [],
        "area": {"id": 2081, "name": "World"},
        "competition": {"id": 1, "name": "FIFA World Cup", "code": "WC"},
        "season": {"id": 1, "startDate": "2026-06-11", "endDate": "2026-07-19", "currentMatchday": 1},
    }
    match.update(overrides)
    return match


# ---------------- small helpers ----------------

def test_date_only_truncates_to_date():
    assert _date_only("2026-06-11T18:00:00Z") == "2026-06-11"


def test_date_only_handles_none():
    assert _date_only(None) is None


def test_display_name_prefers_name_field():
    assert _display_name({"name": "Lionel Messi", "firstName": "Lionel"}) == "Lionel Messi"


def test_display_name_falls_back_to_first_last():
    assert _display_name({"firstName": "Lionel", "lastName": "Messi"}) == "Lionel Messi"


def test_display_name_returns_none_for_empty_person():
    assert _display_name({}) is None
    assert _display_name(None) is None


def test_score_side_reads_nested_period():
    score = {"regularTime": {"home": 2, "away": 1}}
    assert _score_side(score, "regularTime", "home") == 2
    assert _score_side(score, "extraTime", "home") is None


def test_winner_team_id_home_and_away():
    home_win = make_match(score={"winner": "HOME_TEAM"})
    away_win = make_match(score={"winner": "AWAY_TEAM"})
    assert _winner_team_id(home_win) == 1
    assert _winner_team_id(away_win) == 2


def test_winner_team_id_none_when_draw():
    draw = make_match(score={"winner": "DRAW"})
    assert _winner_team_id(draw) is None


def test_flag_url_for_known_code_uses_map():
    assert flag_url_for("GER", None) == "https://flagcdn.com/w160/de.png"


def test_flag_url_for_unknown_code_falls_back_to_prefix():
    assert flag_url_for("XYZ", None) == "https://flagcdn.com/w160/xy.png"


def test_flag_url_for_empty_returns_none():
    assert flag_url_for(None, None) is None


# ---------------- build_matches ----------------

def test_build_matches_computes_total_goals_and_winner():
    rows = build_matches([make_match()])
    assert len(rows) == 1
    row = rows[0]
    assert row["match_id"] == 1001
    assert row["total_goals"] == 3
    assert row["winner_team_id"] == 1
    assert row["match_date"] == "2026-06-11"
    assert row["goals_count"] == 3
    assert row["referee_name"] == "Referee One"
    assert row["home_formation"] == "4-3-3"


def test_build_matches_handles_scoreless_scheduled_match():
    scheduled = make_match(
        id=1002,
        status="SCHEDULED",
        score={"winner": None, "fullTime": {"home": None, "away": None}},
        goals=[],
    )
    row = build_matches([scheduled])[0]
    assert row["total_goals"] == 0
    assert row["winner_team_id"] is None
    assert row["home_score_ft"] is None


# ---------------- build_group_standings ----------------

def test_build_group_standings_flattens_table_rows():
    raw = [{
        "group": "Group A",
        "stage": "GROUP_STAGE",
        "table": [
            {"position": 1, "team": {"id": 1}, "playedGames": 1, "won": 1, "points": 3},
            {"position": 2, "team": {"id": 2}, "playedGames": 1, "won": 0, "points": 0},
        ],
    }]
    rows = build_group_standings(raw)
    assert len(rows) == 2
    assert rows[0]["team_id"] == 1
    assert rows[0]["points"] == 3


# ---------------- build_top_scorers ----------------

def test_build_top_scorers_defaults_missing_counts_to_zero():
    raw = [{
        "player": {"id": 10, "name": "Top Scorer"},
        "team": {"id": 1, "name": "Mexico"},
        "goals": 5,
    }]
    row = build_top_scorers(raw)[0]
    assert row["goals"] == 5
    assert row["assists"] == 0
    assert row["penalties"] == 0
    assert row["played_matches"] == 0
    assert row["player_name"] == "Top Scorer"


# ---------------- build_teams ----------------

def test_build_teams_picks_up_group_name_from_matches():
    raw_teams = [{"id": 1, "name": "Mexico", "tla": "MEX", "area": {"code": "MEX"}}]
    rows = build_teams(raw_teams, [make_match()], [], {})
    team = next(t for t in rows if t["team_id"] == 1)
    assert team["group_name"] == "Group A"
    assert team["team_name"] == "Mexico"


def test_build_teams_falls_back_to_flag_url_when_no_area_flag():
    raw_teams = [{"id": 1, "name": "Germany", "tla": "GER", "area": {"code": "GER"}}]
    rows = build_teams(raw_teams, [], [], {})
    assert rows[0]["flag_url"] == "https://flagcdn.com/w160/de.png"


# ---------------- build_players ----------------

def test_build_players_merges_squad_and_scorer_sources():
    squad_payloads = {
        1: {"squad": [{"id": 100, "name": "Player One", "position": "Forward"}]},
    }
    raw_scorers = [{
        "player": {"id": 100, "name": "Player One"},
        "team": {"id": 1},
    }]
    players = build_players(squad_payloads, raw_scorers)
    assert len(players) == 1
    assert players[0]["source"] == "squad+scorers"


def test_build_players_skips_rows_without_player_id():
    squad_payloads = {1: {"squad": [{"name": "No Id Player"}]}}
    assert build_players(squad_payloads, []) == []

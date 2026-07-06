from worldcup_pipeline import load


def test_schema_path_points_to_project_schema_file():
    assert load.SCHEMA_PATH.name == "schema.sql"
    assert load.SCHEMA_PATH.exists()


def test_load_top_scorers_filters_rows_without_foreign_keys(monkeypatch):
    captured = {}

    def fake_upsert(sql, rows, table):
        captured["sql"] = sql
        captured["rows"] = rows
        captured["table"] = table

    monkeypatch.setattr(load, "_upsert", fake_upsert)
    load.load_top_scorers([
        {
            "player_id": 10,
            "team_id": 1,
            "goals": 3,
            "assists": 1,
            "penalties": 0,
            "played_matches": 2,
            "player_name": "Player One",
            "player_first_name": "Player",
            "player_last_name": "One",
            "player_date_of_birth": "2000-01-01",
            "player_country_of_birth": "Germany",
            "player_nationality": "Germany",
            "player_position": "Forward",
            "team_name": "Germany",
            "team_short_name": "Germany",
            "team_tla": "GER",
            "raw_scorer": {},
            "raw_player": {},
            "raw_team": {},
        },
        {
            "player_id": None,
            "team_id": 1,
            "goals": 1,
            "assists": 0,
            "penalties": 0,
            "played_matches": 1,
            "player_name": "Missing Id",
            "player_first_name": None,
            "player_last_name": None,
            "player_date_of_birth": None,
            "player_country_of_birth": None,
            "player_nationality": None,
            "player_position": None,
            "team_name": "Germany",
            "team_short_name": "Germany",
            "team_tla": "GER",
            "raw_scorer": {},
            "raw_player": {},
            "raw_team": {},
        },
    ])

    assert captured["table"] == "top_scorers"
    assert len(captured["rows"]) == 1
    assert captured["rows"][0][0:2] == (10, 1)

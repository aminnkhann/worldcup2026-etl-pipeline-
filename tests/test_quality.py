import pytest

from worldcup_pipeline.quality import DataQualityError, validate_dimensions, validate_facts


def test_validate_dimensions_rejects_missing_required_team_name():
    with pytest.raises(DataQualityError, match="team_name"):
        validate_dimensions([{"team_id": 1, "team_name": None}], [])


def test_validate_facts_rejects_unknown_top_scorer_player():
    with pytest.raises(DataQualityError, match="player_id is not present in players"):
        validate_facts(
            matches=[],
            standings=[],
            scorers=[{"player_id": 10, "team_id": 1, "player_name": "Player One"}],
            team_ids={1},
            player_ids=set(),
        )


def test_validate_facts_accepts_fk_safe_rows():
    validate_facts(
        matches=[{"match_id": 100, "home_team_id": 1, "away_team_id": 2, "winner_team_id": 1}],
        standings=[{"group_name": "Group A", "team_id": 1}],
        scorers=[{"player_id": 10, "team_id": 1, "player_name": "Player One"}],
        team_ids={1, 2},
        player_ids={10},
    )

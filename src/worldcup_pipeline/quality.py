"""Data-quality checks for transformed ETL rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class QualityIssue:
    dataset: str
    row: str
    message: str


class DataQualityError(ValueError):
    def __init__(self, issues: list[QualityIssue]):
        self.issues = issues
        preview = "\n".join(
            f"- {issue.dataset} [{issue.row}]: {issue.message}"
            for issue in issues[:20]
        )
        suffix = "" if len(issues) <= 20 else f"\n... and {len(issues) - 20} more issue(s)"
        super().__init__(f"Data quality validation failed with {len(issues)} issue(s):\n{preview}{suffix}")


def _row_label(row: dict, keys: Iterable[str]) -> str:
    values = [f"{key}={row.get(key)!r}" for key in keys]
    return ", ".join(values)


def _require(
    row: dict,
    dataset: str,
    label_keys: Iterable[str],
    keys: Iterable[str],
    issues: list[QualityIssue],
) -> None:
    label = _row_label(row, label_keys)
    for key in keys:
        if row.get(key) in (None, ""):
            issues.append(QualityIssue(dataset, label, f"missing required field {key!r}"))


def _check_unique(rows: list[dict], dataset: str, keys: tuple[str, ...], issues: list[QualityIssue]) -> None:
    seen = set()
    for row in rows:
        value = tuple(row.get(key) for key in keys)
        if any(part is None for part in value):
            continue
        if value in seen:
            issues.append(QualityIssue(dataset, _row_label(row, keys), "duplicate key"))
        seen.add(value)


def validate_dimensions(teams: list[dict], players: list[dict]) -> None:
    issues: list[QualityIssue] = []
    _check_unique(teams, "teams", ("team_id",), issues)
    _check_unique(players, "players", ("player_id",), issues)

    team_ids = {row.get("team_id") for row in teams if row.get("team_id") is not None}
    for team in teams:
        _require(team, "teams", ("team_id", "team_name"), ("team_id", "team_name"), issues)

    for player in players:
        _require(player, "players", ("player_id", "player_name"), ("player_id", "player_name"), issues)
        team_id = player.get("team_id")
        if team_id is not None and team_id not in team_ids:
            issues.append(
                QualityIssue(
                    "players",
                    _row_label(player, ("player_id", "team_id")),
                    "team_id is not present in teams",
                )
            )

    if issues:
        raise DataQualityError(issues)


def validate_facts(
    matches: list[dict],
    standings: list[dict],
    scorers: list[dict],
    *,
    team_ids: set[int],
    player_ids: set[int],
) -> None:
    issues: list[QualityIssue] = []
    _check_unique(matches, "matches", ("match_id",), issues)
    _check_unique(standings, "group_standings", ("group_name", "team_id"), issues)
    _check_unique(scorers, "top_scorers", ("player_id", "team_id"), issues)

    for match in matches:
        _require(match, "matches", ("match_id",), ("match_id",), issues)
        for key in ("home_team_id", "away_team_id", "winner_team_id"):
            team_id = match.get(key)
            if team_id is not None and team_id not in team_ids:
                issues.append(
                    QualityIssue(
                        "matches",
                        _row_label(match, ("match_id", key)),
                        f"{key} is not present in teams",
                    )
                )
        if match.get("status") == "FINISHED" and (
            match.get("home_score_ft") is None or match.get("away_score_ft") is None
        ):
            issues.append(
                QualityIssue(
                    "matches",
                    _row_label(match, ("match_id",)),
                    "finished match is missing full-time score",
                )
            )

    for standing in standings:
        _require(standing, "group_standings", ("group_name", "team_id"), ("group_name", "team_id"), issues)
        team_id = standing.get("team_id")
        if team_id is not None and team_id not in team_ids:
            issues.append(
                QualityIssue(
                    "group_standings",
                    _row_label(standing, ("group_name", "team_id")),
                    "team_id is not present in teams",
                )
            )

    for scorer in scorers:
        _require(scorer, "top_scorers", ("player_id", "team_id"), ("player_id", "team_id", "player_name"), issues)
        team_id = scorer.get("team_id")
        player_id = scorer.get("player_id")
        if team_id is not None and team_id not in team_ids:
            issues.append(
                QualityIssue(
                    "top_scorers",
                    _row_label(scorer, ("player_id", "team_id")),
                    "team_id is not present in teams",
                )
            )
        if player_id is not None and player_id not in player_ids:
            issues.append(
                QualityIssue(
                    "top_scorers",
                    _row_label(scorer, ("player_id", "team_id")),
                    "player_id is not present in players",
                )
            )

    if issues:
        raise DataQualityError(issues)

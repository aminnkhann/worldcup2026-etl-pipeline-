# FIFA World Cup 2026 ETL Pipeline

A small ETL pipeline that pulls FIFA World Cup 2026 data from the
[football-data.org](https://www.football-data.org/) API and loads it into
PostgreSQL, feeding a Power BI report.

## Architecture

The pipeline is split into three stages plus an orchestrator, so each part
can be read, tested, and changed independently:

| File | Responsibility |
|---|---|
| `extract.py` | HTTP calls to football-data.org (retries, backoff, rate-limit handling). Returns raw JSON, unchanged. |
| `transform.py` | Pure functions that reshape raw JSON into row dicts matching the database schema. No network or database calls. |
| `load.py` | Applies `schema.sql` and upserts row dicts into PostgreSQL (`ON CONFLICT ... DO UPDATE`, so re-running is always safe). |
| `run.py` | Orchestrates the three stages above and exposes the CLI. |
| `schema.sql` | Idempotent table/index/view definitions (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`). |

Because `transform.py` has no I/O, it's covered by fast unit tests in
`tests/test_transform.py` that don't need an API key or a running database.

## Setup

```bash
uv sync                 # runtime dependencies
uv sync --extra dev      # + pytest, for running tests
cp .env.example .env     # then fill in real values
```

Required `.env` values:

| Variable | Purpose |
|---|---|
| `FOOTBALL_API_KEY` | football-data.org API key (required) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection |

**Never commit `.env`.** It holds real secrets and is excluded via
`.gitignore`; only `.env.example` (placeholders) is meant to be tracked.

## Running

```bash
uv run python run.py                # full sync: dimensions + facts
uv run python run.py --facts-only   # facts only (matches, standings, scorers)
```

**Dimensions vs. facts:** teams, coaches, and squads (`teams`, `players`)
rarely change once the tournament is under way, and fetching a squad per
team is the slowest and most rate-limit-sensitive part of a run. Matches,
standings, and top scorers change every matchday. So:

- Run a full sync (no flag) once at the start, and again if rosters change
  (injuries, late call-ups).
- Run `--facts-only` for routine refreshes during the tournament — it
  skips the per-team squad fetch entirely and only updates the tables that
  actually change.

Known limitation: `top_scorers.player_id` has a foreign key on `players`.
If a `--facts-only` run surfaces a scorer who isn't already in the
`players` table (rare — scorers are normally already in their team's
squad), that row will fail to load until a full sync adds the player.

## Tests

```bash
uv run pytest
```

Tests cover the pure transform logic only (score/winner calculation, name
formatting, flag URL lookup, row building for teams/players/matches/
standings/top scorers). They don't hit the network or a database.

## Schema overview

- `teams` — one row per team, plus coach/area info and raw API payloads.
- `players` — one row per player, sourced from squads and/or the scorers
  list.
- `matches` — one row per match, with scores, referees, and per-match raw
  JSON blocks (goals, bookings, substitutions, penalties, odds).
- `group_standings` — one row per team per group.
- `top_scorers` — one row per (player, team), with a generated
  `goals_per_game` column.
- `v_team_match_results` — view joining `teams`/`matches` into a
  per-team, per-match result feed for Power BI.

## Possible next steps

- Orchestrate with Dagster (`@asset` per extract/transform/load function),
  which would also let dimensions and facts run on different schedules
  instead of a CLI flag.

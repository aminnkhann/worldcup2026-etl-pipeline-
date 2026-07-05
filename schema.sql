-- ============================================================
-- FIFA World Cup 2026 - additive Power BI schema
-- Existing table names and original columns are preserved.
-- New scalar columns and raw JSONB columns are added idempotently.
-- Safe to re-run: CREATE TABLE IF NOT EXISTS, ALTER ADD COLUMN IF NOT EXISTS.
-- ============================================================

CREATE TABLE IF NOT EXISTS teams (
    team_id      INTEGER PRIMARY KEY,
    team_name    VARCHAR(100) NOT NULL,
    short_name   VARCHAR(100),
    tla          VARCHAR(10),
    group_name   VARCHAR(10),
    country_name VARCHAR(100),
    country_code VARCHAR(10),
    flag_url     VARCHAR(300),
    crest_url    VARCHAR(300),
    area_id      INTEGER,
    area_name    VARCHAR(100),
    area_code    VARCHAR(10),
    area_flag    VARCHAR(300),
    address      VARCHAR(300),
    website      VARCHAR(300),
    founded      INTEGER,
    club_colors  VARCHAR(200),
    venue        VARCHAR(200),
    coach_id     INTEGER,
    coach_name   VARCHAR(150),
    coach_nationality VARCHAR(100),
    last_updated TIMESTAMPTZ,
    raw_team     JSONB,
    raw_area     JSONB,
    raw_coach    JSONB,
    raw_squad    JSONB,
    raw_running_competitions JSONB,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY,
    player_name   VARCHAR(150) NOT NULL,
    first_name    VARCHAR(100),
    last_name     VARCHAR(100),
    position      VARCHAR(50),
    date_of_birth DATE,
    country_of_birth VARCHAR(100),
    nationality   VARCHAR(100),
    shirt_number  INTEGER,
    last_updated  TIMESTAMPTZ,
    team_id       INTEGER REFERENCES teams(team_id),
    contract_start DATE,
    contract_until DATE,
    source        VARCHAR(50),
    raw_player    JSONB,
    raw_current_team JSONB,
    raw_contract  JSONB,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches (
    match_id            INTEGER PRIMARY KEY,
    status              VARCHAR(50),
    matchday            INTEGER,
    stage               VARCHAR(100),
    group_name          VARCHAR(10),
    utc_date            TIMESTAMPTZ,
    match_date          DATE,
    home_team_id        INTEGER REFERENCES teams(team_id),
    away_team_id        INTEGER REFERENCES teams(team_id),
    winner_team_id      INTEGER REFERENCES teams(team_id),
    venue_name          VARCHAR(200),
    home_score_ft       INTEGER,
    away_score_ft       INTEGER,
    home_score_ht       INTEGER,
    away_score_ht       INTEGER,
    total_goals         INTEGER DEFAULT 0,
    referee_name        VARCHAR(150),
    referee_nationality VARCHAR(100),
    area_id             INTEGER,
    area_name           VARCHAR(100),
    competition_id      INTEGER,
    competition_name    VARCHAR(150),
    competition_code    VARCHAR(20),
    season_id           INTEGER,
    season_start_date   DATE,
    season_end_date     DATE,
    current_matchday    INTEGER,
    score_winner        VARCHAR(50),
    score_duration      VARCHAR(50),
    home_score_regular  INTEGER,
    away_score_regular  INTEGER,
    home_score_extra    INTEGER,
    away_score_extra    INTEGER,
    home_score_penalties INTEGER,
    away_score_penalties INTEGER,
    minute              INTEGER,
    injury_time         INTEGER,
    attendance          INTEGER,
    last_updated        TIMESTAMPTZ,
    referees_count      INTEGER DEFAULT 0,
    goals_count         INTEGER DEFAULT 0,
    bookings_count      INTEGER DEFAULT 0,
    substitutions_count INTEGER DEFAULT 0,
    penalties_count     INTEGER DEFAULT 0,
    home_formation      VARCHAR(50),
    away_formation      VARCHAR(50),
    raw_match           JSONB,
    raw_area            JSONB,
    raw_competition     JSONB,
    raw_season          JSONB,
    raw_score           JSONB,
    raw_home_team       JSONB,
    raw_away_team       JSONB,
    raw_referees        JSONB,
    raw_goals           JSONB,
    raw_bookings        JSONB,
    raw_substitutions   JSONB,
    raw_penalties       JSONB,
    raw_odds            JSONB,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS group_standings (
    group_name      VARCHAR(10) NOT NULL,
    stage           VARCHAR(100),
    position        INTEGER,
    team_id         INTEGER REFERENCES teams(team_id),
    played          INTEGER DEFAULT 0,
    won             INTEGER DEFAULT 0,
    draw            INTEGER DEFAULT 0,
    lost            INTEGER DEFAULT 0,
    goals_for       INTEGER DEFAULT 0,
    goals_against   INTEGER DEFAULT 0,
    goal_difference INTEGER DEFAULT 0,
    points          INTEGER DEFAULT 0,
    form            VARCHAR(100),
    raw_standing    JSONB,
    raw_team        JSONB,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (group_name, team_id)
);

CREATE TABLE IF NOT EXISTS top_scorers (
    player_id      INTEGER REFERENCES players(player_id),
    team_id        INTEGER REFERENCES teams(team_id),
    goals          INTEGER DEFAULT 0,
    assists        INTEGER DEFAULT 0,
    penalties      INTEGER DEFAULT 0,
    played_matches INTEGER DEFAULT 0,
    goals_per_game NUMERIC(6, 2) GENERATED ALWAYS AS (
        CASE WHEN played_matches > 0
             THEN ROUND(goals::NUMERIC / played_matches, 2)
             ELSE 0
        END
    ) STORED,
    player_name VARCHAR(150),
    player_first_name VARCHAR(100),
    player_last_name VARCHAR(100),
    player_date_of_birth DATE,
    player_country_of_birth VARCHAR(100),
    player_nationality VARCHAR(100),
    player_position VARCHAR(50),
    team_name VARCHAR(100),
    team_short_name VARCHAR(100),
    team_tla VARCHAR(10),
    raw_scorer JSONB,
    raw_player JSONB,
    raw_team JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, team_id)
);

-- Additive migrations for existing databases.

ALTER TABLE teams ADD COLUMN IF NOT EXISTS area_id INTEGER;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS area_name VARCHAR(100);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS area_code VARCHAR(10);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS area_flag VARCHAR(300);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS address VARCHAR(300);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS website VARCHAR(300);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS founded INTEGER;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS club_colors VARCHAR(200);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS venue VARCHAR(200);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS coach_id INTEGER;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS coach_name VARCHAR(150);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS coach_nationality VARCHAR(100);
ALTER TABLE teams ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS raw_team JSONB;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS raw_area JSONB;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS raw_coach JSONB;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS raw_squad JSONB;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS raw_running_competitions JSONB;

ALTER TABLE players ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE players ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
ALTER TABLE players ADD COLUMN IF NOT EXISTS country_of_birth VARCHAR(100);
ALTER TABLE players ADD COLUMN IF NOT EXISTS shirt_number INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ;
ALTER TABLE players ADD COLUMN IF NOT EXISTS contract_start DATE;
ALTER TABLE players ADD COLUMN IF NOT EXISTS contract_until DATE;
ALTER TABLE players ADD COLUMN IF NOT EXISTS source VARCHAR(50);
ALTER TABLE players ADD COLUMN IF NOT EXISTS raw_player JSONB;
ALTER TABLE players ADD COLUMN IF NOT EXISTS raw_current_team JSONB;
ALTER TABLE players ADD COLUMN IF NOT EXISTS raw_contract JSONB;

ALTER TABLE matches ADD COLUMN IF NOT EXISTS area_id INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS area_name VARCHAR(100);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_id INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_name VARCHAR(150);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_code VARCHAR(20);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS season_id INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS season_start_date DATE;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS season_end_date DATE;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS current_matchday INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_winner VARCHAR(50);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS score_duration VARCHAR(50);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score_regular INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score_regular INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score_extra INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score_extra INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score_penalties INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score_penalties INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS minute INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS injury_time INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS attendance INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS referees_count INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS goals_count INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS bookings_count INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS substitutions_count INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS penalties_count INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_formation VARCHAR(50);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_formation VARCHAR(50);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_match JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_area JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_competition JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_season JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_score JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_home_team JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_away_team JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_referees JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_goals JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_bookings JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_substitutions JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_penalties JSONB;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_odds JSONB;

ALTER TABLE group_standings ADD COLUMN IF NOT EXISTS form VARCHAR(100);
ALTER TABLE group_standings ADD COLUMN IF NOT EXISTS raw_standing JSONB;
ALTER TABLE group_standings ADD COLUMN IF NOT EXISTS raw_team JSONB;

ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_name VARCHAR(150);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_first_name VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_last_name VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_date_of_birth DATE;
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_country_of_birth VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_nationality VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS player_position VARCHAR(50);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS team_name VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS team_short_name VARCHAR(100);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS team_tla VARCHAR(10);
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS raw_scorer JSONB;
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS raw_player JSONB;
ALTER TABLE top_scorers ADD COLUMN IF NOT EXISTS raw_team JSONB;

-- Indexes

CREATE INDEX IF NOT EXISTS idx_matches_home_team_id ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away_team_id ON matches(away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_match_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_stage ON matches(stage);
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_group_standings_team_id ON group_standings(team_id);
CREATE INDEX IF NOT EXISTS idx_top_scorers_team_id ON top_scorers(team_id);
CREATE INDEX IF NOT EXISTS idx_top_scorers_goals ON top_scorers(goals DESC);
CREATE INDEX IF NOT EXISTS idx_teams_group_name ON teams(group_name);

-- Convenience view: original Power BI shape remains stable.

DROP VIEW IF EXISTS v_team_match_results CASCADE;
CREATE VIEW v_team_match_results AS
SELECT
    t.team_id,
    t.team_name,
    t.country_name,
    t.flag_url,
    t.crest_url,
    m.match_date,
    m.stage,
    m.group_name,
    m.status,
    opp.team_name AS opponent_name,
    CASE WHEN m.home_team_id = t.team_id THEN m.home_score_ft ELSE m.away_score_ft END AS team_score,
    CASE WHEN m.home_team_id = t.team_id THEN m.away_score_ft ELSE m.home_score_ft END AS opponent_score,
    CASE
        WHEN m.status <> 'FINISHED' THEN 'Scheduled'
        WHEN (m.home_team_id = t.team_id AND m.home_score_ft > m.away_score_ft)
          OR (m.away_team_id = t.team_id AND m.away_score_ft > m.home_score_ft) THEN 'W'
        WHEN m.home_score_ft = m.away_score_ft THEN 'D'
        ELSE 'L'
    END AS result
FROM teams t
JOIN matches m ON t.team_id = m.home_team_id OR t.team_id = m.away_team_id
JOIN teams opp ON opp.team_id = CASE WHEN m.home_team_id = t.team_id THEN m.away_team_id ELSE m.home_team_id END
ORDER BY t.team_name, m.match_date;

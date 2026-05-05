CREATE TABLE IF NOT EXISTS standings (
    position INT,
    team VARCHAR(100),
    season INT NOT NULL,
    played INT,
    won INT,
    drawn INT,
    lost INT,
    goals_for INT,
    goals_against INT,
    goal_difference INT,
    win_rate FLOAT,
    points INT,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (team, season)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INT PRIMARY KEY,
    season INT NOT NULL,
    date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INT,
    away_score INT,
    result VARCHAR(10)
);

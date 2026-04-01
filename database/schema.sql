CREATE TABLE IF NOT EXISTS standings(
    position INT,
    team VARCHAR(100),
    played INT,
    won INT,
    drawn INT,
    lost INT,
    goals_for INT,
    goals_against INT,
    goal_difference INT,
    win_rate FLOAT,
    points INT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches(
    match_id INT PRIMARY KEY,
    date DATE,
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INT,
    away_score INT,
    result VARCHAR(10),
);

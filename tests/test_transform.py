import pandas as pd
import pytest
from transformation.transform import transform_standings, transform_matches

# Fixtures
@pytest.fixture
def sample_standings():
    return pd.DataFrame([
        {'position': 1, 'team': 'Arsenal', 'played': 10, 'won': 7, 'draw': 2, 'lost': 1, 'goals_for': 20, 'goals_against': 8, 'points': 23},
        {'position': 2, 'team': 'Chelsea', 'played': 10, 'won': 6, 'draw': 1, 'lost': 3, 'goals_for': 15, 'goals_against': 10, 'points': 19},
    ])

@pytest.fixture
def sample_matches():
    return pd.DataFrame([
        {'match_id': 1, 'date': '2024-01-01', 'home_team': 'Arsenal',  'away_team': 'Chelsea',   'home_score': 2, 'away_score': 1, 'status': 'FINISHED'},
        {'match_id': 2, 'date': '2024-01-08', 'home_team': 'Chelsea',  'away_team': 'Liverpool', 'home_score': 0, 'away_score': 0, 'status': 'FINISHED'},
        {'match_id': 3, 'date': '2024-01-15', 'home_team': 'Arsenal',  'away_team': 'Liverpool', 'home_score': 1, 'away_score': 3, 'status': 'SCHEDULED'},
    ])

# Tests
def test_transform_standings_adiciona_goal_difference(sample_standings):
    result = transform_standings(sample_standings)
    assert 'goal_difference' in result.columns

def test_transform_standings_calcula_goal_difference_correto(sample_standings):
    result = transform_standings(sample_standings)
    assert result.iloc[0]['goal_difference'] == 12  # 20 - 8
    assert result.iloc[1]['goal_difference'] == 5   # 15 - 10

def test_transform_standings_adiciona_win_rate(sample_standings):
    result = transform_standings(sample_standings)
    assert 'win_rate' in result.columns

def test_transform_standings_calcula_win_rate_correto(sample_standings):
    result = transform_standings(sample_standings)
    assert result.iloc[0]['win_rate'] == 0.70  # 7/10
    assert result.iloc[1]['win_rate'] == 0.60  # 6/10

# Tests
def test_transform_matches_remove_jogos_nao_finalizados(sample_matches):
    result = transform_matches(sample_matches)
    assert len(result) == 2 

def test_transform_matches_adiciona_coluna_result(sample_matches):
    result = transform_matches(sample_matches)
    assert 'result' in result.columns

def test_transform_matches_resultado_home(sample_matches):
    result = transform_matches(sample_matches)
    arsenal_game = result[result['match_id'] == 1]
    assert arsenal_game.iloc[0]['result'] == 'HOME'  # Arsenal 2x1 Chelsea

def test_transform_matches_resultado_draw(sample_matches):
    result = transform_matches(sample_matches)
    draw_game = result[result['match_id'] == 2]
    assert draw_game.iloc[0]['result'] == 'DRAW'  # Chelsea 0x0 Liverpool

def test_transform_matches_converte_data(sample_matches):
    result = transform_matches(sample_matches)
    assert pd.api.types.is_datetime64_any_dtype(result['date'])
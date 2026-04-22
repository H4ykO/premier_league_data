import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from ingestion.fetch_data import fetch_league_standings, fetch_matches

# Mock da API — evita chamadas reais
@pytest.fixture
def mock_standings_response():
    return {
        "standings": [{
            "table": [
                {
                    "position": 1,
                    "team": {"name": "Arsenal"},
                    "playedGames": 10,
                    "won": 7,
                    "draw": 2,
                    "lost": 1,
                    "goalsFor": 20,
                    "goalsAgainst": 8,
                    "points": 23
                }
            ]
        }]
    }

@pytest.fixture
def mock_matches_response():
    return {
        "matches": [
            {
                "id": 1,
                "utcDate": "2024-01-01T15:00:00Z",
                "homeTeam": {"name": "Arsenal"},
                "awayTeam": {"name": "Chelsea"},
                "score": {"fullTime": {"home": 2, "away": 1}},
                "status": "FINISHED"
            }
        ]
    }

# Testes — fetch_league_standings
@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_retorna_dataframe(mock_get, mock_standings_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_standings_response

    result = fetch_league_standings()
    assert isinstance(result, pd.DataFrame)

@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_tem_colunas_corretas(mock_get, mock_standings_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_standings_response

    result = fetch_league_standings()
    expected_columns = ['position', 'team', 'played', 'won', 'draw', 'lost', 'goals_for', 'goals_against', 'points']
    assert list(result.columns) == expected_columns

@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_retorna_dados_corretos(mock_get, mock_standings_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_standings_response

    result = fetch_league_standings()
    assert result.iloc[0]['team'] == 'Arsenal'
    assert result.iloc[0]['points'] == 23

# ─────────────────────────────────────────
# Testes — fetch_matches
# ─────────────────────────────────────────
@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_retorna_dataframe(mock_get, mock_matches_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_matches_response

    result = fetch_matches()
    assert isinstance(result, pd.DataFrame)

@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_tem_colunas_corretas(mock_get, mock_matches_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_matches_response

    result = fetch_matches()
    expected_columns = ['match_id', 'date', 'home_team', 'away_team', 'home_score', 'away_score', 'status']
    assert list(result.columns) == expected_columns

@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_retorna_dados_corretos(mock_get, mock_matches_response):
    mock_get.return_value = MagicMock()
    mock_get.return_value.json.return_value = mock_matches_response

    result = fetch_matches()
    assert result.iloc[0]['home_team'] == 'Arsenal'
    assert result.iloc[0]['away_team'] == 'Chelsea'
    assert result.iloc[0]['status'] == 'FINISHED'
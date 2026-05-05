import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from ingestion.fetch_data import fetch_league_standings, fetch_matches


def make_mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    return mock


@pytest.fixture
def mock_standings_response():
    return {
        "season": {"startDate": "2024-08-01"},
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
        "filters": {"season": "2024"},
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


# ─── fetch_league_standings ───────────────────────────────────────────────────

@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_retorna_dataframe(mock_get, mock_standings_response):
    mock_get.return_value = make_mock_response(mock_standings_response)
    result = fetch_league_standings()
    assert isinstance(result, pd.DataFrame)


@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_tem_colunas_corretas(mock_get, mock_standings_response):
    mock_get.return_value = make_mock_response(mock_standings_response)
    result = fetch_league_standings()
    expected = ['position', 'team', 'season', 'played', 'won', 'drawn', 'lost',
                'goals_for', 'goals_against', 'points']
    assert list(result.columns) == expected


@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_retorna_dados_corretos(mock_get, mock_standings_response):
    mock_get.return_value = make_mock_response(mock_standings_response)
    result = fetch_league_standings()
    assert result.iloc[0]['team'] == 'Arsenal'
    assert result.iloc[0]['points'] == 23


@patch('ingestion.fetch_data.requests.get')
def test_fetch_standings_season_explicita(mock_get, mock_standings_response):
    mock_get.return_value = make_mock_response(mock_standings_response)
    result = fetch_league_standings(season=2023)
    assert result.iloc[0]['season'] == 2023
    # verifica que o param foi passado na chamada
    _, kwargs = mock_get.call_args
    assert kwargs['params'] == {'season': 2023}


# ─── fetch_matches ────────────────────────────────────────────────────────────

@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_retorna_dataframe(mock_get, mock_matches_response):
    mock_get.return_value = make_mock_response(mock_matches_response)
    result = fetch_matches(seasons=[2024])
    assert isinstance(result, pd.DataFrame)


@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_tem_colunas_corretas(mock_get, mock_matches_response):
    mock_get.return_value = make_mock_response(mock_matches_response)
    result = fetch_matches(seasons=[2024])
    expected = ['match_id', 'season', 'date', 'home_team', 'away_team',
                'home_score', 'away_score', 'status']
    assert list(result.columns) == expected


@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_retorna_dados_corretos(mock_get, mock_matches_response):
    mock_get.return_value = make_mock_response(mock_matches_response)
    result = fetch_matches(seasons=[2024])
    assert result.iloc[0]['home_team'] == 'Arsenal'
    assert result.iloc[0]['away_team'] == 'Chelsea'
    assert result.iloc[0]['status'] == 'FINISHED'
    assert result.iloc[0]['season'] == 2024


@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_multi_season_chama_api_duas_vezes(mock_get, mock_matches_response):
    mock_get.return_value = make_mock_response(mock_matches_response)
    result = fetch_matches(seasons=[2023, 2024])
    assert mock_get.call_count == 2
    # dois jogos (um por season) concatenados
    assert len(result) == 2


@patch('ingestion.fetch_data.requests.get')
def test_fetch_matches_multi_season_tem_coluna_season_correta(mock_get, mock_matches_response):
    def side_effect(url, headers, params):
        return make_mock_response(mock_matches_response)

    mock_get.side_effect = side_effect
    result = fetch_matches(seasons=[2023, 2024])
    assert set(result['season'].tolist()) == {2023, 2024}

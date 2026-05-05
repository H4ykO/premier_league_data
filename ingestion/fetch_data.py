import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
BASE_URL = 'https://api.football-data.org/v4'
headers = {'X-Auth-Token': API_KEY}


def fetch_league_standings(season: int | None = None) -> pd.DataFrame:
    url = f'{BASE_URL}/competitions/PL/standings'
    params = {'season': season} if season is not None else {}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if 'standings' not in data:
        error_msg = data.get('message', 'resposta inesperada da API')
        raise RuntimeError(f'Erro ao buscar standings: {error_msg}')

    standings = []
    for team in data['standings'][0]['table']:
        standings.append({
            'position': team['position'],
            'team': team['team']['name'],
            'season': data['season']['startDate'][:4] if season is None else season,
            'played': team['playedGames'],
            'won': team['won'],
            'drawn': team['draw'],
            'lost': team['lost'],
            'goals_for': team['goalsFor'],
            'goals_against': team['goalsAgainst'],
            'points': team['points']
        })
    return pd.DataFrame(standings)


def fetch_matches(seasons: list[int] | None = None) -> pd.DataFrame:
    if seasons is None:
        seasons = [None]

    all_matches = []
    for season in seasons:
        url = f'{BASE_URL}/competitions/PL/matches'
        params = {'season': season} if season is not None else {}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        season_value = season if season is not None else int(data['filters']['season'][:4])

        if 'matches' not in data:
            error_msg = data.get('message', 'resposta inesperada da API')
            print(f'⚠️  season={season_value} ignorada: {error_msg}')
            continue

        for match in data['matches']:
            all_matches.append({
                'match_id': match['id'],
                'season': season_value,
                'date': match['utcDate'][:10],
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'home_score': match['score']['fullTime']['home'],
                'away_score': match['score']['fullTime']['away'],
                'status': match['status']
            })

    return pd.DataFrame(all_matches)

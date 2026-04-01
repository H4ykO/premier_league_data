import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
BASE_URL = 'https://api.football-data.org/v4'
headers = {'X-Auth-Token': API_KEY}

def fetch_league_standings():
    url = f'{BASE_URL}/competitions/PL/standings'
    response = requests.get(url, headers=headers)
    data = response.json()
    
    standings = []
    for team in data['standings'][0]['table']:
        standings.append({
            'position': team['position'],
            'team': team['team']['name'],
            'played': team['playedGames'],
            'won': team['won'],
            'draw': team['draw'],
            'lost': team['lost'],
            'goals_for': team['goalsFor'],
            'goals_against': team['goalsAgainst'],
            'points': team['points']
        })
    return pd.DataFrame(standings)

def fetch_matches():
    url = f'{BASE_URL}/competitions/PL/matches'
    response = requests.get(url, headers=headers)
    data = response.json()

    matches = []
    for match in data['matches']:
        matches.append({
            'match_id': match ['id'],
            'date': match['utcDate'][:10],
            'home_team': match['homeTeam']['name'],
            'away_team': match['awayTeam']['name'],
            'home_score': match['score']['fullTime']['home'],
            'away_score': match['score']['fullTime']['away'],
            'status': match['status']
        })
    return pd.DataFrame(matches)
   


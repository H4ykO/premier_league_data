from pyexpat import features
import pandas as pd
import numpy as np
import os
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)

def load_data():
    matches = pd.read_sql('SELECT * FROM matches ORDER BY date ASC', engine)
    standings = pd.read_sql('SELECT * FROM standings ORDER BY position ASC', engine)
    matches['date'] = pd.to_datetime(matches['date'])
    return matches, standings

def calc_goals_avg(matches, team, date, n=5):
    home = matches[(matches['home_team'] == team) & (matches['date'] < date)].tail(n)
    away = matches[(matches['away_team'] == team) & (matches['date'] < date)].tail(n)

    goals_scored = []
    goals_conceded = []

    for _, row in home.iterrows():
        if pd.notna(row['home_score']):
            goals_scored.append(row['home_score'])
            goals_conceded.append(row['away_score'])

    for _, row in away.iterrows():
        if pd.notna(row['away_score']):
            goals_scored.append(row['away_score'])
            goals_conceded.append(row['home_score'])

    all_scored = goals_scored[-n:] if len(goals_scored) >= n else goals_scored
    all_conceded = goals_conceded[-n:] if len(goals_conceded) >= n else goals_conceded

    avg_scored = np.mean(all_scored) if all_scored else 0.0
    avg_conceded = np.mean(all_conceded) if all_conceded else 0.0

    return round(avg_scored, 2), round(avg_conceded, 2)

def get_position(standings, team):
    row = standings[standings['team'] == team]
    if not row.empty:
        return int(row['position'].values[0])
    return 10

def build_features(matches, standings):
    features = []
    labels = []

    finished = matches[matches['result'].notna()].copy()

    for _, row in finished.iterrows():
        home_team = row['home_team']
        away_team = row['away_team']
        date = row['date']

        home_scored, home_conceded = calc_goals_avg(matches, home_team, date)
        away_scored, away_conceded = calc_goals_avg(matches, away_team, date)

        home_pos = get_position(standings, home_team)
        away_pos = get_position(standings, away_team)

        features.append([
            home_pos,
            away_pos,
            home_scored,
            home_conceded,
            away_scored,
            away_conceded,
        ])
        labels.append(row['result'])

    return pd.DataFrame(features, columns=[
        'home_position', 'away_position',
        'home_avg_scored', 'home_avg_conceded',
        'away_avg_scored', 'away_avg_conceded'
    ]), labels

def train_model():
    matches, standings = load_data()
    X, y = build_features(matches, standings)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    model = XGBClassifier(
        n_estimators=50,        
        max_depth=2,            
        learning_rate=0.05,     
        subsample=0.8,          
        colsample_bytree=0.8,  
        eval_metric='mlogloss',
        random_state=42
)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f'Accuracy: {acc:.2f}')

    return model, le, matches, standings

def predict_match(model, le, matches, standings, home_team, away_team):
    today = pd.Timestamp.now()

    home_scored, home_conceded = calc_goals_avg(matches, home_team, today)
    away_scored, away_conceded = calc_goals_avg(matches, away_team, today)
    home_pos = get_position(standings, home_team)
    away_pos = get_position(standings, away_team)

    features = [[
        home_pos,
        away_pos,
        home_scored,
        home_conceded,
        away_scored,
        away_conceded
    ]]

    prediction_encoded = model.predict(features)[0]
    prediction = le.inverse_transform([prediction_encoded])[0]

    probability = model.predict_proba(features)[0]
    classes = le.inverse_transform(range(len(le.classes_)))

    proba_dict = {cls: round(prob * 100, 1) for cls, prob in zip(classes, probability)}

    return prediction, proba_dict
import pandas as pd
import numpy as np
import os
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import accuracy_score, log_loss
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
    matches['date'] = pd.to_datetime(matches['date'])
    return matches


# ─── Posição sem leakage ──────────────────────────────────────────────────────

def _build_positions_history(matches: pd.DataFrame) -> dict:
    """
    Pre-computa {date: {team: position}} usando resultados acumulados ATÉ
    aquela data. O snapshot é salvo ANTES de processar o dia, garantindo
    que a posição reflete apenas o passado.
    """
    finished = matches[matches['result'].notna()].sort_values('date')
    points: dict = {}
    history: dict = {}

    for date, group in finished.groupby('date'):
        ranked = sorted(points.items(), key=lambda x: -x[1])
        history[date] = {t: i + 1 for i, (t, _) in enumerate(ranked)}

        for _, row in group.iterrows():
            h, a = row['home_team'], row['away_team']
            points.setdefault(h, 0)
            points.setdefault(a, 0)
            if row['result'] == 'HOME':
                points[h] += 3
            elif row['result'] == 'AWAY':
                points[a] += 3
            else:
                points[h] += 1
                points[a] += 1

    return history


def _get_position_at_date(history: dict, team: str, date, default: int = 10) -> int:
    candidates = [d for d in history if d <= date]
    if not candidates:
        return default
    return history[max(candidates)].get(team, default)


# ─── Features por jogo ───────────────────────────────────────────────────────

def calc_goals_avg(matches: pd.DataFrame, team: str, date, n: int = 5):
    home = matches[(matches['home_team'] == team) & (matches['date'] < date)].tail(n)
    away = matches[(matches['away_team'] == team) & (matches['date'] < date)].tail(n)

    goals_scored, goals_conceded = [], []

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

    return (
        round(np.mean(all_scored) if all_scored else 0.0, 2),
        round(np.mean(all_conceded) if all_conceded else 0.0, 2),
    )


def calc_form(matches: pd.DataFrame, team: str, date, n: int = 5) -> int:
    """Pontos acumulados nos últimos n jogos antes de date."""
    past_home = matches[
        (matches['home_team'] == team) & (matches['date'] < date) & matches['result'].notna()
    ][['date', 'result']].copy()
    past_home['pts'] = past_home['result'].map({'HOME': 3, 'DRAW': 1, 'AWAY': 0})

    past_away = matches[
        (matches['away_team'] == team) & (matches['date'] < date) & matches['result'].notna()
    ][['date', 'result']].copy()
    past_away['pts'] = past_away['result'].map({'HOME': 0, 'DRAW': 1, 'AWAY': 3})

    all_games = pd.concat([past_home, past_away]).sort_values('date').tail(n)
    return int(all_games['pts'].sum()) if not all_games.empty else 0


def calc_venue_win_rate(matches: pd.DataFrame, team: str, date, venue: str, n: int = 10) -> float:
    """Win rate específico (casa ou fora) nos últimos n jogos naquele mando."""
    if venue == 'home':
        past = matches[
            (matches['home_team'] == team) & (matches['date'] < date) & matches['result'].notna()
        ].tail(n)
        if past.empty:
            return 0.33
        return round((past['result'] == 'HOME').mean(), 2)
    else:
        past = matches[
            (matches['away_team'] == team) & (matches['date'] < date) & matches['result'].notna()
        ].tail(n)
        if past.empty:
            return 0.33
        return round((past['result'] == 'AWAY').mean(), 2)


def calc_h2h(matches: pd.DataFrame, home_team: str, away_team: str, date, n: int = 3) -> int:
    """Pontos acumulados pelo home_team nos últimos n confrontos diretos antes de date."""
    h2h = matches[
        (
            ((matches['home_team'] == home_team) & (matches['away_team'] == away_team)) |
            ((matches['home_team'] == away_team) & (matches['away_team'] == home_team))
        ) &
        (matches['date'] < date) &
        matches['result'].notna()
    ].tail(n)

    if h2h.empty:
        return 0

    pts = 0
    for _, row in h2h.iterrows():
        if row['home_team'] == home_team:
            pts += {'HOME': 3, 'DRAW': 1, 'AWAY': 0}[row['result']]
        else:
            pts += {'HOME': 0, 'DRAW': 1, 'AWAY': 3}[row['result']]
    return pts


# ─── Build features ───────────────────────────────────────────────────────────

def build_features(matches: pd.DataFrame):
    features, labels, dates = [], [], []
    history = _build_positions_history(matches)
    finished = matches[matches['result'].notna()].copy()

    for _, row in finished.iterrows():
        home_team = row['home_team']
        away_team = row['away_team']
        date = row['date']

        home_scored, home_conceded = calc_goals_avg(matches, home_team, date)
        away_scored, away_conceded = calc_goals_avg(matches, away_team, date)

        # Gols ajustados pela força defensiva do adversário
        home_scored_adj = round(home_scored / max(away_conceded, 0.5), 2)
        away_scored_adj = round(away_scored / max(home_conceded, 0.5), 2)

        features.append([
            _get_position_at_date(history, home_team, date),
            _get_position_at_date(history, away_team, date),
            home_scored_adj,
            home_conceded,
            away_scored_adj,
            away_conceded,
            calc_form(matches, home_team, date),
            calc_form(matches, away_team, date),
            calc_venue_win_rate(matches, home_team, date, 'home'),
            calc_venue_win_rate(matches, away_team, date, 'away'),
            calc_h2h(matches, home_team, away_team, date),
        ])
        labels.append(row['result'])
        dates.append(date)

    X = pd.DataFrame(features, columns=[
        'home_position', 'away_position',
        'home_scored_adj', 'home_avg_conceded',
        'away_scored_adj', 'away_avg_conceded',
        'home_form_pts', 'away_form_pts',
        'home_venue_wr', 'away_venue_wr',
        'h2h_home_pts',
    ])
    return X, labels, dates


# ─── Métricas ─────────────────────────────────────────────────────────────────

def brier_score_multiclass(y_true_onehot: np.ndarray, proba: np.ndarray) -> float:
    return float(np.mean(np.sum((proba - y_true_onehot) ** 2, axis=1)))


# ─── Treino ───────────────────────────────────────────────────────────────────

def train_model():
    matches = load_data()
    X, y, dates = build_features(matches)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    n_classes = len(le.classes_)

    order = np.argsort(dates)
    X = X.iloc[order].reset_index(drop=True)
    y_encoded = y_encoded[order]

    # Tuning de hiperparâmetros com validação temporal
    print('🔍 Buscando melhores hiperparâmetros...')
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [2, 3, 4],
        'learning_rate': [0.01, 0.05, 0.1],
    }
    gs = GridSearchCV(
        XGBClassifier(subsample=0.8, colsample_bytree=0.8,
                      eval_metric='mlogloss', random_state=42),
        param_grid,
        cv=TimeSeriesSplit(n_splits=3),
        scoring='neg_log_loss',
        n_jobs=-1,
    )
    gs.fit(X, y_encoded)
    best_params = gs.best_params_
    print(f'   Melhores parâmetros: {best_params}')

    # Validação com 5 folds temporais
    tscv = TimeSeriesSplit(n_splits=5)
    fold_metrics = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), start=1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y_encoded[train_idx], y_encoded[test_idx]

        model = XGBClassifier(
            **best_params,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='mlogloss',
            random_state=42,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        ll = log_loss(y_test, y_proba, labels=list(range(n_classes)))
        brier = brier_score_multiclass(np.eye(n_classes)[y_test], y_proba)

        fold_metrics.append({'accuracy': acc, 'log_loss': ll, 'brier': brier})
        print(f'Fold {fold}: accuracy={acc:.3f}  log_loss={ll:.3f}  brier={brier:.3f}')

    accs = [m['accuracy'] for m in fold_metrics]
    lls = [m['log_loss'] for m in fold_metrics]
    briers = [m['brier'] for m in fold_metrics]
    print(f'\nMédia ± std (5 folds)')
    print(f'  Accuracy : {np.mean(accs):.3f} ± {np.std(accs):.3f}')
    print(f'  Log-loss : {np.mean(lls):.3f} ± {np.std(lls):.3f}')
    print(f'  Brier    : {np.mean(briers):.3f} ± {np.std(briers):.3f}')

    # Modelo final calibrado treinado em todo o dataset
    final_model = CalibratedClassifierCV(
        XGBClassifier(
            **best_params,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='mlogloss',
            random_state=42,
        ),
        method='isotonic',
        cv=TimeSeriesSplit(n_splits=3),
    )
    final_model.fit(X, y_encoded)

    return final_model, le, matches


# ─── Inferência ───────────────────────────────────────────────────────────────

def predict_match(model, le, matches, home_team: str, away_team: str):
    today = pd.Timestamp.now()
    history = _build_positions_history(matches)

    home_scored, home_conceded = calc_goals_avg(matches, home_team, today)
    away_scored, away_conceded = calc_goals_avg(matches, away_team, today)

    home_scored_adj = round(home_scored / max(away_conceded, 0.5), 2)
    away_scored_adj = round(away_scored / max(home_conceded, 0.5), 2)

    features = [[
        _get_position_at_date(history, home_team, today),
        _get_position_at_date(history, away_team, today),
        home_scored_adj,
        home_conceded,
        away_scored_adj,
        away_conceded,
        calc_form(matches, home_team, today),
        calc_form(matches, away_team, today),
        calc_venue_win_rate(matches, home_team, today, 'home'),
        calc_venue_win_rate(matches, away_team, today, 'away'),
        calc_h2h(matches, home_team, away_team, today),
    ]]

    prediction_encoded = model.predict(features)[0]
    prediction = le.inverse_transform([prediction_encoded])[0]

    probability = model.predict_proba(features)[0]
    classes = le.inverse_transform(range(len(le.classes_)))

    proba_dict = {cls: round(prob * 100, 1) for cls, prob in zip(classes, probability)}

    return prediction, proba_dict

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import TimeSeriesSplit
from model.predict import (
    _build_positions_history,
    _get_position_at_date,
    calc_goals_avg,
    calc_form,
    calc_venue_win_rate,
    calc_h2h,
    build_features,
    brier_score_multiclass,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_matches():
    return pd.DataFrame([
        {'match_id': 1, 'season': 2024, 'date': pd.Timestamp('2024-01-01'),
         'home_team': 'Arsenal', 'away_team': 'Chelsea',
         'home_score': 2, 'away_score': 1, 'result': 'HOME'},
        {'match_id': 2, 'season': 2024, 'date': pd.Timestamp('2024-01-08'),
         'home_team': 'Chelsea', 'away_team': 'Liverpool',
         'home_score': 0, 'away_score': 0, 'result': 'DRAW'},
        {'match_id': 3, 'season': 2024, 'date': pd.Timestamp('2024-01-15'),
         'home_team': 'Arsenal', 'away_team': 'Liverpool',
         'home_score': 1, 'away_score': 3, 'result': 'AWAY'},
        {'match_id': 4, 'season': 2024, 'date': pd.Timestamp('2024-01-22'),
         'home_team': 'Liverpool', 'away_team': 'Arsenal',
         'home_score': 2, 'away_score': 0, 'result': 'HOME'},
    ])


# ─── _build_positions_history ─────────────────────────────────────────────────

def test_positions_history_snapshot_antes_do_dia(sample_matches):
    history = _build_positions_history(sample_matches)
    # No dia 2024-01-01 (primeiro jogo) ainda não há histórico acumulado
    snap = history[pd.Timestamp('2024-01-01')]
    assert snap == {}, "Snapshot no 1º dia deve estar vazio — nenhuma partida foi disputada antes"


def test_positions_history_apos_primeira_rodada(sample_matches):
    history = _build_positions_history(sample_matches)
    # No dia 08/01, Arsenal já tem 3 pts (ganhou em 01/01) e Chelsea tem 0
    snap = history[pd.Timestamp('2024-01-08')]
    assert snap['Arsenal'] < snap['Chelsea'], "Arsenal deve estar acima do Chelsea após vencer o 1º jogo"


def test_get_position_at_date_retorna_default_sem_historico(sample_matches):
    history = _build_positions_history(sample_matches)
    pos = _get_position_at_date(history, 'Arsenal', pd.Timestamp('2023-12-01'))
    assert pos == 10


def test_get_position_at_date_usa_snapshot_anterior(sample_matches):
    history = _build_positions_history(sample_matches)
    # Entre 01/01 e 08/01, Arsenal está em 1º
    pos = _get_position_at_date(history, 'Arsenal', pd.Timestamp('2024-01-10'))
    assert pos == 1


# ─── calc_goals_avg ───────────────────────────────────────────────────────────

def test_calc_goals_avg_retorna_zero_sem_historico(sample_matches):
    avg_scored, avg_conceded = calc_goals_avg(sample_matches, 'Arsenal', pd.Timestamp('2023-12-01'))
    assert avg_scored == 0.0
    assert avg_conceded == 0.0


def test_calc_goals_avg_usa_apenas_jogos_anteriores(sample_matches):
    # Arsenal só jogou match_id=1 antes de 2024-01-15
    avg_scored, avg_conceded = calc_goals_avg(sample_matches, 'Arsenal', pd.Timestamp('2024-01-15'))
    assert avg_scored == 2.0
    assert avg_conceded == 1.0


# ─── calc_form ────────────────────────────────────────────────────────────────

def test_calc_form_retorna_zero_sem_historico(sample_matches):
    assert calc_form(sample_matches, 'Arsenal', pd.Timestamp('2023-12-01')) == 0


def test_calc_form_contabiliza_vitoria_em_casa(sample_matches):
    # Arsenal ganhou match_id=1 (3 pts) antes de 2024-01-15
    pts = calc_form(sample_matches, 'Arsenal', pd.Timestamp('2024-01-15'))
    assert pts == 3


def test_calc_form_contabiliza_empate_fora(sample_matches):
    # Chelsea empatou match_id=2 (1 pt) antes de 2024-01-15
    pts = calc_form(sample_matches, 'Chelsea', pd.Timestamp('2024-01-15'))
    assert pts == 1


def test_calc_form_contabiliza_derrota(sample_matches):
    # Chelsea perdeu match_id=1 (0 pts) antes de 2024-01-08
    pts = calc_form(sample_matches, 'Chelsea', pd.Timestamp('2024-01-08'))
    assert pts == 0


# ─── calc_venue_win_rate ──────────────────────────────────────────────────────

def test_calc_venue_win_rate_retorna_prior_sem_historico(sample_matches):
    wr = calc_venue_win_rate(sample_matches, 'Arsenal', pd.Timestamp('2023-12-01'), 'home')
    assert wr == 0.33


def test_calc_venue_win_rate_home_correto(sample_matches):
    # Arsenal jogou 2 jogos em casa antes de 2024-01-22: ganhou match_id=1, perdeu match_id=3 → 50%
    wr = calc_venue_win_rate(sample_matches, 'Arsenal', pd.Timestamp('2024-01-22'), 'home')
    assert wr == 0.5


def test_calc_venue_win_rate_away_correto(sample_matches):
    # Liverpool jogou fora em match_id=2 e empatou → win rate away = 0%
    wr = calc_venue_win_rate(sample_matches, 'Liverpool', pd.Timestamp('2024-01-15'), 'away')
    assert wr == 0.0


# ─── calc_h2h ─────────────────────────────────────────────────────────────────

def test_calc_h2h_retorna_zero_sem_historico(sample_matches):
    h2h = calc_h2h(sample_matches, 'Arsenal', 'Chelsea', pd.Timestamp('2023-12-01'))
    assert h2h == 0


def test_calc_h2h_pontos_diretos(sample_matches):
    # Arsenal (home) ganhou de Chelsea em match_id=1 → 3 pts
    h2h = calc_h2h(sample_matches, 'Arsenal', 'Chelsea', pd.Timestamp('2024-12-31'))
    assert h2h == 3


def test_calc_h2h_pontos_quando_time_jogou_fora(sample_matches):
    # Liverpool ganhou os 2 H2H contra Arsenal:
    # match_id=3: Liverpool jogou fora, result=AWAY → 3 pts
    # match_id=4: Liverpool jogou em casa, result=HOME → 3 pts
    # Total = 6 pts
    h2h = calc_h2h(sample_matches, 'Liverpool', 'Arsenal', pd.Timestamp('2024-12-31'))
    assert h2h == 6


# ─── brier_score_multiclass ───────────────────────────────────────────────────

def test_brier_score_perfeito_e_zero():
    y_onehot = np.array([[1, 0, 0], [0, 1, 0]])
    proba = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert brier_score_multiclass(y_onehot, proba) == pytest.approx(0.0)


def test_brier_score_previsao_errada_com_confianca():
    y_onehot = np.array([[1, 0, 0]])
    proba = np.array([[0.0, 0.0, 1.0]])
    assert brier_score_multiclass(y_onehot, proba) == pytest.approx(2.0)


# ─── Split temporal — garantia de ordem ──────────────────────────────────────

def test_timeseries_split_preserva_ordem_temporal():
    n_samples = 100
    dates = pd.date_range('2020-01-01', periods=n_samples, freq='W')
    X = pd.DataFrame({'feature': range(n_samples)})

    tscv = TimeSeriesSplit(n_splits=5)
    for train_idx, test_idx in tscv.split(X):
        assert dates[train_idx].max() < dates[test_idx].min(), (
            f"Leakage temporal: max treino={dates[train_idx].max()} "
            f">= min teste={dates[test_idx].min()}"
        )

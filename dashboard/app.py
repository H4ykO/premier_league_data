import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from model.predict import train_model, predict_match, calc_goals_avg, calc_form, calc_venue_win_rate

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)


def _current_season():
    today = datetime.date.today()
    return today.year if today.month >= 8 else today.year - 1


season = _current_season()
st.set_page_config(page_title='Premier League Dashboard', page_icon='⚽')
st.title(f'📊 Premier League {season}/{season + 1}')

# Classificação — só temporada corrente
st.subheader('Classificação Atual')
standings = pd.read_sql(
    'SELECT * FROM standings WHERE season = (SELECT MAX(season) FROM standings) ORDER BY position',
    engine
)
st.dataframe(standings, use_container_width=True)

# Top 10
st.subheader('Top 10 Times por Pontos')
st.bar_chart(standings.head(10).set_index('team')['points'])

# Últimos jogos
st.subheader('Últimos Jogos')
matches_db = pd.read_sql('SELECT * FROM matches ORDER BY date DESC LIMIT 10', engine)
st.dataframe(matches_db, use_container_width=True)

# Previsão
st.subheader('Previsão de Resultados')


@st.cache_resource
def get_model():
    return train_model()


model, le, matches = get_model()

teams = standings['team'].tolist()
home = st.selectbox('Time da Casa', teams)
away = st.selectbox('Time Visitante', [t for t in teams if t != home])

if st.button('Prever Resultado'):
    prediction, probabilities = predict_match(model, le, matches, home, away)

    result_map = {
        "HOME": f"🏠 Vitória do {home}",
        "AWAY": f"✈️ Vitória do {away}",
        "DRAW": "🤝 Empate"
    }

    st.success(f'Resultado previsto: **{result_map[prediction]}**')

    st.write('Probabilidades:')
    col1, col2, col3 = st.columns(3)
    col1.metric(f"🏠 {home}", f"{probabilities.get('HOME', 0):.1f}%")
    col2.metric("🤝 Empate", f"{probabilities.get('DRAW', 0):.1f}%")
    col3.metric(f"✈️ {away}", f"{probabilities.get('AWAY', 0):.1f}%")

    today = pd.Timestamp.now()
    st.write('**Features usadas para previsão:**')

    c1, c2 = st.columns(2)
    c1.metric("📍 Posição Casa", int(standings[standings['team'] == home]['position'].values[0]))
    c2.metric("📍 Posição Visitante", int(standings[standings['team'] == away]['position'].values[0]))

    h_scored, h_conc = calc_goals_avg(matches, home, today)
    a_scored, a_conc = calc_goals_avg(matches, away, today)
    c3, c4 = st.columns(2)
    c3.metric("⚽ Gols/jogo Casa", h_scored)
    c4.metric("⚽ Gols/jogo Visitante", a_scored)

    c5, c6 = st.columns(2)
    c5.metric("📈 Forma Casa (pts)", calc_form(matches, home, today))
    c6.metric("📈 Forma Visitante (pts)", calc_form(matches, away, today))

    c7, c8 = st.columns(2)
    c7.metric("🏟️ Win Rate Casa em Casa", f"{calc_venue_win_rate(matches, home, today, 'home'):.0%}")
    c8.metric("✈️ Win Rate Visitante Fora", f"{calc_venue_win_rate(matches, away, today, 'away'):.0%}")

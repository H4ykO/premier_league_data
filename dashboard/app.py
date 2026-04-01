import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from model.predict import train_model, predict_match

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

engine = create_engine(f'postgresql://{DB_USER}:@{DB_HOST}:{DB_PORT}/{DB_NAME}')

st.set_page_config(page_title='Premier League Dashboard', page_icon='⚽')
st.title('📊 Premier League 2025/2026')

#Classification
st.subheader('Classificação Atual')
standings = pd.read_sql('SELECT * FROM standings ORDER BY position', engine)
st.dataframe(standings, use_container_width=True)

#Points
st.subheader('Top 10 Times por Pontos')
top10 = standings.head(10)
st.bar_chart(top10.set_index('team')['points'])

#Last games
st.subheader('Últimos Jogos')
matches = pd.read_sql('SELECT * FROM matches ORDER BY date DESC LIMIT 10', engine)
st.dataframe(matches, use_container_width=True)

#Forecast
st.subheader('Previsão de Resultados')

@st.cache_resource
def get_model():
    return train_model()

model, scaler, matches, standings = get_model()

teams = standings['team'].tolist()
home = st.selectbox('Time da Casa', teams)
away = st.selectbox('Time Visitante', [t for t in teams if t != home])

if st.button('Prever Resultado'):
    prediction, probabilities = predict_match(model, scaler, matches, standings, home, away)

    result_map = {
        "HOME": f"🏠 Vitória do {home}",
        "AWAY": f"✈️ Vitória do {away}",
        "DRAW": "🤝 Empate"
    }

    st.success(f'Resultado previsto: **{result_map[prediction]}**')

    st.write('Probabilidades:')
    col1, col2, col3 = st.columns(3)
    col1.metric(f"🏠 {home}", f"{probabilities.get('HOME', 0)}%")
    col2.metric("🤝 Empate", f"{probabilities.get('DRAW', 0)}%")
    col3.metric(f"✈️ {away}", f"{probabilities.get('AWAY', 0)}%")

    st.write('Features usadas para previsão:')
    pos_col1, pos_col2 = st.columns(2)
    pos_col1.metric("📍 Posição (casa)", int(standings[standings['team'] == home]['position'].values[0]))
    pos_col2.metric("📍 Posição (visitante)", int(standings[standings['team'] == away]['position'].values[0]))

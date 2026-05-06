import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from model.predict import (
    train_model, predict_match, calc_goals_avg, calc_form,
    calc_venue_win_rate, _build_positions_history,
)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)


def _current_season() -> int:
    today = datetime.date.today()
    return today.year if today.month >= 8 else today.year - 1


@st.cache_data
def load_matches() -> pd.DataFrame:
    df = pd.read_sql('SELECT * FROM matches ORDER BY date ASC', engine)
    df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data
def load_standings(sel_season: int) -> pd.DataFrame:
    return pd.read_sql(
        'SELECT * FROM standings WHERE season = %(s)s ORDER BY position',
        engine, params={'s': sel_season},
    )


@st.cache_data
def load_available_seasons() -> list[int]:
    return sorted(
        pd.read_sql('SELECT DISTINCT season FROM standings', engine)['season'].tolist(),
        reverse=True,
    )


@st.cache_resource
def get_model():
    return train_model()


def form_chips_html(matches: pd.DataFrame, team: str, n: int = 10) -> str:
    past = matches[
        ((matches['home_team'] == team) | (matches['away_team'] == team)) &
        matches['result'].notna()
    ].sort_values('date').tail(n)

    chips = []
    for _, row in past.iterrows():
        is_home = row['home_team'] == team
        win = (row['result'] == 'HOME' and is_home) or (row['result'] == 'AWAY' and not is_home)
        draw = row['result'] == 'DRAW'
        color, letter = ('#28a745', 'V') if win else ('#e6a817', 'E') if draw else ('#dc3545', 'D')
        chips.append(
            f'<span style="background:{color};color:white;padding:5px 11px;'
            f'border-radius:14px;margin:3px;font-weight:bold;font-size:14px">{letter}</span>'
        )
    return (
        '<div style="line-height:2.8">' + ''.join(chips) + '</div>'
        if chips else '<p style="color:gray">Sem dados</p>'
    )


# ─── Setup da página ──────────────────────────────────────────────────────────

season = _current_season()
st.set_page_config(page_title='Premier League Dashboard', page_icon='⚽', layout='wide')
st.title(f'📊 Premier League {season}/{season + 1}')

matches_all = load_matches()
available_seasons = load_available_seasons()
all_teams = sorted(matches_all['home_team'].unique().tolist())

tab1, tab2, tab3, tab4 = st.tabs([
    '🏆 Classificação', '⚽ Partidas', '📊 Análise de Time', '🔮 Previsão'
])


# ─── Aba 1: Classificação ─────────────────────────────────────────────────────

with tab1:
    sel_season_1 = st.selectbox('Temporada', available_seasons, key='season_tab1')
    standings = load_standings(sel_season_1)

    st.subheader(f'Tabela de Classificação — {sel_season_1}/{sel_season_1 + 1}')
    st.dataframe(standings, use_container_width=True)

    st.subheader('Gols Marcados vs Sofridos')
    fig_goals = go.Figure([
        go.Bar(name='Gols Marcados', x=standings['team'], y=standings['goals_for'],
               marker_color='#2ecc71'),
        go.Bar(name='Gols Sofridos', x=standings['team'], y=standings['goals_against'],
               marker_color='#e74c3c'),
    ])
    fig_goals.update_layout(
        barmode='group', xaxis_tickangle=-45,
        height=420, margin=dict(b=120), legend=dict(orientation='h', y=1.1),
    )
    st.plotly_chart(fig_goals, use_container_width=True)

    st.subheader('Top 10 — Aproveitamento (%)')
    top10 = standings.head(10).copy()
    top10['aproveitamento'] = (top10['win_rate'] * 100).round(1)
    fig_wr = px.bar(
        top10, x='aproveitamento', y='team', orientation='h',
        color='aproveitamento', color_continuous_scale='Greens',
        labels={'aproveitamento': 'Aproveitamento (%)', 'team': ''},
        height=380,
    )
    fig_wr.update_layout(yaxis=dict(autorange='reversed'), coloraxis_showscale=False)
    st.plotly_chart(fig_wr, use_container_width=True)


# ─── Aba 2: Partidas ─────────────────────────────────────────────────────────

with tab2:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_season_2 = st.selectbox('Temporada', available_seasons, key='season_tab2')
    with col_f2:
        team_filter = st.selectbox('Filtrar por time', ['Todos'] + all_teams, key='team_tab2')

    season_matches = matches_all[matches_all['season'] == sel_season_2].copy()

    if team_filter != 'Todos':
        display_matches = season_matches[
            (season_matches['home_team'] == team_filter) |
            (season_matches['away_team'] == team_filter)
        ]
    else:
        display_matches = season_matches

    st.subheader('Partidas')
    st.dataframe(
        display_matches[['date', 'home_team', 'home_score', 'away_score', 'away_team', 'result']]
        .sort_values('date', ascending=False).reset_index(drop=True),
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader('Distribuição de Resultados')
        result_counts = season_matches['result'].value_counts()
        labels_map = {'HOME': 'Vitória Casa', 'AWAY': 'Vitória Visitante', 'DRAW': 'Empate'}
        fig_pie = px.pie(
            values=result_counts.values,
            names=[labels_map.get(r, r) for r in result_counts.index],
            color=[labels_map.get(r, r) for r in result_counts.index],
            color_discrete_map={
                'Vitória Casa': '#2ecc71',
                'Empate': '#f39c12',
                'Vitória Visitante': '#e74c3c',
            },
            hole=0.42,
            height=360,
        )
        fig_pie.update_traces(textinfo='percent+label', textfont_size=13)
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.subheader('Média de Gols por Rodada')
        season_matches['total_goals'] = season_matches['home_score'] + season_matches['away_score']
        goals_by_date = (
            season_matches.groupby('date')['total_goals']
            .mean()
            .reset_index()
            .rename(columns={'total_goals': 'media'})
        )
        goals_by_date['media_movel'] = goals_by_date['media'].rolling(5, min_periods=1).mean()
        fig_gt = go.Figure([
            go.Scatter(x=goals_by_date['date'], y=goals_by_date['media'],
                       mode='markers', name='Por rodada', opacity=0.35,
                       marker=dict(color='#3498db', size=6)),
            go.Scatter(x=goals_by_date['date'], y=goals_by_date['media_movel'],
                       mode='lines', name='Média móvel (5)',
                       line=dict(color='#2c3e50', width=2.5)),
        ])
        fig_gt.update_layout(
            height=360, xaxis_title='', yaxis_title='Gols/jogo',
            legend=dict(orientation='h', y=-0.25), margin=dict(b=60),
        )
        st.plotly_chart(fig_gt, use_container_width=True)


# ─── Aba 3: Análise de Time ───────────────────────────────────────────────────

with tab3:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        selected_team = st.selectbox('Time', all_teams, key='team_tab3')
    with col_t2:
        sel_season_3 = st.selectbox('Temporada', available_seasons, key='season_tab3')

    team_matches = matches_all[
        ((matches_all['home_team'] == selected_team) | (matches_all['away_team'] == selected_team)) &
        (matches_all['season'] == sel_season_3)
    ].sort_values('date')

    if team_matches.empty:
        st.warning('Sem partidas para este time na temporada selecionada.')
    else:
        today = pd.Timestamp.now()

        wins = sum(
            1 for _, r in team_matches.iterrows()
            if (r['home_team'] == selected_team and r['result'] == 'HOME') or
               (r['away_team'] == selected_team and r['result'] == 'AWAY')
        )
        draws = int((team_matches['result'] == 'DRAW').sum())
        losses = len(team_matches) - wins - draws

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric('Jogos', len(team_matches))
        m2.metric('Vitórias', wins)
        m3.metric('Empates', draws)
        m4.metric('Derrotas', losses)
        m5.metric('Forma (últimos 5 pts)', calc_form(matches_all, selected_team, today))

        c1, c2 = st.columns(2)
        c1.metric('🏟️ Win Rate em Casa',
                  f"{calc_venue_win_rate(matches_all, selected_team, today, 'home'):.0%}")
        c2.metric('✈️ Win Rate Fora',
                  f"{calc_venue_win_rate(matches_all, selected_team, today, 'away'):.0%}")

        st.subheader('Forma Recente (últimos 10 jogos)')
        st.markdown(form_chips_html(matches_all, selected_team, n=10), unsafe_allow_html=True)

        col_pos, col_gols = st.columns(2)

        with col_pos:
            st.subheader('Evolução de Posição')
            history = _build_positions_history(
                matches_all[matches_all['season'] == sel_season_3]
            )
            pos_data = [
                {'date': d, 'posição': snap[selected_team]}
                for d, snap in sorted(history.items())
                if selected_team in snap
            ]
            if pos_data:
                df_pos = pd.DataFrame(pos_data)
                fig_pos = px.line(df_pos, x='date', y='posição',
                                  markers=True, color_discrete_sequence=['#3498db'],
                                  height=320)
                fig_pos.update_yaxes(autorange='reversed', title='Posição', dtick=2)
                fig_pos.update_xaxes(title='')
                fig_pos.update_layout(margin=dict(b=40))
                st.plotly_chart(fig_pos, use_container_width=True)
            else:
                st.info('Dados insuficientes para evolução de posição.')

        with col_gols:
            st.subheader('Gols por Jogo')
            gols_data = [
                {
                    'date': row['date'],
                    'Marcados': row['home_score'] if row['home_team'] == selected_team else row['away_score'],
                    'Sofridos': row['away_score'] if row['home_team'] == selected_team else row['home_score'],
                }
                for _, row in team_matches.iterrows()
            ]
            df_gols = pd.DataFrame(gols_data).sort_values('date')
            fig_gols = go.Figure([
                go.Scatter(x=df_gols['date'], y=df_gols['Marcados'],
                           mode='lines+markers', name='Marcados',
                           line=dict(color='#2ecc71', width=2)),
                go.Scatter(x=df_gols['date'], y=df_gols['Sofridos'],
                           mode='lines+markers', name='Sofridos',
                           line=dict(color='#e74c3c', width=2)),
            ])
            fig_gols.update_layout(
                height=320, xaxis_title='', yaxis_title='Gols',
                legend=dict(orientation='h', y=-0.3), margin=dict(b=60),
            )
            st.plotly_chart(fig_gols, use_container_width=True)


# ─── Aba 4: Previsão ─────────────────────────────────────────────────────────

with tab4:
    standings_latest = load_standings(max(available_seasons))
    teams_latest = standings_latest['team'].tolist()

    home = st.selectbox('Time da Casa', teams_latest, key='home_pred')
    away = st.selectbox('Time Visitante', [t for t in teams_latest if t != home], key='away_pred')

    # H2H automático
    h2h_matches = matches_all[
        ((matches_all['home_team'] == home) & (matches_all['away_team'] == away)) |
        ((matches_all['home_team'] == away) & (matches_all['away_team'] == home))
    ].sort_values('date', ascending=False).head(5)

    if not h2h_matches.empty:
        st.subheader(f'Últimos Confrontos Diretos — {home} vs {away}')
        st.dataframe(
            h2h_matches[['date', 'home_team', 'home_score', 'away_score', 'away_team', 'result']]
            .reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info('Sem histórico de confrontos diretos disponível.')

    # Comparativo lado a lado
    st.subheader('Comparativo')
    today = pd.Timestamp.now()
    h_scored, h_conc = calc_goals_avg(matches_all, home, today)
    a_scored, a_conc = calc_goals_avg(matches_all, away, today)

    def _pos(team: str) -> int | str:
        row = standings_latest[standings_latest['team'] == team]
        return int(row['position'].values[0]) if not row.empty else '-'

    comp_df = pd.DataFrame({
        'Métrica': ['Posição', 'Gols/jogo', 'Gols sofridos/jogo',
                    'Forma (últimos 5 pts)', 'Win Rate mando'],
        home: [
            _pos(home), h_scored, h_conc,
            calc_form(matches_all, home, today),
            f"{calc_venue_win_rate(matches_all, home, today, 'home'):.0%}",
        ],
        away: [
            _pos(away), a_scored, a_conc,
            calc_form(matches_all, away, today),
            f"{calc_venue_win_rate(matches_all, away, today, 'away'):.0%}",
        ],
    }).set_index('Métrica')
    st.dataframe(comp_df, use_container_width=True)

    # Forma recente dos dois times
    st.subheader('Forma Recente')
    col_fc1, col_fc2 = st.columns(2)
    with col_fc1:
        st.markdown(f'**{home}**')
        st.markdown(form_chips_html(matches_all, home), unsafe_allow_html=True)
    with col_fc2:
        st.markdown(f'**{away}**')
        st.markdown(form_chips_html(matches_all, away), unsafe_allow_html=True)

    if st.button('🔮 Prever Resultado'):
        with st.spinner('Treinando modelo...'):
            model, le, _ = get_model()

        prediction, probabilities = predict_match(model, le, matches_all, home, away)
        result_map = {
            'HOME': f'🏠 Vitória do {home}',
            'AWAY': f'✈️ Vitória do {away}',
            'DRAW': '🤝 Empate',
        }
        st.success(f'Resultado previsto: **{result_map[prediction]}**')

        col1, col2, col3 = st.columns(3)
        col1.metric(f'🏠 {home}', f"{probabilities.get('HOME', 0):.1f}%")
        col2.metric('🤝 Empate', f"{probabilities.get('DRAW', 0):.1f}%")
        col3.metric(f'✈️ {away}', f"{probabilities.get('AWAY', 0):.1f}%")

        proba_df = pd.DataFrame({
            'Resultado': [f'🏠 {home}', '🤝 Empate', f'✈️ {away}'],
            'Probabilidade': [
                probabilities.get('HOME', 0),
                probabilities.get('DRAW', 0),
                probabilities.get('AWAY', 0),
            ],
        })
        fig_proba = px.bar(
            proba_df, x='Resultado', y='Probabilidade',
            color='Probabilidade', color_continuous_scale='Blues',
            labels={'Probabilidade': 'Probabilidade (%)'},
            height=320,
        )
        fig_proba.update_layout(coloraxis_showscale=False, yaxis_range=[0, 100])
        st.plotly_chart(fig_proba, use_container_width=True)

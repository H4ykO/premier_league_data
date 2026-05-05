import os
import datetime
from dotenv import load_dotenv
from ingestion.fetch_data import fetch_league_standings, fetch_matches
from transformation.transform import transform_standings, transform_matches
from database.load import upsert

load_dotenv()


def _current_season() -> int:
    today = datetime.date.today()
    # A Premier League começa em agosto; antes disso a temporada corrente é do ano anterior
    return today.year if today.month >= 8 else today.year - 1


SEASONS = list(range(_current_season() - 2, _current_season() + 1))


def run_pipeline():
    print("🚀 Iniciando pipeline da Premier League...")

    # ETAPA 1 — Coleta
    print("\n📡 Coletando dados da API...")
    standings_raw = fetch_league_standings()
    matches_raw = fetch_matches(seasons=SEASONS)
    print(f"✅ {len(standings_raw)} times coletados (temporada corrente)")
    seasons_loaded = matches_raw['season'].nunique() if not matches_raw.empty else 0
    print(f"✅ {len(matches_raw)} partidas coletadas ({seasons_loaded}/{len(SEASONS)} temporadas acessíveis)")

    # ETAPA 2 — Transformação
    print("\n🔧 Transformando dados...")
    standings_clean = transform_standings(standings_raw)
    matches_clean = transform_matches(matches_raw)
    print("✅ Transformações concluídas")

    # ETAPA 3 — Carga no banco (idempotente via UPSERT)
    print("\n🗄️ Carregando no banco de dados...")
    upsert(standings_clean, "standings", conflict_cols=["team", "season"])
    upsert(matches_clean, "matches", conflict_cols=["match_id"])

    print("\n🏁 Pipeline finalizado com sucesso!")


if __name__ == "__main__":
    run_pipeline()

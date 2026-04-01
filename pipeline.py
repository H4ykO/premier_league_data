import os
from dotenv import load_dotenv
from ingestion.fetch_data import fetch_league_standings, fetch_matches
from transformation.transform import transform_standings, transform_matches
from database.load import load_to_db

load_dotenv()

def run_pipeline():
    print("🚀 Iniciando pipeline da Premier League...")

    # ETAPA 1 — Coleta
    print("\n📡 Coletando dados da API...")
    standings_raw = fetch_league_standings()
    matches_raw = fetch_matches()
    print(f"✅ {len(standings_raw)} times coletados")
    print(f"✅ {len(matches_raw)} partidas coletadas")

    # ETAPA 2 — Transformação
    print("\n🔧 Transformando dados...")
    standings_clean = transform_standings(standings_raw)
    matches_clean = transform_matches(matches_raw)
    print("✅ Transformações concluídas")

    # ETAPA 3 — Carga no banco
    print("\n🗄️ Carregando no banco de dados...")
    load_to_db(standings_clean, "standings")
    load_to_db(matches_clean, "matches")

    print("\n🏁 Pipeline finalizado com sucesso!")

if __name__ == "__main__":
    run_pipeline()
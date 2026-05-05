import os
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
)


def upsert(df, table_name: str, conflict_cols: list[str]) -> None:
    meta = sa.MetaData()
    meta.reflect(bind=engine, only=[table_name])
    table = meta.tables[table_name]

    records = df.to_dict(orient='records')
    with engine.begin() as conn:
        for batch_start in range(0, len(records), 500):
            batch = records[batch_start:batch_start + 500]
            stmt = pg_insert(table).values(batch)
            update_cols = {col: stmt.excluded[col] for col in df.columns if col not in conflict_cols}
            stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
            conn.execute(stmt)
    print(f'✅ {len(df)} registros upserted em {table_name}')

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

engine = create_engine(f'postgresql://{DB_USER}:@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def load_to_db(df, table_name):
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    print(f'✅ {len(df)} registros carregados em {table_name}')



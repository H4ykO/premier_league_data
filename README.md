# Premier League Data Pipeline

Pipeline de dados completo para coleta, transformação, armazenamento e análise de dados da Premier League, com dashboard interativo e modelo preditivo de resultados.

Link Streamlit Cloud app: https://premierleaguedata-fnk2qmdraacovckfse8sft.streamlit.app/

---

## Projeto

Este projeto foi desenvolvido como parte de um portfólio de Engenharia e Análise de Dados, com o objetivo de demonstrar habilidades em construção de pipelines ETL, modelagem de dados, visualização e Machine Learning aplicados a dados reais de futebol.

Os dados são coletados automaticamente da API [football-data.org](https://www.football-data.org), transformados com Python e armazenados em um banco PostgreSQL na nuvem via Supabase. Um dashboard interativo permite explorar classificação, resultados e prever o desfecho de partidas com base em um modelo simples de Machine Learning.

---

## Arquitetura

```
football-data.org API
        ↓
   Python (coleta)
        ↓
  Transformação (Pandas)
        ↓
   PostgreSQL - Supabase (armazenamento na nuvem)
        ↓
  Streamlit (dashboard + modelo preditivo)
```

---

## Funcionalidades

- **Pipeline ETL automatizado** — coleta, transforma e carrega dados da Premier League
- **Classificação atualizada** — tabela completa com pontos, saldo de gols e aproveitamento
- **Histórico de partidas** — resultados de todos os jogos da temporada
- **Modelo preditivo** — previsão de resultados com probabilidades usando Regressão Logística
- **Features inteligentes** — modelo considera posição na tabela e média de gols dos últimos 5 jogos
- **Testes automatizados** — cobertura de testes com pytest para transformações e ingestão de dados

---

## Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| Python 3.14 | Linguagem principal |
| Pandas | Transformação e manipulação de dados |
| PostgreSQL | Armazenamento dos dados |
| Supabase | Banco de dados PostgreSQL na nuvem |
| SQLAlchemy | Conexão com o banco de dados |
| Scikit-learn | Modelo preditivo (Regressão Logística) |
| Streamlit | Dashboard interativo |
| pytest | Testes automatizados |
| python-dotenv | Gerenciamento de variáveis de ambiente |

---

## Estrutura

```
premier-league-pipeline/
│
├── ingestion/
│   ├── __init__.py
│   └── fetch_data.py        # Coleta dados da API
│
├── transformation/
│   ├── __init__.py
│   └── transform.py         # Limpeza e transformação
│
├── database/
│   ├── __init__.py
│   ├── load.py              # Carrega no PostgreSQL
│   └── schema.sql           # Criação das tabelas
│
├── dashboard/
│   └── app.py               # Dashboard em Streamlit
│
├── model/
│   └── predict.py           # Modelo preditivo
│
├── tests/
│   ├── __init__.py
│   ├── test_transform.py    # Testes de transformação
│   └── test_fetch.py        # Testes de ingestão
│
├── pipeline.py              # Orquestra o pipeline completo
├── requirements.txt         # Dependências do projeto
└── README.md
```

---

## Como Rodar Localmente

### Pré-requisitos

- Python 3.10+
- PostgreSQL instalado e rodando (ou conta no [Supabase](https://supabase.com))
- Chave de API gratuita do [football-data.org](https://www.football-data.org)

### 1. Clone o repositório

```bash
git clone https://github.com/H4ykO/premier-league-pipeline.git
cd premier-league-pipeline
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```
API_KEY=sua_chave_aqui
DB_USER=seu_usuario
DB_HOST=localhost
DB_PORT=5432
DB_NAME=premier_league
DB_PASSWORD=sua_senha
```

### 4. Crie o banco de dados

```bash
psql postgres
```

```sql
CREATE DATABASE premier_league;
\c premier_league
```

Cole o conteúdo do arquivo `database/schema.sql` para criar as tabelas.

### 5. Execute o pipeline

```bash
python pipeline.py
```

### 6. Rode o dashboard

```bash
streamlit run dashboard/app.py
```

---

## Testes

O projeto conta com testes automatizados cobrindo as camadas de ingestão e transformação.

### Rodar os testes

```bash
pytest tests/ -v
```

### Cobertura dos testes

| Arquivo | O que é testado |
|---------|----------------|
| `test_transform.py` | Cálculo de goal difference, win rate, classificação de resultados e filtragem de jogos |
| `test_fetch.py` | Estrutura do DataFrame retornado, colunas corretas e mapeamento do JSON da API |

Os testes de ingestão utilizam **Mock** para simular as respostas da API sem realizar chamadas reais, garantindo testes rápidos e independentes de conectividade.

---

## Modelo Preditivo

O modelo utiliza **Regressão Logística** treinada com o histórico de partidas da temporada atual. As features utilizadas são:

| Feature | Descrição |
|---------|-----------|
| `home_position` | Posição do time da casa na tabela |
| `away_position` | Posição do time visitante na tabela |
| `home_avg_scored` | Média de gols marcados (casa) — últimos 5 jogos |
| `home_avg_conceded` | Média de gols sofridos (casa) — últimos 5 jogos |
| `away_avg_scored` | Média de gols marcados (visitante) — últimos 5 jogos |
| `away_avg_conceded` | Média de gols sofridos (visitante) — últimos 5 jogos |

**Acurácia atual:** ~61% — acima do baseline aleatório (33%) e compatível com a complexidade inerente de prever resultados de futebol.

---

## Dependências

```
requests
pandas
sqlalchemy
psycopg2-binary
streamlit
scikit-learn
python-dotenv
pytest
```

Instale tudo com:

```bash
pip install -r requirements.txt
```

---

## Autor

Desenvolvido por Joao Lucas Melo

[![LinkedIn](https://img.shields.io/badge/LinkedIn-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/joaolucas-melo/)
[![GitHub](https://img.shields.io/badge/GitHub-black?style=flat&logo=github)](https://github.com/H4ykO)

---

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

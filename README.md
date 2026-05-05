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
- **Ingestão multi-temporada** — coleta as últimas 3 temporadas acessíveis (2023/24 a 2025/26) via parâmetro `season` da API (plano gratuito da football-data.org libera apenas os 3 anos mais recentes)
- **Pipeline idempotente** — usa `UPSERT` no banco; rodar novamente não duplica registros
- **Modelo preditivo** — previsão de resultados com probabilidades usando XGBoost
- **Validação temporal** — `TimeSeriesSplit` garante que o modelo nunca "vê o futuro" durante a validação
- **Métricas completas** — reporta Accuracy, Log-loss e Brier score (média ± desvio padrão nos 5 folds)
- **Features inteligentes** — 11 features: posição na tabela (sem leakage), gols ajustados pela defesa adversária, forma recente (pts nos últimos 5 jogos), win rate por mando e confronto direto (H2H)
- **Testes automatizados** — cobertura de testes com pytest para transformações, ingestão e modelo preditivo

---

## Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| Python 3.10+ | Linguagem principal |
| Pandas | Transformação e manipulação de dados |
| PostgreSQL | Armazenamento dos dados |
| Supabase | Banco de dados PostgreSQL na nuvem |
| SQLAlchemy | Conexão com o banco de dados |
| XGBoost | Modelo preditivo (classificação) |
| Scikit-learn | TimeSeriesSplit e métricas de avaliação |
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
│   ├── test_fetch.py        # Testes de ingestão
│   └── test_predict.py      # Testes do modelo e split temporal
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

### 4. Crie (ou recrie) o banco de dados

> **Atenção:** se já tiver dados do schema antigo no Supabase, execute os comandos abaixo antes de aplicar o schema (os dados são reproduzíveis pelo pipeline):
> ```sql
> DROP TABLE IF EXISTS matches;
> DROP TABLE IF EXISTS standings;
> ```

Em seguida, aplique o schema atualizado:

```bash
psql postgres
```

```sql
CREATE DATABASE premier_league;
\c premier_league
```

Cole o conteúdo do arquivo `database/schema.sql` para criar as tabelas com suporte a múltiplas temporadas.

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

### CI — Integração Contínua

O projeto utiliza **GitHub Actions** para rodar os testes automaticamente a cada push na branch `main`, garantindo que nenhuma alteração quebre o pipeline.

![Tests](https://github.com/H4ykO/premier-league-pipeline/actions/workflows/tests.yml/badge.svg)

### Rodar os testes

```bash
pytest tests/ -v
```

### Cobertura dos testes

| Arquivo | O que é testado |
|---------|----------------|
| `test_transform.py` | Cálculo de goal difference, win rate, classificação de resultados, filtragem de jogos e preservação da coluna `season` |
| `test_fetch.py` | Estrutura do DataFrame, colunas corretas (incluindo `season`), chamada multi-temporada e mapeamento do JSON da API |
| `test_predict.py` | `_build_positions_history`, `_get_position_at_date`, `calc_goals_avg`, `calc_form`, `calc_venue_win_rate`, `calc_h2h`, `brier_score_multiclass` e garantia de que o `TimeSeriesSplit` preserva ordem temporal (19 testes no total) |

Os testes de ingestão utilizam **Mock** para simular as respostas da API sem realizar chamadas reais, garantindo testes rápidos e independentes de conectividade.

---

## Modelo Preditivo

O modelo utiliza **XGBoost** treinado com o histórico de partidas das últimas 3 temporadas da Premier League (2023/24 a 2025/26). A posição na tabela é calculada diretamente a partir do histórico de matches, com snapshot tirado **antes** de cada rodada — eliminando leakage temporal. Os hiperparâmetros são selecionados via `GridSearchCV` com `TimeSeriesSplit(n_splits=3)`. A validação final usa `TimeSeriesSplit` com 5 folds, garantindo que cada fold treina apenas no passado e valida no futuro. O modelo final é calibrado com `CalibratedClassifierCV(method='isotonic')` para melhorar a qualidade das probabilidades.

**Métricas (5 folds temporais):** Accuracy ~0.509 ± 0.043 | Log-loss ~1.027 | Brier ~0.612

As features utilizadas são:

| Feature | Descrição |
|---------|-----------|
| `home_position` | Posição da casa calculada do histórico de matches (sem leakage) |
| `away_position` | Posição do visitante calculada do histórico de matches (sem leakage) |
| `home_scored_adj` | Gols marcados pela casa ajustados pela defesa do visitante |
| `home_avg_conceded` | Média de gols sofridos pela casa — últimos 5 jogos |
| `away_scored_adj` | Gols marcados pelo visitante ajustados pela defesa da casa |
| `away_avg_conceded` | Média de gols sofridos pelo visitante — últimos 5 jogos |
| `home_form_pts` | Pontos acumulados pela casa nos últimos 5 jogos (0–15) |
| `away_form_pts` | Pontos acumulados pelo visitante nos últimos 5 jogos (0–15) |
| `home_venue_wr` | Win rate do time da casa jogando em casa (últimos 10 jogos em casa) |
| `away_venue_wr` | Win rate do visitante jogando fora (últimos 10 jogos fora) |
| `h2h_home_pts` | Pontos do time da casa nos últimos 3 confrontos diretos (0–9) |

**Métricas reportadas** (validação com 5 folds temporais):
- **Accuracy** — percentual de previsões corretas
- **Log-loss** — penaliza previsões confiantes e erradas (quanto menor, melhor)
- **Brier score** — erro quadrático médio entre probabilidades previstas e resultado real (quanto menor, melhor)

---

## Dependências

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

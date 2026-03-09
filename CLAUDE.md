# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Streamlit-based knowledge graph explorer with real movie data from TMDB. Demonstrates three retrieval approaches — Knowledge Graph (Neo4j), Vector Search (ChromaDB), and Hybrid — with an evaluation framework comparing their accuracy.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (serves at http://localhost:8501)
streamlit run Home.py
```

There are no tests, linting, or build steps configured.

## Architecture

Multi-page Streamlit app. Original pages (Home, Neo4j, NetworkX, Advanced Cypher, AI Assistant) are self-contained with their own connection management. New pages use a shared `utils/` layer.

### Shared Utilities (`utils/`)

- **config.py** — Loads `.env` via python-dotenv. All API keys and connection strings as module constants.
- **tmdb_client.py** — TMDB API client: `get_popular_movies()`, `get_movie_details()`, `build_graph_data()`. Builds structured dataset with movies, people, genres, companies, keywords.
- **neo4j_utils.py** — `neo4j_sidebar_connect()` renders connection UI with Aura Cloud / Local toggle. `execute_query()`, `get_graph_schema()`, `format_schema()`, `query_to_networkx()`, `load_tmdb_to_neo4j()` (MERGE-based, idempotent).
- **openai_utils.py** — Cached OpenAI client, `get_embedding()`, `get_embeddings_batch()`, `chat_completion()`.

### Pages

- **Home.py** — Sample NetworkX + Pyvis visualization
- **pages/Neo4j.py** — Basic Neo4j queries (self-contained connection)
- **pages/NetworkX.py** — Business network analysis with Plotly
- **pages/3_Advanced_Cypher.py** — Pre-built Cypher query library
- **pages/4_AI_Assistant.py** — Single-turn text-to-Cypher
- **pages/5_TMDB_Data.py** — Data pipeline: fetch TMDB -> preview -> load Neo4j -> index ChromaDB -> export JSON
- **pages/6_Conversational_Cypher.py** — Multi-turn conversational Cypher with context accumulation. LLM returns JSON `{cypher, explanation, follow_ups}`. Pre-built analytical workflows.
- **pages/7_Vector_Search.py** — ChromaDB semantic search with keyword-vs-semantic comparison. Tabs: search, similar movies, collection explorer.
- **pages/8_Evaluation.py** — KG vs Vector vs Hybrid benchmark. Generates eval questions from actual Neo4j data with ground truth. Measures recall across Factual/Semantic/Complex categories.

### Data Model (Neo4j)

Nodes: `Movie`, `Person`, `Genre`, `ProductionCompany`, `Keyword` (all keyed by `tmdb_id`).
Relationships: `ACTED_IN` (character, credit_order), `DIRECTED`, `IN_GENRE`, `PRODUCED_BY`, `HAS_KEYWORD`.

### Vector Store (ChromaDB)

Collection `movie_overviews`: documents are `"{title}. {tagline} {overview}"`, embedded with `text-embedding-3-small`. Metadata includes title, tmdb_id, vote_average, release_date, genres. Persisted in `./chroma_db/`.

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` — Required for AI pages, embeddings, evaluation
- `TMDB_API_KEY`, `OMDB_API_KEY` — Required for TMDB data pipeline
- `AURA_NEO4J_URI`, `AURORA_NEO4J_USER`, `AURORA_NEO4J_PASSWORD` — Neo4j Aura cloud (instance: knowledge-graph-kaljuvee)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Local Neo4j fallback

## Key Patterns

- New pages use `utils/neo4j_utils.neo4j_sidebar_connect()` for connection; original pages manage their own
- ChromaDB uses `PersistentClient` with `@st.cache_resource` to avoid file lock conflicts on Streamlit reload
- TMDB data loading uses `MERGE` with uniqueness constraints for idempotency
- Conversational Cypher accumulates context in `st.session_state.conv_context` — each turn appends question, query, and result summary
- Hybrid retrieval: vector search finds candidates -> LLM generates Cypher using those as starting points -> graph traversal for structural context
- Evaluation generates questions dynamically from actual KG data to ensure ground truth accuracy

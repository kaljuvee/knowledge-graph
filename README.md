# Knowledge Graph Explorer

A Streamlit application for exploring knowledge graphs with real movie data from TMDB. Compares three retrieval approaches — **Knowledge Graph** (Neo4j), **Vector Search** (ChromaDB), and **Hybrid** — with an evaluation framework demonstrating that a hybrid approach achieves the best accuracy.

## Features

### Data Pipeline
- **TMDB Integration**: Fetch real movie data (cast, crew, genres, keywords) from the TMDB and OMDB APIs
- **Neo4j Loading**: Automated graph construction with Movies, People, Genres, Production Companies, and Keywords
- **Vector Indexing**: Embed movie overviews into ChromaDB using OpenAI `text-embedding-3-small`

### Knowledge Graph
- **Neo4j Queries**: Pre-built Cypher query library across 7 categories (pattern matching, path finding, aggregations, recommendations, etc.)
- **Multi-Turn Conversational Cypher**: Chat-style interface where each question builds on previous context — ask follow-ups like "who directed those movies?" or "now filter by rating above 8"
- **Text-to-Cypher AI Assistant**: Convert natural language to Cypher queries using OpenAI

### Vector Search
- **Semantic Movie Search**: Find movies by meaning, not keywords — "a dystopian future where machines control humans" finds The Matrix
- **Keyword vs Semantic Comparison**: Side-by-side demonstration of why vector search outperforms keyword matching for thematic queries
- **Similar Movies**: Find thematically similar movies via embedding distance

### Evaluation
- **KG vs Vector vs Hybrid Benchmark**: Automated evaluation generating questions from actual graph data with ground truth answers
- **Three question categories**: Factual (KG excels), Semantic (Vector excels), Complex (Hybrid excels)
- **Recall scoring** with per-category breakdown and comparative visualizations

### Visualization
- **Interactive graph rendering** with Pyvis
- **Plotly charts** for analytics and evaluation results
- **NetworkX** graph algorithms (centrality, community detection)

## Quick Start

```bash
git clone https://github.com/kaljuvee/knowledge-graph.git
cd knowledge-graph
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your API keys
streamlit run Home.py
```

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Required For | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | AI Assistant, Vector Search, Evaluation | OpenAI API key ([get one here](https://platform.openai.com/api-keys)) |
| `TMDB_API_KEY` | Data Pipeline | TMDB API key ([get one here](https://www.themoviedb.org/settings/api)) |
| `OMDB_API_KEY` | Data Pipeline (optional) | OMDB API key for supplementary ratings |
| `AURA_NEO4J_URI` | Neo4j pages | Neo4j Aura connection URI (e.g., `neo4j+s://xxxxx.databases.neo4j.io`) |
| `AURORA_NEO4J_USER` | Neo4j pages | Neo4j Aura username |
| `AURORA_NEO4J_PASSWORD` | Neo4j pages | Neo4j Aura password |

For local Neo4j, set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` instead.

## Neo4j Setup

### Option 1: Neo4j Aura (Recommended)
1. Sign up at [Neo4j Aura](https://neo4j.com/cloud/aura/) (free tier available)
2. Create a database instance
3. Add the connection URI, username, and password to `.env`

### Option 2: Local Neo4j
```bash
# Ubuntu/Linux
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 4.1' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt-get update && sudo apt-get install neo4j
sudo systemctl start neo4j
```

## Workflow

1. **Fetch Data** (page 5): Pull movies from TMDB API
2. **Load to Neo4j** (page 5): Build the knowledge graph
3. **Index to ChromaDB** (page 5): Embed movie overviews for vector search
4. **Explore**: Use Conversational Cypher (page 6), Vector Search (page 7), or the original query pages
5. **Evaluate** (page 8): Run the benchmark comparing KG vs Vector vs Hybrid retrieval

## Project Structure

```
knowledge-graph/
├── Home.py                              # Entry point — sample NetworkX visualization
├── pages/
│   ├── Neo4j.py                         # Basic Neo4j queries
│   ├── NetworkX.py                      # Business network analysis
│   ├── 3_Advanced_Cypher.py             # Pre-built Cypher query library
│   ├── 4_AI_Assistant.py                # Single-turn text-to-Cypher
│   ├── 5_TMDB_Data.py                   # TMDB data pipeline
│   ├── 6_Conversational_Cypher.py       # Multi-turn conversational Cypher
│   ├── 7_Vector_Search.py              # ChromaDB semantic search
│   └── 8_Evaluation.py                 # KG vs Vector vs Hybrid benchmark
├── utils/
│   ├── config.py                        # Environment config (dotenv)
│   ├── tmdb_client.py                   # TMDB API client
│   ├── neo4j_utils.py                   # Neo4j connection, queries, data loading
│   └── openai_utils.py                  # OpenAI embeddings and chat
├── docs/
│   ├── architecture_readme.md           # Architecture with Mermaid diagrams
│   └── knowledge-graph-summary.md       # Feature summary
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Data Model

The Neo4j knowledge graph uses TMDB data with the following schema:

**Nodes**: `Movie`, `Person`, `Genre`, `ProductionCompany`, `Keyword`

**Relationships**: `ACTED_IN` (character, credit_order), `DIRECTED`, `IN_GENRE`, `PRODUCED_BY`, `HAS_KEYWORD`

See [docs/architecture_readme.md](docs/architecture_readme.md) for full ER diagrams, data pipeline flowcharts, and a detailed comparison of retrieval strategies.

## Dependencies

- **Web**: Streamlit
- **Graph DB**: Neo4j
- **Vector DB**: ChromaDB
- **AI**: OpenAI (embeddings + LLM)
- **Data**: TMDB/OMDB APIs, Pandas
- **Visualization**: Pyvis, Plotly, Matplotlib, NetworkX

## License

Apache License 2.0

## Acknowledgments

- [Streamlit](https://streamlit.io/) — Web framework
- [Neo4j](https://neo4j.com/) — Graph database
- [ChromaDB](https://www.trychroma.com/) — Vector database
- [OpenAI](https://openai.com/) — Embeddings and LLM
- [TMDB](https://www.themoviedb.org/) — Movie data
- [Pyvis](https://pyvis.readthedocs.io/) / [NetworkX](https://networkx.org/) — Graph visualization

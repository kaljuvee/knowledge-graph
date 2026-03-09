import os
from dotenv import load_dotenv

load_dotenv()

# TMDB
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4.1-mini"

# Neo4j - Aura Cloud (default)
AURA_NEO4J_URI = os.getenv("AURA_NEO4J_URI", "")
AURA_NEO4J_USER = os.getenv("AURORA_NEO4J_USER", "")
AURA_NEO4J_PASSWORD = os.getenv("AURORA_NEO4J_PASSWORD", "")

# Neo4j - Local fallback
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# ChromaDB
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

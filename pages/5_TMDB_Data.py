import streamlit as st
import pandas as pd
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import TMDB_API_KEY, OPENAI_API_KEY, CHROMA_PERSIST_DIR
from utils.tmdb_client import get_popular_movies, build_graph_data
from utils.neo4j_utils import neo4j_sidebar_connect, load_tmdb_to_neo4j

st.set_page_config(page_title="TMDB Data Pipeline", layout="wide")
st.title("TMDB Movie Data Pipeline")
st.markdown("""
Fetch real movie data from **TMDB** (The Movie Database), load it into **Neo4j** as a knowledge graph,
and index movie descriptions into **ChromaDB** for vector search.
""")

# Sidebar
driver = neo4j_sidebar_connect(key_prefix="tmdb")

if not TMDB_API_KEY:
    st.error("TMDB_API_KEY not set in .env")
    st.stop()

# --- Step 1: Fetch from TMDB ---
st.header("1. Fetch Movies from TMDB")
num_pages = st.slider("Number of pages to fetch (20 movies/page)", 1, 10, 5)

if "tmdb_data" not in st.session_state:
    st.session_state.tmdb_data = None

if st.button("Fetch from TMDB", type="primary"):
    progress = st.progress(0)
    status = st.empty()

    status.text("Fetching popular movie list...")
    popular = get_popular_movies(pages=num_pages)
    progress.progress(0.1)

    def progress_cb(i, total, title):
        pct = 0.1 + 0.9 * (i / total)
        progress.progress(pct)
        status.text(f"[{i+1}/{total}] Fetching: {title}")

    data = build_graph_data(popular, progress_callback=progress_cb)
    st.session_state.tmdb_data = data
    progress.progress(1.0)
    status.text("Done!")
    st.success(
        f"Fetched {len(data['movies'])} movies, "
        f"{len(data['people'])} people, "
        f"{len(data['genres'])} genres, "
        f"{len(data['keywords'])} keywords"
    )

# --- Preview ---
if st.session_state.tmdb_data:
    data = st.session_state.tmdb_data
    st.header("2. Preview Data")

    tab_movies, tab_people, tab_genres, tab_keywords = st.tabs(
        ["Movies", "People", "Genres", "Keywords"]
    )

    with tab_movies:
        df = pd.DataFrame(data["movies"])
        display_cols = [
            "title",
            "release_date",
            "vote_average",
            "revenue",
            "runtime",
            "overview",
        ]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True)

    with tab_people:
        st.dataframe(pd.DataFrame(data["people"]), use_container_width=True)

    with tab_genres:
        st.dataframe(pd.DataFrame(data["genres"]), use_container_width=True)

    with tab_keywords:
        st.dataframe(pd.DataFrame(data["keywords"]), use_container_width=True)

    # --- Step 3: Load to Neo4j ---
    st.header("3. Load into Neo4j")
    if not driver:
        st.info("Connect to Neo4j in the sidebar to load data.")
    else:
        clear_first = st.checkbox("Clear existing data before loading", value=False)
        if st.button("Load into Neo4j", type="primary"):
            progress = st.progress(0)
            status = st.empty()

            if clear_first:
                from utils.neo4j_utils import execute_write
                status.text("Clearing existing data...")
                execute_write(driver, "MATCH (n) DETACH DELETE n")

            def neo4j_progress(step, total, msg):
                progress.progress(step / total)
                status.text(msg)

            load_tmdb_to_neo4j(driver, data, progress_callback=neo4j_progress)
            progress.progress(1.0)
            status.text("Done!")
            st.success("Data loaded into Neo4j!")

            # Show counts
            from utils.neo4j_utils import execute_query

            counts = execute_query(
                driver,
                """
                MATCH (n)
                WITH labels(n)[0] AS label, count(n) AS cnt
                RETURN label, cnt ORDER BY cnt DESC
                """,
            )
            st.dataframe(pd.DataFrame(counts), use_container_width=True)

    # --- Step 4: Index to ChromaDB ---
    st.header("4. Index into ChromaDB (Vector Store)")
    if not OPENAI_API_KEY:
        st.warning("Set OPENAI_API_KEY in .env for embeddings.")
    else:
        if st.button("Index Movie Overviews into ChromaDB", type="primary"):
            import chromadb
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

            progress = st.progress(0)
            status = st.empty()

            status.text("Initializing ChromaDB...")
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            ef = OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY, model_name="text-embedding-3-small"
            )
            # Delete existing collection if it exists
            try:
                client.delete_collection("movie_overviews")
            except Exception:
                pass
            collection = client.get_or_create_collection(
                "movie_overviews", embedding_function=ef
            )
            progress.progress(0.2)

            # Prepare documents
            documents = []
            metadatas = []
            ids = []
            for movie in data["movies"]:
                if movie.get("overview"):
                    # Build rich document text
                    genre_names = []
                    for gid in movie.get("genres", []):
                        for g in data["genres"]:
                            if g["tmdb_id"] == gid:
                                genre_names.append(g["name"])
                    doc = f"{movie['title']}. {movie.get('tagline', '')} {movie['overview']}"
                    documents.append(doc)
                    metadatas.append(
                        {
                            "title": movie["title"],
                            "tmdb_id": str(movie["tmdb_id"]),
                            "vote_average": float(movie.get("vote_average", 0)),
                            "release_date": movie.get("release_date", ""),
                            "genres": ", ".join(genre_names),
                        }
                    )
                    ids.append(f"movie_{movie['tmdb_id']}")

            status.text(f"Embedding {len(documents)} movie overviews...")
            progress.progress(0.4)

            # Add in batches
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                end = min(i + batch_size, len(documents))
                collection.add(
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                    ids=ids[i:end],
                )
                progress.progress(0.4 + 0.6 * (end / len(documents)))

            status.text("Done!")
            st.success(f"Indexed {len(documents)} movies into ChromaDB!")

    # --- Save/Load JSON ---
    st.header("5. Export/Import JSON")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save to data/tmdb_movies.json"):
            os.makedirs("data", exist_ok=True)
            with open("data/tmdb_movies.json", "w") as f:
                json.dump(data, f, indent=2)
            st.success("Saved!")
    with col2:
        if os.path.exists("data/tmdb_movies.json"):
            if st.button("Load from data/tmdb_movies.json"):
                with open("data/tmdb_movies.json") as f:
                    st.session_state.tmdb_data = json.load(f)
                st.rerun()

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import OPENAI_API_KEY, CHROMA_PERSIST_DIR

st.set_page_config(page_title="Vector Search", layout="wide")
st.title("Vector Similarity Search")
st.markdown("""
Search movies by **semantic meaning** using ChromaDB vector embeddings.
Unlike keyword search, vector search understands concepts — searching for
*"a hero fighting against machines"* will find *The Matrix* even if those exact words
don't appear in the description.
""")

if not OPENAI_API_KEY:
    st.error("Set OPENAI_API_KEY in .env for embeddings.")
    st.stop()


@st.cache_resource
def get_chroma_collection():
    """Load or create ChromaDB collection."""
    import chromadb
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    ef = OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY, model_name="text-embedding-3-small"
    )
    return client.get_or_create_collection("movie_overviews", embedding_function=ef)


# Check if collection has data
try:
    collection = get_chroma_collection()
    doc_count = collection.count()
except Exception as e:
    st.error(f"ChromaDB error: {e}")
    st.stop()

if doc_count == 0:
    st.warning(
        "No movies indexed yet. Go to **5 TMDB Data** page to fetch and index movie data."
    )
    st.stop()

st.sidebar.metric("Indexed Movies", doc_count)

# --- Tab layout ---
tab_search, tab_similar, tab_explore = st.tabs(
    ["Semantic Search", "Similar Movies", "Collection Explorer"]
)

# --- Tab 1: Semantic Search ---
with tab_search:
    st.subheader("Search by Meaning")
    query = st.text_input(
        "Describe what kind of movie you're looking for:",
        placeholder="e.g., a dystopian future where machines control humans",
    )
    n_results = st.slider("Number of results", 1, 20, 10, key="search_n")

    # Optional filters
    with st.expander("Filters"):
        min_rating = st.slider("Minimum rating", 0.0, 10.0, 0.0, 0.5, key="search_rating")

    if query:
        with st.spinner("Searching..."):
            results = collection.query(query_texts=[query], n_results=n_results)

        if results and results["ids"][0]:
            rows = []
            for i, (doc, meta, dist) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                similarity = max(0, 1 - dist)  # Convert distance to similarity
                if float(meta.get("vote_average", 0)) >= min_rating:
                    rows.append(
                        {
                            "Rank": i + 1,
                            "Title": meta.get("title", "Unknown"),
                            "Similarity": f"{similarity:.3f}",
                            "Rating": meta.get("vote_average", "N/A"),
                            "Genres": meta.get("genres", ""),
                            "Release": meta.get("release_date", ""),
                            "Overview": doc[:200] + "..." if len(doc) > 200 else doc,
                        }
                    )

            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No results match the filters.")
        else:
            st.info("No results found.")

    # Keyword comparison
    st.subheader("Keyword vs Semantic Comparison")
    st.markdown("""
    Try searching for the same concept using keywords vs semantic search.
    For example, *"artificial intelligence rebellion"* finds different results than
    just looking for movies with "AI" in the title.
    """)
    keyword = st.text_input("Keyword search:", placeholder="e.g., robot")
    if keyword:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Keyword Match** (title/overview contains word)")
            all_docs = collection.get(include=["documents", "metadatas"])
            keyword_matches = []
            for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
                if keyword.lower() in doc.lower():
                    keyword_matches.append(
                        {
                            "Title": meta.get("title", ""),
                            "Rating": meta.get("vote_average", ""),
                        }
                    )
            if keyword_matches:
                st.dataframe(pd.DataFrame(keyword_matches[:10]), hide_index=True)
            else:
                st.info("No keyword matches found.")

        with col2:
            st.markdown("**Semantic Match** (meaning-based)")
            sem_results = collection.query(query_texts=[keyword], n_results=10)
            if sem_results["ids"][0]:
                sem_rows = [
                    {
                        "Title": meta.get("title", ""),
                        "Rating": meta.get("vote_average", ""),
                        "Similarity": f"{max(0, 1 - dist):.3f}",
                    }
                    for meta, dist in zip(
                        sem_results["metadatas"][0], sem_results["distances"][0]
                    )
                ]
                st.dataframe(pd.DataFrame(sem_rows), hide_index=True)


# --- Tab 2: Similar Movies ---
with tab_similar:
    st.subheader("Find Similar Movies")
    all_data = collection.get(include=["metadatas"])
    movie_titles = sorted([m.get("title", "") for m in all_data["metadatas"]])

    selected_movie = st.selectbox("Select a movie:", movie_titles, key="similar_select")
    n_similar = st.slider("Number of similar movies", 1, 15, 5, key="similar_n")

    if selected_movie:
        # Find the selected movie's document
        selected_idx = None
        for i, meta in enumerate(all_data["metadatas"]):
            if meta.get("title") == selected_movie:
                selected_idx = all_data["ids"][i]
                break

        if selected_idx:
            # Get the document and use it to query
            movie_doc = collection.get(ids=[selected_idx], include=["documents"])
            if movie_doc["documents"]:
                results = collection.query(
                    query_texts=[movie_doc["documents"][0]],
                    n_results=n_similar + 1,  # +1 because it includes itself
                )

                rows = []
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    if meta.get("title") != selected_movie:
                        rows.append(
                            {
                                "Title": meta.get("title", ""),
                                "Similarity": f"{max(0, 1 - dist):.3f}",
                                "Rating": meta.get("vote_average", ""),
                                "Genres": meta.get("genres", ""),
                                "Overview": doc[:200] + "..." if len(doc) > 200 else doc,
                            }
                        )

                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# --- Tab 3: Collection Explorer ---
with tab_explore:
    st.subheader("Collection Statistics")

    all_data = collection.get(include=["metadatas"])
    metas = all_data["metadatas"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Movies", len(metas))
    with col2:
        ratings = [float(m.get("vote_average", 0)) for m in metas if m.get("vote_average")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        st.metric("Avg Rating", f"{avg_rating:.1f}")
    with col3:
        genres_all = []
        for m in metas:
            genres_all.extend([g.strip() for g in m.get("genres", "").split(",") if g.strip()])
        st.metric("Unique Genres", len(set(genres_all)))

    # Genre distribution
    if genres_all:
        import plotly.express as px

        genre_counts = pd.Series(genres_all).value_counts().reset_index()
        genre_counts.columns = ["Genre", "Count"]
        fig = px.bar(genre_counts, x="Genre", y="Count", title="Genre Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # Rating distribution
    if ratings:
        import plotly.express as px

        fig = px.histogram(
            x=ratings, nbins=20, title="Rating Distribution", labels={"x": "Rating", "y": "Count"}
        )
        st.plotly_chart(fig, use_container_width=True)

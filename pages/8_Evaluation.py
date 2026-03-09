import streamlit as st
import pandas as pd
import json
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import OPENAI_API_KEY, CHROMA_PERSIST_DIR
from utils.neo4j_utils import (
    neo4j_sidebar_connect,
    execute_query,
    get_graph_schema,
    format_schema,
)
from utils.openai_utils import chat_completion

st.set_page_config(page_title="Retrieval Evaluation", layout="wide")
st.title("KG vs Vector vs Hybrid Evaluation")
st.markdown("""
Compare three retrieval approaches on the same movie dataset:
- **Knowledge Graph (KG)**: Text-to-Cypher queries against Neo4j
- **Vector Search**: Semantic similarity via ChromaDB embeddings
- **Hybrid**: Vector search to find relevant context, then structured KG traversal

This demonstrates that **structured questions** favor KG, **semantic questions** favor vectors,
and a **hybrid approach** often achieves the best overall accuracy.
""")

# Sidebar
driver = neo4j_sidebar_connect(key_prefix="eval")

if not driver:
    st.info("Connect to Neo4j to run evaluations.")
    st.stop()

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY required.")
    st.stop()


@st.cache_resource
def get_chroma_collection():
    import chromadb
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    ef = OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY, model_name="text-embedding-3-small"
    )
    return client.get_or_create_collection("movie_overviews", embedding_function=ef)


try:
    collection = get_chroma_collection()
    if collection.count() == 0:
        st.warning("ChromaDB empty. Index data via **5 TMDB Data** page first.")
        st.stop()
except Exception as e:
    st.error(f"ChromaDB error: {e}")
    st.stop()


# --- Generate ground truth from KG ---
@st.cache_data(ttl=600)
def generate_eval_questions(_driver):
    """Generate evaluation questions with ground truth from the actual KG data."""
    questions = []

    # Category 1: Factual/Structural (KG should excel)
    # Q: Who directed movie X?
    directors = execute_query(
        _driver,
        """
        MATCH (p:Person)-[:DIRECTED]->(m:Movie)
        RETURN m.title AS movie, p.name AS director
        LIMIT 5
        """,
    )
    for d in directors[:3]:
        questions.append(
            {
                "question": f"Who directed {d['movie']}?",
                "ground_truth": [d["director"]],
                "category": "Factual",
                "expected_winner": "KG",
            }
        )

    # Q: What genre is movie X?
    genres = execute_query(
        _driver,
        """
        MATCH (m:Movie)-[:IN_GENRE]->(g:Genre)
        WITH m.title AS movie, COLLECT(g.name) AS genres
        RETURN movie, genres
        LIMIT 3
        """,
    )
    for g in genres[:2]:
        questions.append(
            {
                "question": f"What genres does {g['movie']} belong to?",
                "ground_truth": g["genres"],
                "category": "Factual",
                "expected_winner": "KG",
            }
        )

    # Q: How many movies did actor X appear in?
    actors = execute_query(
        _driver,
        """
        MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
        WITH p.name AS actor, COUNT(m) AS count, COLLECT(m.title) AS movies
        WHERE count >= 2
        RETURN actor, count, movies
        ORDER BY count DESC LIMIT 3
        """,
    )
    for a in actors[:2]:
        questions.append(
            {
                "question": f"What movies has {a['actor']} appeared in?",
                "ground_truth": a["movies"],
                "category": "Factual",
                "expected_winner": "KG",
            }
        )

    # Category 2: Semantic (Vector should help)
    # Use keyword-rich queries about themes
    keyword_groups = execute_query(
        _driver,
        """
        MATCH (m:Movie)-[:HAS_KEYWORD]->(k:Keyword)
        WITH k.name AS keyword, COLLECT(m.title) AS movies, COUNT(m) AS cnt
        WHERE cnt >= 2
        RETURN keyword, movies
        ORDER BY cnt DESC LIMIT 3
        """,
    )
    for kg in keyword_groups[:2]:
        questions.append(
            {
                "question": f"Find movies related to '{kg['keyword']}'",
                "ground_truth": kg["movies"],
                "category": "Semantic",
                "expected_winner": "Vector",
            }
        )

    # Genre-based semantic queries
    genre_movies = execute_query(
        _driver,
        """
        MATCH (m:Movie)-[:IN_GENRE]->(g:Genre)
        WHERE g.name IN ['Science Fiction', 'Thriller', 'Animation']
        WITH g.name AS genre, COLLECT(m.title) AS movies
        RETURN genre, movies
        LIMIT 2
        """,
    )
    for gm in genre_movies[:1]:
        questions.append(
            {
                "question": f"Find movies with a {gm['genre'].lower()} feel or theme",
                "ground_truth": gm["movies"],
                "category": "Semantic",
                "expected_winner": "Vector",
            }
        )

    # Category 3: Complex/Hybrid
    complex_q = execute_query(
        _driver,
        """
        MATCH (p:Person)-[:DIRECTED]->(m:Movie)-[:IN_GENRE]->(g:Genre)
        WHERE m.vote_average > 7.0
        WITH p.name AS director, COLLECT(DISTINCT m.title) AS movies,
             COLLECT(DISTINCT g.name) AS genres
        WHERE size(movies) >= 2
        RETURN director, movies, genres
        LIMIT 2
        """,
    )
    for c in complex_q[:2]:
        questions.append(
            {
                "question": f"What are the highly rated movies directed by {c['director']} and their genres?",
                "ground_truth": c["movies"] + c["genres"],
                "category": "Complex",
                "expected_winner": "Hybrid",
            }
        )

    # Cross-domain: actor + genre
    cross = execute_query(
        _driver,
        """
        MATCH (p:Person)-[:ACTED_IN]->(m:Movie)-[:IN_GENRE]->(g:Genre)
        WHERE g.name = 'Action'
        WITH p.name AS actor, COLLECT(DISTINCT m.title) AS movies
        WHERE size(movies) >= 2
        RETURN actor, movies
        LIMIT 1
        """,
    )
    for c in cross:
        questions.append(
            {
                "question": f"Find action movies featuring {c['actor']}",
                "ground_truth": c["movies"],
                "category": "Complex",
                "expected_winner": "Hybrid",
            }
        )

    return questions


# --- Retrieval functions ---
def kg_retrieve(question, driver, schema_str):
    """KG-only: text-to-Cypher then execute."""
    t0 = time.time()
    prompt = f"""Convert this question to a Cypher query.

{schema_str}

RULES:
- Return ONLY the Cypher query, no explanations
- LIMIT 20
- Use property names from the schema
- Movie nodes: tmdb_id, title, overview, vote_average, revenue, runtime, release_date
- Person nodes: tmdb_id, name, known_for_department
- Relationships: ACTED_IN (character), DIRECTED, IN_GENRE, PRODUCED_BY, HAS_KEYWORD"""

    cypher = chat_completion(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
    )
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()

    try:
        results = execute_query(driver, cypher)
        # Extract all string values as answer items
        answers = set()
        for row in results:
            for v in row.values():
                if isinstance(v, str):
                    answers.add(v)
                elif isinstance(v, list):
                    answers.update(str(x) for x in v)
        latency = time.time() - t0
        return list(answers), cypher, latency
    except Exception as e:
        return [], f"ERROR: {cypher}\n{e}", time.time() - t0


def vector_retrieve(question, collection, n=10):
    """Vector-only: semantic search on ChromaDB."""
    t0 = time.time()
    results = collection.query(query_texts=[question], n_results=n)
    answers = []
    if results["metadatas"][0]:
        for meta in results["metadatas"][0]:
            answers.append(meta.get("title", ""))
            if meta.get("genres"):
                answers.extend([g.strip() for g in meta["genres"].split(",")])
    latency = time.time() - t0
    return answers, "vector_search", latency


def hybrid_retrieve(question, driver, collection, schema_str, n=5):
    """Hybrid: vector search for context, then KG traversal."""
    t0 = time.time()

    # Step 1: Vector search for relevant movies
    vec_results = collection.query(query_texts=[question], n_results=n)
    movie_titles = [m.get("title", "") for m in vec_results["metadatas"][0]]

    # Step 2: Use those as context for Cypher generation
    context = f"Relevant movies from semantic search: {movie_titles}"
    prompt = f"""Convert this question to a Cypher query. You have additional context from a semantic search.

{schema_str}

CONTEXT: {context}

RULES:
- Return ONLY the Cypher query
- LIMIT 20
- You may use the movie titles from context as starting points for graph traversal
- If the question is about relationships, use the context movies as entry points
- Movie nodes: tmdb_id, title, overview, vote_average, revenue, runtime, release_date
- Person nodes: tmdb_id, name, known_for_department
- Relationships: ACTED_IN (character), DIRECTED, IN_GENRE, PRODUCED_BY, HAS_KEYWORD"""

    cypher = chat_completion(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
    )
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()

    try:
        results = execute_query(driver, cypher)
        answers = set(movie_titles)  # Include vector matches
        for row in results:
            for v in row.values():
                if isinstance(v, str):
                    answers.add(v)
                elif isinstance(v, list):
                    answers.update(str(x) for x in v)
        latency = time.time() - t0
        return list(answers), cypher, latency
    except Exception as e:
        latency = time.time() - t0
        return list(movie_titles), f"Vector fallback. Cypher ERROR: {cypher}\n{e}", latency


def compute_score(retrieved, ground_truth):
    """Compute recall: fraction of ground truth items found in retrieved."""
    if not ground_truth:
        return 0.0
    retrieved_lower = set(str(x).lower() for x in retrieved)
    found = sum(
        1
        for gt in ground_truth
        if any(str(gt).lower() in r for r in retrieved_lower)
    )
    return found / len(ground_truth)


# --- Main UI ---
schema_str = format_schema(get_graph_schema(driver))

tab_single, tab_bench, tab_analysis = st.tabs(
    ["Single Query", "Benchmark", "Analysis"]
)

# --- Single query comparison ---
with tab_single:
    st.subheader("Compare Approaches on a Single Question")
    question = st.text_input(
        "Question:",
        placeholder="e.g., What movies has Tom Hanks appeared in?",
        key="eval_single_q",
    )

    if question and st.button("Compare", type="primary", key="eval_single_btn"):
        col_kg, col_vec, col_hyb = st.columns(3)

        with col_kg:
            st.markdown("**Knowledge Graph**")
            answers, detail, latency = kg_retrieve(question, driver, schema_str)
            st.caption(f"Latency: {latency:.2f}s")
            st.code(detail, language="cypher")
            if answers:
                st.dataframe(
                    pd.DataFrame({"Results": list(answers)[:20]}), hide_index=True
                )
            else:
                st.info("No results")

        with col_vec:
            st.markdown("**Vector Search**")
            answers, detail, latency = vector_retrieve(question, collection)
            st.caption(f"Latency: {latency:.2f}s")
            if answers:
                st.dataframe(
                    pd.DataFrame({"Results": list(set(answers))[:20]}), hide_index=True
                )
            else:
                st.info("No results")

        with col_hyb:
            st.markdown("**Hybrid**")
            answers, detail, latency = hybrid_retrieve(
                question, driver, collection, schema_str
            )
            st.caption(f"Latency: {latency:.2f}s")
            st.code(detail, language="cypher")
            if answers:
                st.dataframe(
                    pd.DataFrame({"Results": list(set(answers))[:20]}), hide_index=True
                )
            else:
                st.info("No results")


# --- Benchmark ---
with tab_bench:
    st.subheader("Automated Benchmark")
    st.markdown("""
    Runs all three approaches against questions **generated from actual data** in your Neo4j
    database. Each question has known ground truth answers, so we can measure recall.
    """)

    questions = generate_eval_questions(driver)

    if not questions:
        st.warning("Not enough data in Neo4j to generate evaluation questions. Load TMDB data first.")
        st.stop()

    st.info(f"Generated **{len(questions)}** evaluation questions across {len(set(q['category'] for q in questions))} categories.")

    # Show questions
    with st.expander("Preview Questions"):
        for i, q in enumerate(questions, 1):
            st.markdown(
                f"{i}. [{q['category']}] **{q['question']}** "
                f"(expected: {q['expected_winner']}, truth: {q['ground_truth'][:3]}...)"
            )

    if st.button("Run Full Benchmark", type="primary", key="eval_run_bench"):
        progress = st.progress(0)
        results_table = []

        for i, q in enumerate(questions):
            progress.progress((i + 1) / len(questions))

            # KG
            kg_answers, kg_detail, kg_latency = kg_retrieve(
                q["question"], driver, schema_str
            )
            kg_score = compute_score(kg_answers, q["ground_truth"])

            # Vector
            vec_answers, _, vec_latency = vector_retrieve(
                q["question"], collection
            )
            vec_score = compute_score(vec_answers, q["ground_truth"])

            # Hybrid
            hyb_answers, hyb_detail, hyb_latency = hybrid_retrieve(
                q["question"], driver, collection, schema_str
            )
            hyb_score = compute_score(hyb_answers, q["ground_truth"])

            # Determine actual winner
            scores = {"KG": kg_score, "Vector": vec_score, "Hybrid": hyb_score}
            actual_winner = max(scores, key=scores.get)
            if kg_score == vec_score == hyb_score:
                actual_winner = "Tie"

            results_table.append(
                {
                    "Category": q["category"],
                    "Question": q["question"],
                    "Expected Winner": q["expected_winner"],
                    "KG Recall": f"{kg_score:.2f}",
                    "Vector Recall": f"{vec_score:.2f}",
                    "Hybrid Recall": f"{hyb_score:.2f}",
                    "KG Latency": f"{kg_latency:.2f}s",
                    "Vector Latency": f"{vec_latency:.2f}s",
                    "Hybrid Latency": f"{hyb_latency:.2f}s",
                    "Actual Winner": actual_winner,
                }
            )

        progress.progress(1.0)
        df = pd.DataFrame(results_table)
        st.session_state.eval_results = df

    # Show results
    if "eval_results" in st.session_state:
        df = st.session_state.eval_results
        st.subheader("Results")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Summary by category
        st.subheader("Summary by Category")
        summary_data = []
        for cat in df["Category"].unique():
            cat_df = df[df["Category"] == cat]
            summary_data.append(
                {
                    "Category": cat,
                    "Avg KG Recall": f"{cat_df['KG Recall'].astype(float).mean():.2f}",
                    "Avg Vector Recall": f"{cat_df['Vector Recall'].astype(float).mean():.2f}",
                    "Avg Hybrid Recall": f"{cat_df['Hybrid Recall'].astype(float).mean():.2f}",
                    "Questions": len(cat_df),
                }
            )
        st.dataframe(pd.DataFrame(summary_data), hide_index=True)

        # Overall averages
        st.subheader("Overall Performance")
        col1, col2, col3 = st.columns(3)
        with col1:
            avg = df["KG Recall"].astype(float).mean()
            st.metric("KG Average Recall", f"{avg:.2f}")
        with col2:
            avg = df["Vector Recall"].astype(float).mean()
            st.metric("Vector Average Recall", f"{avg:.2f}")
        with col3:
            avg = df["Hybrid Recall"].astype(float).mean()
            st.metric("Hybrid Average Recall", f"{avg:.2f}")

        # Chart
        import plotly.graph_objects as go

        categories = list(df["Category"].unique()) + ["Overall"]
        kg_scores = []
        vec_scores = []
        hyb_scores = []
        for cat in df["Category"].unique():
            cat_df = df[df["Category"] == cat]
            kg_scores.append(cat_df["KG Recall"].astype(float).mean())
            vec_scores.append(cat_df["Vector Recall"].astype(float).mean())
            hyb_scores.append(cat_df["Hybrid Recall"].astype(float).mean())
        kg_scores.append(df["KG Recall"].astype(float).mean())
        vec_scores.append(df["Vector Recall"].astype(float).mean())
        hyb_scores.append(df["Hybrid Recall"].astype(float).mean())

        fig = go.Figure(
            data=[
                go.Bar(name="Knowledge Graph", x=categories, y=kg_scores, marker_color="#1f77b4"),
                go.Bar(name="Vector Search", x=categories, y=vec_scores, marker_color="#ff7f0e"),
                go.Bar(name="Hybrid", x=categories, y=hyb_scores, marker_color="#2ca02c"),
            ]
        )
        fig.update_layout(
            barmode="group",
            title="Recall by Category and Approach",
            yaxis_title="Average Recall",
            yaxis_range=[0, 1],
        )
        st.plotly_chart(fig, use_container_width=True)


# --- Analysis ---
with tab_analysis:
    st.subheader("When to Use Each Approach")

    st.markdown("""
    | Approach | Best For | Weaknesses |
    |----------|----------|------------|
    | **Knowledge Graph** | Exact lookups, relationship traversal, aggregations, multi-hop queries | Cannot handle fuzzy/thematic queries; requires exact schema knowledge |
    | **Vector Search** | Thematic similarity, fuzzy matching, "find movies like X" | No structured relationships; cannot count, aggregate, or traverse paths |
    | **Hybrid** | Complex queries needing both semantic relevance and structural precision | Higher latency (2 API calls); more complex to implement |

    ### Key Findings

    **Factual queries** (who directed X, what genre is Y) are best answered by the Knowledge Graph
    because they map directly to graph traversals with exact answers.

    **Semantic queries** (find movies about time travel, movies similar to Inception) benefit from
    vector search because they match on meaning rather than exact keywords or relationships.

    **Complex queries** (highly-rated sci-fi movies by prolific directors) benefit from the hybrid
    approach: vector search identifies relevant candidates, then graph traversal applies structural
    filters and retrieves connected entities.

    ### Architecture Recommendation

    For production systems, use a **hybrid pipeline**:
    1. **Vector search** as the first pass to identify relevant entities
    2. **Knowledge graph** as the second pass for structured filtering and relationship traversal
    3. **LLM** to synthesize the final answer from both sources

    This combines the semantic understanding of embeddings with the structural precision of a
    knowledge graph, achieving higher accuracy than either approach alone.
    """)

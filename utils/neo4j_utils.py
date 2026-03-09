import streamlit as st
from neo4j import GraphDatabase
import networkx as nx
from utils.config import (
    AURA_NEO4J_URI,
    AURA_NEO4J_USER,
    AURA_NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
)


def neo4j_sidebar_connect(key_prefix=""):
    """Render Neo4j connection sidebar and return driver or None."""
    st.sidebar.header("Neo4j Connection")

    # Default to Aura cloud if credentials exist
    use_cloud = bool(AURA_NEO4J_URI and AURA_NEO4J_USER)
    connection_type = st.sidebar.radio(
        "Connection",
        ["Aura Cloud", "Local"],
        index=0 if use_cloud else 1,
        key=f"{key_prefix}_conn_type",
    )

    if connection_type == "Aura Cloud":
        uri = st.sidebar.text_input(
            "Aura URI", AURA_NEO4J_URI, key=f"{key_prefix}_aura_uri"
        )
        username = st.sidebar.text_input(
            "Username", AURA_NEO4J_USER, key=f"{key_prefix}_aura_user"
        )
        password = st.sidebar.text_input(
            "Password",
            AURA_NEO4J_PASSWORD,
            type="password",
            key=f"{key_prefix}_aura_pass",
        )
    else:
        uri = st.sidebar.text_input(
            "Neo4j URI", NEO4J_URI, key=f"{key_prefix}_local_uri"
        )
        username = st.sidebar.text_input(
            "Username", NEO4J_USERNAME, key=f"{key_prefix}_local_user"
        )
        password = st.sidebar.text_input(
            "Password",
            NEO4J_PASSWORD,
            type="password",
            key=f"{key_prefix}_local_pass",
        )

    driver_key = f"{key_prefix}_neo4j_driver"
    if driver_key not in st.session_state:
        st.session_state[driver_key] = None

    if st.sidebar.button("Connect to Neo4j", key=f"{key_prefix}_connect_btn"):
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                session.run("RETURN 1")
            st.session_state[driver_key] = driver
            st.sidebar.success("Connected to Neo4j!")
        except Exception as e:
            st.sidebar.error(f"Connection failed: {e}")
            st.session_state[driver_key] = None

    return st.session_state[driver_key]


def execute_query(driver, query, params=None):
    """Execute a Cypher query and return list of record dicts."""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def execute_write(driver, query, params=None):
    """Execute a write Cypher query."""
    with driver.session() as session:
        session.run(query, params or {})


def get_graph_schema(driver):
    """Extract graph schema from Neo4j."""
    with driver.session() as session:
        node_schema = session.run("""
            CALL db.schema.nodeTypeProperties()
            YIELD nodeType, propertyName, propertyTypes
            RETURN nodeType, COLLECT({property: propertyName, type: propertyTypes}) as properties
        """).data()

        rel_schema = session.run("""
            CALL db.schema.relTypeProperties()
            YIELD relType, propertyName, propertyTypes
            RETURN relType, COLLECT({property: propertyName, type: propertyTypes}) as properties
        """).data()

        return {"nodes": node_schema, "relationships": rel_schema}


def format_schema(schema_info):
    """Format schema info into a string description for LLM prompts."""
    desc = "Graph Schema:\n\nNode Types:\n"
    for node in schema_info.get("nodes", []):
        props = [p["property"] for p in node["properties"] if p["property"]]
        desc += f"- {node['nodeType']}: {', '.join(props)}\n"
    desc += "\nRelationship Types:\n"
    for rel in schema_info.get("relationships", []):
        props = [p["property"] for p in rel["properties"] if p["property"]]
        desc += f"- {rel['relType']}: {', '.join(props)}\n"
    return desc


def query_to_networkx(driver, query):
    """Execute a Cypher query and return results as a NetworkX graph."""
    with driver.session() as session:
        result = session.run(query)
        G = nx.MultiDiGraph()

        for record in result:
            for value in record.values():
                if hasattr(value, "__class__"):
                    cls = value.__class__.__name__
                    if cls == "Node":
                        node_id = value.element_id
                        labels = list(value.labels)
                        props = dict(value)
                        label = props.get("name") or props.get("title") or str(node_id)
                        G.add_node(
                            node_id,
                            label=label,
                            title=f"{', '.join(labels)}\n{props}",
                            group=labels[0] if labels else "Unknown",
                        )
                    elif cls == "Relationship":
                        G.add_edge(
                            value.start_node.element_id,
                            value.end_node.element_id,
                            label=value.type,
                            title=f"{value.type}\n{dict(value)}",
                        )
        return G


def load_tmdb_to_neo4j(driver, data, progress_callback=None):
    """Load TMDB dataset into Neo4j using MERGE for idempotency."""
    with driver.session() as session:
        # Create constraints
        for constraint in [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Movie) REQUIRE m.tmdb_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.tmdb_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Genre) REQUIRE g.tmdb_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:ProductionCompany) REQUIRE c.tmdb_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.tmdb_id IS UNIQUE",
        ]:
            try:
                session.run(constraint)
            except Exception:
                pass  # Constraint may already exist

        total = 5
        step = 0

        # Load genres
        if progress_callback:
            progress_callback(step, total, "Loading genres...")
        session.run(
            """
            UNWIND $genres AS g
            MERGE (genre:Genre {tmdb_id: g.tmdb_id})
            SET genre.name = g.name
            """,
            {"genres": data["genres"]},
        )
        step += 1

        # Load people
        if progress_callback:
            progress_callback(step, total, "Loading people...")
        session.run(
            """
            UNWIND $people AS p
            MERGE (person:Person {tmdb_id: p.tmdb_id})
            SET person.name = p.name,
                person.popularity = p.popularity,
                person.known_for_department = p.known_for_department
            """,
            {"people": data["people"]},
        )
        step += 1

        # Load production companies
        if progress_callback:
            progress_callback(step, total, "Loading companies...")
        session.run(
            """
            UNWIND $companies AS c
            MERGE (co:ProductionCompany {tmdb_id: c.tmdb_id})
            SET co.name = c.name, co.origin_country = c.origin_country
            """,
            {"production_companies": data["production_companies"]},
        )
        step += 1

        # Load keywords
        if progress_callback:
            progress_callback(step, total, "Loading keywords...")
        session.run(
            """
            UNWIND $keywords AS k
            MERGE (kw:Keyword {tmdb_id: k.tmdb_id})
            SET kw.name = k.name
            """,
            {"keywords": data["keywords"]},
        )
        step += 1

        # Load movies and all relationships
        if progress_callback:
            progress_callback(step, total, "Loading movies & relationships...")

        for movie in data["movies"]:
            # Create movie node
            session.run(
                """
                MERGE (m:Movie {tmdb_id: $tmdb_id})
                SET m.title = $title,
                    m.overview = $overview,
                    m.tagline = $tagline,
                    m.release_date = $release_date,
                    m.vote_average = $vote_average,
                    m.vote_count = $vote_count,
                    m.popularity = $popularity,
                    m.budget = $budget,
                    m.revenue = $revenue,
                    m.runtime = $runtime,
                    m.original_language = $original_language
                """,
                {
                    "tmdb_id": movie["tmdb_id"],
                    "title": movie["title"],
                    "overview": movie["overview"],
                    "tagline": movie.get("tagline", ""),
                    "release_date": movie.get("release_date", ""),
                    "vote_average": movie.get("vote_average", 0),
                    "vote_count": movie.get("vote_count", 0),
                    "popularity": movie.get("popularity", 0),
                    "budget": movie.get("budget", 0),
                    "revenue": movie.get("revenue", 0),
                    "runtime": movie.get("runtime", 0),
                    "original_language": movie.get("original_language", ""),
                },
            )

            # Genre relationships
            for genre_id in movie["genres"]:
                session.run(
                    """
                    MATCH (m:Movie {tmdb_id: $movie_id}), (g:Genre {tmdb_id: $genre_id})
                    MERGE (m)-[:IN_GENRE]->(g)
                    """,
                    {"movie_id": movie["tmdb_id"], "genre_id": genre_id},
                )

            # Production company relationships
            for co_id in movie["production_companies"]:
                session.run(
                    """
                    MATCH (m:Movie {tmdb_id: $movie_id}), (c:ProductionCompany {tmdb_id: $co_id})
                    MERGE (m)-[:PRODUCED_BY]->(c)
                    """,
                    {"movie_id": movie["tmdb_id"], "co_id": co_id},
                )

            # Keyword relationships
            for kw_id in movie["keywords"]:
                session.run(
                    """
                    MATCH (m:Movie {tmdb_id: $movie_id}), (k:Keyword {tmdb_id: $kw_id})
                    MERGE (m)-[:HAS_KEYWORD]->(k)
                    """,
                    {"movie_id": movie["tmdb_id"], "kw_id": kw_id},
                )

            # Cast relationships
            for cast in movie["cast"]:
                session.run(
                    """
                    MATCH (p:Person {tmdb_id: $person_id}), (m:Movie {tmdb_id: $movie_id})
                    MERGE (p)-[r:ACTED_IN]->(m)
                    SET r.character = $character, r.credit_order = $credit_order
                    """,
                    {
                        "person_id": cast["person_id"],
                        "movie_id": movie["tmdb_id"],
                        "character": cast["character"],
                        "credit_order": cast["credit_order"],
                    },
                )

            # Director relationships
            for dir_id in movie["directors"]:
                session.run(
                    """
                    MATCH (p:Person {tmdb_id: $person_id}), (m:Movie {tmdb_id: $movie_id})
                    MERGE (p)-[:DIRECTED]->(m)
                    """,
                    {"person_id": dir_id, "movie_id": movie["tmdb_id"]},
                )

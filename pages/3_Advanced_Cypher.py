import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import os

st.set_page_config(page_title="Advanced Cypher Queries", layout="wide")

st.title("Advanced Cypher Queries & Use Cases")
st.markdown("""
This page demonstrates advanced Neo4j Cypher queries including pattern matching, path finding, 
graph algorithms, aggregations, and complex relationship queries.
""")

# Neo4j connection settings
st.sidebar.header("Neo4j Connection Settings")
uri = st.sidebar.text_input("Neo4j URI", "bolt://localhost:7687")
username = st.sidebar.text_input("Username", "neo4j")
password = st.sidebar.text_input("Password", type="password")

# Enhanced sample data initialization
def initialize_advanced_data(driver):
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create a more complex knowledge graph with multiple domains
        session.run("""
        // Movies and People
        CREATE (matrix:Movie {title: 'The Matrix', released: 1999, genre: 'Sci-Fi', rating: 8.7})
        CREATE (matrix2:Movie {title: 'The Matrix Reloaded', released: 2003, genre: 'Sci-Fi', rating: 7.2})
        CREATE (matrix3:Movie {title: 'The Matrix Revolutions', released: 2003, genre: 'Sci-Fi', rating: 6.8})
        CREATE (johnwick:Movie {title: 'John Wick', released: 2014, genre: 'Action', rating: 7.4})
        CREATE (speed:Movie {title: 'Speed', released: 1994, genre: 'Action', rating: 7.3})
        
        CREATE (keanu:Person {name: 'Keanu Reeves', born: 1964, nationality: 'Canadian'})
        CREATE (laurence:Person {name: 'Laurence Fishburne', born: 1961, nationality: 'American'})
        CREATE (carrie:Person {name: 'Carrie-Anne Moss', born: 1967, nationality: 'Canadian'})
        CREATE (lana:Person {name: 'Lana Wachowski', born: 1965, nationality: 'American'})
        CREATE (lilly:Person {name: 'Lilly Wachowski', born: 1967, nationality: 'American'})
        
        // Companies and Studios
        CREATE (wb:Studio {name: 'Warner Bros', founded: 1923, country: 'USA'})
        CREATE (village:Studio {name: 'Village Roadshow', founded: 1954, country: 'Australia'})
        
        // Characters
        CREATE (neo:Character {name: 'Neo', description: 'The One'})
        CREATE (morpheus:Character {name: 'Morpheus', description: 'Captain of Nebuchadnezzar'})
        CREATE (trinity:Character {name: 'Trinity', description: 'Hacker and pilot'})
        
        // Technologies and Concepts
        CREATE (ai:Technology {name: 'Artificial Intelligence', category: 'Computing'})
        CREATE (vr:Technology {name: 'Virtual Reality', category: 'Computing'})
        CREATE (simulation:Concept {name: 'Simulation Theory', domain: 'Philosophy'})
        
        // Relationships - Acting
        CREATE (keanu)-[:ACTED_IN {roles: ['Neo'], salary: 10000000}]->(matrix)
        CREATE (laurence)-[:ACTED_IN {roles: ['Morpheus'], salary: 5000000}]->(matrix)
        CREATE (carrie)-[:ACTED_IN {roles: ['Trinity'], salary: 3000000}]->(matrix)
        CREATE (keanu)-[:ACTED_IN {roles: ['Neo'], salary: 15000000}]->(matrix2)
        CREATE (laurence)-[:ACTED_IN {roles: ['Morpheus'], salary: 7000000}]->(matrix2)
        CREATE (carrie)-[:ACTED_IN {roles: ['Trinity'], salary: 5000000}]->(matrix2)
        CREATE (keanu)-[:ACTED_IN {roles: ['Neo'], salary: 15000000}]->(matrix3)
        CREATE (keanu)-[:ACTED_IN {roles: ['John Wick'], salary: 2000000}]->(johnwick)
        CREATE (keanu)-[:ACTED_IN {roles: ['Jack Traven'], salary: 1200000}]->(speed)
        
        // Relationships - Directing
        CREATE (lana)-[:DIRECTED {year: 1999}]->(matrix)
        CREATE (lilly)-[:DIRECTED {year: 1999}]->(matrix)
        CREATE (lana)-[:DIRECTED {year: 2003}]->(matrix2)
        CREATE (lilly)-[:DIRECTED {year: 2003}]->(matrix2)
        CREATE (lana)-[:DIRECTED {year: 2003}]->(matrix3)
        CREATE (lilly)-[:DIRECTED {year: 2003}]->(matrix3)
        
        // Relationships - Production
        CREATE (wb)-[:PRODUCED {budget: 63000000}]->(matrix)
        CREATE (village)-[:PRODUCED {budget: 63000000}]->(matrix)
        CREATE (wb)-[:PRODUCED {budget: 150000000}]->(matrix2)
        CREATE (wb)-[:PRODUCED {budget: 150000000}]->(matrix3)
        
        // Relationships - Characters
        CREATE (keanu)-[:PORTRAYED]->(neo)
        CREATE (laurence)-[:PORTRAYED]->(morpheus)
        CREATE (carrie)-[:PORTRAYED]->(trinity)
        
        // Relationships - Character interactions
        CREATE (neo)-[:KNOWS {since: 1999, relationship: 'mentor-student'}]->(morpheus)
        CREATE (neo)-[:LOVES {since: 1999}]->(trinity)
        CREATE (trinity)-[:LOVES {since: 1999}]->(neo)
        CREATE (morpheus)-[:TRUSTS {level: 'absolute'}]->(neo)
        
        // Relationships - Themes
        CREATE (matrix)-[:EXPLORES]->(ai)
        CREATE (matrix)-[:EXPLORES]->(vr)
        CREATE (matrix)-[:EXPLORES]->(simulation)
        
        // Relationships - Collaborations
        CREATE (keanu)-[:WORKED_WITH {projects: 3}]->(laurence)
        CREATE (keanu)-[:WORKED_WITH {projects: 3}]->(carrie)
        CREATE (laurence)-[:WORKED_WITH {projects: 3}]->(carrie)
        """)

# Query execution function with result formatting
def execute_query(driver, query):
    with driver.session() as session:
        result = session.run(query)
        records = [record.data() for record in result]
        return records

# Visualize query results
def visualize_query_result(driver, query):
    with driver.session() as session:
        result = session.run(query)
        G = nx.MultiDiGraph()
        
        for record in result:
            for key, value in record.items():
                if hasattr(value, '__class__'):
                    class_name = value.__class__.__name__
                    
                    # Handle nodes
                    if class_name == 'Node':
                        node_id = value.element_id
                        labels = list(value.labels)
                        props = dict(value)
                        
                        # Create a display label
                        display_label = props.get('name') or props.get('title') or str(node_id)
                        
                        G.add_node(node_id, 
                                 label=display_label,
                                 title=f"{', '.join(labels)}\n{props}",
                                 group=labels[0] if labels else 'Unknown')
                    
                    # Handle relationships
                    elif class_name == 'Relationship':
                        start_id = value.start_node.element_id
                        end_id = value.end_node.element_id
                        rel_type = value.type
                        props = dict(value)
                        
                        G.add_edge(start_id, end_id,
                                 label=rel_type,
                                 title=f"{rel_type}\n{props}")
        
        return G

def create_pyvis_network(G):
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    net.force_atlas_2based()
    
    # Add nodes
    for node in G.nodes(data=True):
        node_id = node[0]
        node_data = node[1]
        net.add_node(node_id, 
                    label=node_data.get('label', str(node_id)),
                    title=node_data.get('title', ''),
                    group=node_data.get('group', 'default'))
    
    # Add edges
    for edge in G.edges(data=True):
        edge_data = edge[2]
        net.add_edge(edge[0], edge[1],
                    label=edge_data.get('label', ''),
                    title=edge_data.get('title', ''))
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    net.save_graph(temp_file.name)
    return temp_file.name

# Advanced query categories
QUERY_CATEGORIES = {
    "Pattern Matching": {
        "Find all movies in a franchise": """
            MATCH (m:Movie)
            WHERE m.title CONTAINS 'Matrix'
            RETURN m.title, m.released, m.rating
            ORDER BY m.released
        """,
        "Find actors who worked together multiple times": """
            MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person)
            WHERE id(p1) < id(p2)
            WITH p1, p2, COUNT(DISTINCT m) as collaborations, COLLECT(m.title) as movies
            WHERE collaborations > 1
            RETURN p1.name, p2.name, collaborations, movies
            ORDER BY collaborations DESC
        """,
        "Find movies by genre and minimum rating": """
            MATCH (m:Movie)
            WHERE m.genre = 'Sci-Fi' AND m.rating >= 7.0
            RETURN m.title, m.released, m.rating, m.genre
            ORDER BY m.rating DESC
        """,
    },
    "Path Finding": {
        "Shortest path between two actors": """
            MATCH path = shortestPath(
                (keanu:Person {name: 'Keanu Reeves'})-[*]-(laurence:Person {name: 'Laurence Fishburne'})
            )
            RETURN path, length(path) as pathLength
        """,
        "All paths between actor and studio (max 4 hops)": """
            MATCH path = (keanu:Person {name: 'Keanu Reeves'})-[*1..4]-(wb:Studio {name: 'Warner Bros'})
            RETURN path, length(path) as pathLength
            ORDER BY pathLength
            LIMIT 5
        """,
        "Find connection chain from actor to concept": """
            MATCH path = (keanu:Person {name: 'Keanu Reeves'})-[*]-(concept:Concept)
            RETURN path, length(path) as pathLength
            ORDER BY pathLength
            LIMIT 3
        """,
    },
    "Aggregations & Analytics": {
        "Total earnings per actor": """
            MATCH (p:Person)-[r:ACTED_IN]->(m:Movie)
            WITH p, SUM(r.salary) as totalEarnings, COUNT(m) as movieCount
            RETURN p.name, totalEarnings, movieCount
            ORDER BY totalEarnings DESC
        """,
        "Average movie rating by genre": """
            MATCH (m:Movie)
            WITH m.genre as genre, AVG(m.rating) as avgRating, COUNT(m) as movieCount
            RETURN genre, avgRating, movieCount
            ORDER BY avgRating DESC
        """,
        "Studio investment analysis": """
            MATCH (s:Studio)-[r:PRODUCED]->(m:Movie)
            WITH s, SUM(r.budget) as totalInvestment, COUNT(m) as moviesProduced, AVG(m.rating) as avgRating
            RETURN s.name, totalInvestment, moviesProduced, avgRating
            ORDER BY totalInvestment DESC
        """,
    },
    "Complex Relationships": {
        "Find love triangles": """
            MATCH (p1:Character)-[:LOVES]->(p2:Character)-[:LOVES]->(p3:Character)
            RETURN p1.name, p2.name, p3.name
        """,
        "Mutual relationships (bidirectional)": """
            MATCH (c1:Character)-[r1:LOVES]->(c2:Character)-[r2:LOVES]->(c1)
            RETURN c1.name, c2.name, r1, r2
        """,
        "Find actors and their character relationships": """
            MATCH (p:Person)-[:PORTRAYED]->(c1:Character)-[r]->(c2:Character)<-[:PORTRAYED]-(p2:Person)
            RETURN p.name, c1.name, type(r) as relationship, c2.name, p2.name
        """,
    },
    "Graph Algorithms": {
        "Node degree centrality (most connected)": """
            MATCH (n)
            WITH n, size((n)-[]->()) + size((n)<-[]-()) as degree
            WHERE degree > 0
            RETURN labels(n)[0] as nodeType, 
                   COALESCE(n.name, n.title) as nodeName, 
                   degree
            ORDER BY degree DESC
            LIMIT 10
        """,
        "Find isolated nodes (no connections)": """
            MATCH (n)
            WHERE NOT (n)-[]-()
            RETURN labels(n) as labels, n
        """,
        "Community detection (connected components)": """
            MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
            WITH p, COLLECT(DISTINCT m.genre) as genres
            RETURN p.name, genres, size(genres) as genreCount
            ORDER BY genreCount DESC
        """,
    },
    "Temporal Queries": {
        "Career timeline for an actor": """
            MATCH (p:Person {name: 'Keanu Reeves'})-[r:ACTED_IN]->(m:Movie)
            RETURN m.title, m.released, r.salary
            ORDER BY m.released
        """,
        "Movies released in a decade": """
            MATCH (m:Movie)
            WHERE m.released >= 2000 AND m.released < 2010
            RETURN m.title, m.released, m.genre
            ORDER BY m.released
        """,
        "Director career progression": """
            MATCH (d:Person)-[r:DIRECTED]->(m:Movie)
            WITH d, m, r.year as year
            RETURN d.name, COLLECT(m.title) as movies, COLLECT(year) as years
            ORDER BY d.name
        """,
    },
    "Recommendation Queries": {
        "Recommend movies based on actor preferences": """
            MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m1:Movie)
            MATCH (m1)<-[:ACTED_IN]-(other:Person)-[:ACTED_IN]->(m2:Movie)
            WHERE NOT (p)-[:ACTED_IN]->(m2)
            RETURN m2.title, m2.genre, COUNT(*) as recommendations, COLLECT(DISTINCT other.name) as coActors
            ORDER BY recommendations DESC
            LIMIT 5
        """,
        "Find similar movies by theme": """
            MATCH (m1:Movie {title: 'The Matrix'})-[:EXPLORES]->(t:Technology)<-[:EXPLORES]-(m2:Movie)
            WHERE m1 <> m2
            RETURN m2.title, COLLECT(t.name) as sharedThemes, m2.rating
            ORDER BY m2.rating DESC
        """,
        "Recommend collaborators for directors": """
            MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
            WITH d, a, COUNT(m) as collaborations
            WHERE collaborations >= 2
            RETURN d.name as director, a.name as frequentCollaborator, collaborations
            ORDER BY collaborations DESC
        """,
    },
}

# Main app
def main():
    # Connection management
    if 'driver' not in st.session_state:
        st.session_state.driver = None
    
    # Connect button
    if st.sidebar.button("Connect to Neo4j"):
        try:
            st.session_state.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Test connection
            with st.session_state.driver.session() as session:
                session.run("RETURN 1")
            st.sidebar.success("✅ Connected to Neo4j!")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to connect: {str(e)}")
            st.session_state.driver = None
    
    # Initialize sample data
    if st.session_state.driver and st.sidebar.button("Initialize Advanced Sample Data"):
        try:
            initialize_advanced_data(st.session_state.driver)
            st.sidebar.success("✅ Advanced sample data initialized!")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to initialize data: {str(e)}")
    
    # Main content
    if st.session_state.driver:
        st.subheader("Select Query Category and Example")
        
        # Category selection
        category = st.selectbox("Query Category:", list(QUERY_CATEGORIES.keys()))
        
        # Query selection within category
        query_name = st.selectbox("Select Query:", list(QUERY_CATEGORIES[category].keys()))
        
        # Display selected query
        selected_query = QUERY_CATEGORIES[category][query_name]
        
        st.code(selected_query, language="cypher")
        
        # Custom query option
        use_custom = st.checkbox("Use custom query instead")
        if use_custom:
            custom_query = st.text_area("Enter your Cypher query:", height=150)
            if custom_query.strip():
                selected_query = custom_query
        
        # Execute query
        col1, col2 = st.columns([1, 1])
        with col1:
            show_viz = st.checkbox("Show graph visualization", value=True)
        with col2:
            show_table = st.checkbox("Show table results", value=True)
        
        if st.button("🚀 Execute Query", type="primary"):
            try:
                with st.spinner("Executing query..."):
                    # Show visualization
                    if show_viz:
                        st.subheader("Graph Visualization")
                        G = visualize_query_result(st.session_state.driver, selected_query)
                        
                        if len(G.nodes()) > 0:
                            temp_file = create_pyvis_network(G)
                            with open(temp_file, 'r') as f:
                                html = f.read()
                            st.components.v1.html(html, height=600)
                            os.unlink(temp_file)
                            
                            # Graph statistics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Nodes", len(G.nodes()))
                            with col2:
                                st.metric("Edges", len(G.edges()))
                            with col3:
                                st.metric("Density", f"{nx.density(G):.3f}")
                        else:
                            st.info("No graph structure to visualize")
                    
                    # Show table results
                    if show_table:
                        st.subheader("Query Results")
                        results = execute_query(st.session_state.driver, selected_query)
                        
                        if results:
                            df = pd.DataFrame(results)
                            st.dataframe(df, use_container_width=True)
                            
                            # Download option
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download as CSV",
                                data=csv,
                                file_name="query_results.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("Query returned no results")
                
            except Exception as e:
                st.error(f"❌ Query execution failed: {str(e)}")
    
    else:
        st.info("👈 Please connect to Neo4j using the sidebar to begin exploring advanced queries.")
        
        # Show example queries even without connection
        st.subheader("Available Query Categories")
        for cat, queries in QUERY_CATEGORIES.items():
            with st.expander(f"📁 {cat}"):
                for query_name, query in queries.items():
                    st.markdown(f"**{query_name}**")
                    st.code(query, language="cypher")

if __name__ == "__main__":
    main()

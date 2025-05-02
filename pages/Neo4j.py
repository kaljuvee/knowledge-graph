import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import os

st.set_page_config(page_title="Neo4j Knowledge Graph Explorer", layout="wide")

st.title("Neo4j Knowledge Graph Explorer")
st.markdown("""
This page demonstrates knowledge graph visualization using Neo4j, a popular graph database.
You can connect to your Neo4j instance and explore the graph data interactively.
""")

# Neo4j connection settings
st.sidebar.header("Neo4j Connection Settings")
uri = st.sidebar.text_input("Neo4j URI", "bolt://localhost:7687")
username = st.sidebar.text_input("Username", "neo4j")
password = st.sidebar.text_input("Password", type="password")

# Sample data initialization function
def initialize_sample_data(driver):
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create sample movie data
        session.run("""
        CREATE (matrix:Movie {title: 'The Matrix', released: 1999})
        CREATE (keanu:Person {name: 'Keanu Reeves', born: 1964})
        CREATE (laurence:Person {name: 'Laurence Fishburne', born: 1961})
        CREATE (carrie:Person {name: 'Carrie-Anne Moss', born: 1967})
        CREATE (morpheus:Character {name: 'Morpheus'})
        CREATE (trinity:Character {name: 'Trinity'})
        CREATE (neo:Character {name: 'Neo'})
        
        CREATE (keanu)-[:ACTED_IN {roles: ['Neo']}]->(matrix)
        CREATE (laurence)-[:ACTED_IN {roles: ['Morpheus']}]->(matrix)
        CREATE (carrie)-[:ACTED_IN {roles: ['Trinity']}]->(matrix)
        CREATE (keanu)-[:PORTRAYED]->(neo)
        CREATE (laurence)-[:PORTRAYED]->(morpheus)
        CREATE (carrie)-[:PORTRAYED]->(trinity)
        """)

# Function to query Neo4j and return results as a NetworkX graph
def query_to_graph(driver, query):
    with driver.session() as session:
        result = session.run(query)
        G = nx.Graph()
        
        for record in result:
            for node in record.values():
                if hasattr(node, 'labels'):
                    G.add_node(node.id, 
                             labels=list(node.labels),
                             properties=dict(node))
                elif hasattr(node, 'type'):
                    G.add_edge(node.start_node.id,
                             node.end_node.id,
                             type=node.type,
                             properties=dict(node))
        return G

# Function to visualize the graph using Pyvis
def visualize_pyvis(G):
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # Add nodes with labels and properties
    for node in G.nodes():
        labels = G.nodes[node].get('labels', [])
        properties = G.nodes[node].get('properties', {})
        title = f"Labels: {', '.join(labels)}\nProperties: {properties}"
        net.add_node(node, title=title, label=str(node))
    
    # Add edges with types and properties
    for edge in G.edges():
        edge_data = G.edges[edge]
        edge_type = edge_data.get('type', '')
        properties = edge_data.get('properties', {})
        title = f"Type: {edge_type}\nProperties: {properties}"
        net.add_edge(edge[0], edge[1], title=title)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    net.save_graph(temp_file.name)
    return temp_file.name

# Main app
def main():
    if st.sidebar.button("Connect to Neo4j"):
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            st.sidebar.success("Connected to Neo4j!")
            
            # Initialize sample data
            if st.sidebar.button("Initialize Sample Data"):
                initialize_sample_data(driver)
                st.sidebar.success("Sample data initialized!")
            
            # Query selection
            query = st.selectbox(
                "Select a query to run:",
                [
                    "MATCH (n) RETURN n",
                    "MATCH (p:Person)-[r]->(m:Movie) RETURN p, r, m",
                    "MATCH (p:Person)-[r:ACTED_IN]->(m:Movie) RETURN p, r, m",
                    "MATCH (p:Person)-[r:PORTRAYED]->(c:Character) RETURN p, r, c"
                ]
            )
            
            if st.button("Run Query"):
                G = query_to_graph(driver, query)
                
                # Display graph
                temp_file = visualize_pyvis(G)
                with open(temp_file, 'r') as f:
                    html = f.read()
                st.components.v1.html(html, height=600)
                os.unlink(temp_file)
                
                # Display statistics
                st.subheader("Graph Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Number of Nodes", len(G.nodes))
                with col2:
                    st.metric("Number of Edges", len(G.edges))
                with col3:
                    st.metric("Average Degree", f"{sum(dict(G.degree()).values())/len(G.nodes):.2f}")
                
                # Display node and edge information
                st.subheader("Node Information")
                node_data = []
                for node in G.nodes():
                    node_data.append({
                        'ID': node,
                        'Labels': ', '.join(G.nodes[node].get('labels', [])),
                        'Properties': str(G.nodes[node].get('properties', {}))
                    })
                st.dataframe(pd.DataFrame(node_data))
                
                st.subheader("Edge Information")
                edge_data = []
                for edge in G.edges():
                    edge_data.append({
                        'Source': edge[0],
                        'Target': edge[1],
                        'Type': G.edges[edge].get('type', ''),
                        'Properties': str(G.edges[edge].get('properties', {}))
                    })
                st.dataframe(pd.DataFrame(edge_data))
            
            driver.close()
            
        except Exception as e:
            st.sidebar.error(f"Failed to connect to Neo4j: {str(e)}")

if __name__ == "__main__":
    main() 
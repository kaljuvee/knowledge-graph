import streamlit as st
import networkx as nx
from pyvis.network import Network
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tempfile
import os

st.set_page_config(page_title="Knowledge Graph Explorer", layout="wide")

st.title("Knowledge Graph Explorer")
st.markdown("""
This app demonstrates the concept of knowledge graphs using open-source tools.
A knowledge graph is a network of entities and their relationships, where nodes represent entities
and edges represent relationships between them.
""")

# Sample data
@st.cache_data
def create_sample_data():
    # Create a sample knowledge graph about movies and actors
    data = {
        'source': ['The Matrix', 'The Matrix', 'Keanu Reeves', 'Keanu Reeves', 'Laurence Fishburne', 'Carrie-Anne Moss'],
        'target': ['Keanu Reeves', 'Laurence Fishburne', 'Carrie-Anne Moss', 'John Wick', 'Morpheus', 'Trinity'],
        'relationship': ['stars_in', 'stars_in', 'co_stars_with', 'portrayed_by', 'portrayed_by', 'portrayed_by']
    }
    return pd.DataFrame(data)

# Create the graph
def create_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row['source'], row['target'], title=row['relationship'])
    return G

# Visualize using Pyvis
def visualize_pyvis(G):
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    net.from_nx(G)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    net.save_graph(temp_file.name)
    return temp_file.name

# Visualize using NetworkX
def visualize_networkx(G):
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=2000, font_size=10, font_weight='bold')
    plt.title("Knowledge Graph Visualization")
    return plt

# Main app
def main():
    df = create_sample_data()
    
    st.subheader("Sample Knowledge Graph Data")
    st.dataframe(df)
    
    G = create_graph(df)
    
    # Visualization options
    viz_option = st.radio(
        "Choose visualization method:",
        ["Pyvis (Interactive)", "NetworkX (Static)"]
    )
    
    if viz_option == "Pyvis (Interactive)":
        temp_file = visualize_pyvis(G)
        with open(temp_file, 'r') as f:
            html = f.read()
        st.components.v1.html(html, height=600)
        os.unlink(temp_file)
    else:
        fig = visualize_networkx(G)
        st.pyplot(fig)
    
    # Graph statistics
    st.subheader("Graph Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Number of Nodes", len(G.nodes))
    with col2:
        st.metric("Number of Edges", len(G.edges))
    with col3:
        st.metric("Average Degree", f"{np.mean([d for n, d in G.degree()]):.2f}")
    
    # Explanation
    st.subheader("Understanding Knowledge Graphs")
    st.markdown("""
    - **Nodes**: Represent entities (e.g., movies, actors, characters)
    - **Edges**: Represent relationships between entities
    - **Properties**: Additional information about nodes and edges
    - **Semantics**: Meaningful connections that create context
    """)

if __name__ == "__main__":
    main() 
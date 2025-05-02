import streamlit as st
import networkx as nx
import pandas as pd
import numpy as np
from pyvis.network import Network
import plotly.graph_objects as go
import tempfile
import os
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Business Network Explorer", layout="wide")

# Sample data generation
def generate_sample_business_data():
    companies = {
        "TechCorp": {"industry": "Technology", "size": "Large", "revenue": 500000000},
        "InnovateSoft": {"industry": "Software", "size": "Medium", "revenue": 150000000},
        "DataAnalytics": {"industry": "Data Services", "size": "Medium", "revenue": 120000000},
        "CloudSolutions": {"industry": "Cloud Computing", "size": "Large", "revenue": 450000000},
        "SecureNet": {"industry": "Cybersecurity", "size": "Small", "revenue": 50000000},
        "AILabs": {"industry": "Artificial Intelligence", "size": "Medium", "revenue": 200000000},
        "QuantumTech": {"industry": "Quantum Computing", "size": "Small", "revenue": 80000000},
        "BlockchainCo": {"industry": "Blockchain", "size": "Small", "revenue": 40000000},
        "RoboticsPro": {"industry": "Robotics", "size": "Medium", "revenue": 180000000},
        "SmartSystems": {"industry": "IoT", "size": "Large", "revenue": 350000000}
    }
    
    relationships = [
        ("TechCorp", "InnovateSoft", {"type": "Partnership", "strength": 0.8, "duration": 36}),
        ("TechCorp", "CloudSolutions", {"type": "Investment", "strength": 0.9, "duration": 24}),
        ("InnovateSoft", "DataAnalytics", {"type": "Client", "strength": 0.7, "duration": 12}),
        ("CloudSolutions", "SecureNet", {"type": "Partnership", "strength": 0.6, "duration": 18}),
        ("DataAnalytics", "AILabs", {"type": "Joint Venture", "strength": 0.9, "duration": 24}),
        ("AILabs", "QuantumTech", {"type": "Research", "strength": 0.7, "duration": 12}),
        ("BlockchainCo", "SecureNet", {"type": "Technology", "strength": 0.8, "duration": 6}),
        ("RoboticsPro", "SmartSystems", {"type": "Supply Chain", "strength": 0.7, "duration": 36}),
        ("TechCorp", "SmartSystems", {"type": "Investment", "strength": 0.9, "duration": 24}),
        ("AILabs", "SmartSystems", {"type": "Research", "strength": 0.6, "duration": 12})
    ]
    
    return companies, relationships

def create_graph(companies, relationships):
    G = nx.Graph()
    
    # Add nodes with attributes
    for company, attributes in companies.items():
        G.add_node(company, **attributes)
    
    # Add edges with attributes
    for source, target, attributes in relationships:
        G.add_edge(source, target, **attributes)
    
    return G

def visualize_pyvis(G):
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    net.force_atlas_2based()
    
    # Add nodes with size based on revenue and color based on industry
    industry_colors = {
        "Technology": "#1f77b4",
        "Software": "#ff7f0e",
        "Data Services": "#2ca02c",
        "Cloud Computing": "#d62728",
        "Cybersecurity": "#9467bd",
        "Artificial Intelligence": "#8c564b",
        "Quantum Computing": "#e377c2",
        "Blockchain": "#7f7f7f",
        "Robotics": "#bcbd22",
        "IoT": "#17becf"
    }
    
    for node in G.nodes():
        revenue = G.nodes[node]["revenue"]
        industry = G.nodes[node]["industry"]
        size = revenue / 10000000  # Scale revenue to reasonable node size
        
        net.add_node(
            node,
            label=node,
            title=f"Company: {node}<br>Industry: {industry}<br>Revenue: ${revenue:,}",
            size=size,
            color=industry_colors.get(industry, "#666666")
        )
    
    # Add edges with width based on relationship strength
    for edge in G.edges(data=True):
        source, target, data = edge
        width = data["strength"] * 5  # Scale strength to reasonable edge width
        net.add_edge(
            source,
            target,
            title=f"Type: {data['type']}<br>Strength: {data['strength']}<br>Duration: {data['duration']} months",
            width=width
        )
    
    # Generate the HTML file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    net.save_graph(temp_file.name)
    return temp_file.name

def plot_plotly(G):
    # Create edge traces
    edge_x = []
    edge_y = []
    edge_text = []
    
    pos = nx.spring_layout(G)
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_text.append(f"Type: {edge[2]['type']}<br>Strength: {edge[2]['strength']}")
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='text',
        text=edge_text,
        mode='lines')
    
    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(
            f"Company: {node}<br>" +
            f"Industry: {G.nodes[node]['industry']}<br>" +
            f"Revenue: ${G.nodes[node]['revenue']:,}"
        )
        node_size.append(G.nodes[node]['revenue'] / 10000000)
        # Map industry to a number for color
        industries = list(set(nx.get_node_attributes(G, 'industry').values()))
        node_color.append(industries.index(G.nodes[node]['industry']))
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        marker=dict(
            showscale=True,
            colorscale='Viridis',
            size=node_size,
            color=node_color,
            colorbar=dict(
                title='Industry',
                ticktext=industries,
                tickvals=list(range(len(industries)))
            )
        )
    )
    
    # Create the figure
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=0, l=0, r=0, t=0),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                   ))
    
    return fig

def analyze_network(G):
    # Basic network metrics
    metrics = {
        "Number of Companies": len(G.nodes()),
        "Number of Relationships": len(G.edges()),
        "Average Degree": sum(dict(G.degree()).values()) / len(G.nodes()),
        "Network Density": nx.density(G),
        "Average Clustering Coefficient": nx.average_clustering(G),
    }
    
    # Centrality measures
    degree_centrality = nx.degree_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)
    eigenvector_centrality = nx.eigenvector_centrality(G)
    
    # Most central companies
    central_companies = {
        "Degree Centrality": max(degree_centrality.items(), key=lambda x: x[1])[0],
        "Betweenness Centrality": max(betweenness_centrality.items(), key=lambda x: x[1])[0],
        "Eigenvector Centrality": max(eigenvector_centrality.items(), key=lambda x: x[1])[0]
    }
    
    return metrics, central_companies

def main():
    st.title("Business Network Explorer")
    st.markdown("""
    Explore business relationships and network analytics using NetworkX and interactive visualizations.
    This demo shows a sample network of technology companies and their various relationships.
    """)
    
    # Generate sample data
    companies, relationships = generate_sample_business_data()
    G = create_graph(companies, relationships)
    
    # Visualization options
    viz_option = st.radio(
        "Choose visualization method:",
        ["Interactive Network (Pyvis)", "Interactive Plot (Plotly)"]
    )
    
    if viz_option == "Interactive Network (Pyvis)":
        temp_file = visualize_pyvis(G)
        with open(temp_file, 'r') as f:
            html = f.read()
        st.components.v1.html(html, height=600)
        os.unlink(temp_file)
    else:
        fig = plot_plotly(G)
        st.plotly_chart(fig, use_container_width=True)
    
    # Network Analysis
    st.subheader("Network Analysis")
    metrics, central_companies = analyze_network(G)
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Number of Companies", metrics["Number of Companies"])
        st.metric("Network Density", f"{metrics['Network Density']:.2f}")
    with col2:
        st.metric("Number of Relationships", metrics["Number of Relationships"])
        st.metric("Average Clustering", f"{metrics['Average Clustering Coefficient']:.2f}")
    with col3:
        st.metric("Average Degree", f"{metrics['Average Degree']:.2f}")
    
    # Display central companies
    st.subheader("Most Central Companies")
    central_col1, central_col2, central_col3 = st.columns(3)
    with central_col1:
        st.metric("By Connections", central_companies["Degree Centrality"])
    with central_col2:
        st.metric("By Network Flow", central_companies["Betweenness Centrality"])
    with central_col3:
        st.metric("By Influence", central_companies["Eigenvector Centrality"])
    
    # Display company details
    st.subheader("Company Details")
    company_df = pd.DataFrame.from_dict(companies, orient='index')
    st.dataframe(company_df)
    
    # Display relationship details
    st.subheader("Relationship Details")
    relationship_df = pd.DataFrame(relationships, columns=['Source', 'Target', 'Attributes'])
    relationship_df['Type'] = relationship_df['Attributes'].apply(lambda x: x['type'])
    relationship_df['Strength'] = relationship_df['Attributes'].apply(lambda x: x['strength'])
    relationship_df['Duration (months)'] = relationship_df['Attributes'].apply(lambda x: x['duration'])
    relationship_df = relationship_df.drop('Attributes', axis=1)
    st.dataframe(relationship_df)

if __name__ == "__main__":
    main() 
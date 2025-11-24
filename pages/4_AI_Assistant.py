import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import os
from openai import OpenAI

st.set_page_config(page_title="AI Assistant - Text to Cypher", layout="wide")

st.title("🤖 AI Assistant - Natural Language to Cypher")
st.markdown("""
Ask questions about your graph in natural language, and the AI will convert them to Cypher queries.
This page demonstrates **Text-to-Cypher** capabilities using Large Language Models.
""")

# Neo4j connection settings
st.sidebar.header("Neo4j Connection Settings")
uri = st.sidebar.text_input("Neo4j URI", "bolt://localhost:7687")
username = st.sidebar.text_input("Username", "neo4j")
password = st.sidebar.text_input("Password", type="password")

# OpenAI settings
st.sidebar.header("AI Model Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                       value=os.getenv("OPENAI_API_KEY", ""))
model_choice = st.sidebar.selectbox("Model", ["gpt-4.1-mini", "gpt-4.1-nano", "gemini-2.5-flash"], index=0)

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    return OpenAI()

# Get graph schema
def get_graph_schema(driver):
    """Extract the graph schema from Neo4j"""
    with driver.session() as session:
        # Get node labels and their properties
        node_schema = session.run("""
            CALL db.schema.nodeTypeProperties()
            YIELD nodeType, propertyName, propertyTypes
            RETURN nodeType, COLLECT({property: propertyName, type: propertyTypes}) as properties
        """).data()
        
        # Get relationship types and their properties
        rel_schema = session.run("""
            CALL db.schema.relTypeProperties()
            YIELD relType, propertyName, propertyTypes
            RETURN relType, COLLECT({property: propertyName, type: propertyTypes}) as properties
        """).data()
        
        # Get relationship patterns
        patterns = session.run("""
            CALL db.schema.visualization()
            YIELD nodes, relationships
            RETURN nodes, relationships
        """).data()
        
        return {
            "nodes": node_schema,
            "relationships": rel_schema,
            "patterns": patterns
        }

# Get sample data
def get_sample_data(driver, limit=5):
    """Get sample nodes and relationships"""
    with driver.session() as session:
        samples = session.run(f"""
            MATCH (n)
            WITH DISTINCT labels(n)[0] as label, n
            RETURN label, COLLECT(n)[0..{limit}] as samples
        """).data()
        
        return samples

# Convert natural language to Cypher
def text_to_cypher(question, schema_info, sample_data, model="gpt-4.1-mini"):
    """Use OpenAI to convert natural language to Cypher query"""
    
    client = get_openai_client()
    
    # Build schema description
    schema_desc = "Graph Schema:\n\n"
    schema_desc += "Node Types:\n"
    for node in schema_info.get("nodes", []):
        schema_desc += f"- {node['nodeType']}: "
        props = [p['property'] for p in node['properties']]
        schema_desc += f"{', '.join(props)}\n"
    
    schema_desc += "\nRelationship Types:\n"
    for rel in schema_info.get("relationships", []):
        schema_desc += f"- {rel['relType']}: "
        props = [p['property'] for p in rel['properties']]
        schema_desc += f"{', '.join(props)}\n"
    
    # Build sample data description
    sample_desc = "\n\nSample Data:\n"
    for sample in sample_data[:3]:  # Limit samples
        sample_desc += f"- {sample['label']}: {sample['samples'][:2]}\n"
    
    system_prompt = f"""You are a Neo4j Cypher query expert. Convert natural language questions into valid Cypher queries.

{schema_desc}
{sample_desc}

Rules:
1. Generate ONLY valid Cypher syntax
2. Use MATCH, WHERE, RETURN statements appropriately
3. Include LIMIT clauses for large result sets (default LIMIT 20)
4. Use proper relationship syntax: -[:REL_TYPE]->
5. Return meaningful column names
6. For aggregations, use COUNT, SUM, AVG, etc.
7. For pattern matching, use appropriate WHERE clauses
8. Always consider the schema provided above
9. Return ONLY the Cypher query, no explanations or markdown formatting
10. Do not include ```cypher or ``` markers

Examples:
Question: "Show me all movies"
Query: MATCH (m:Movie) RETURN m.title, m.released, m.rating LIMIT 20

Question: "Who acted in The Matrix?"
Query: MATCH (p:Person)-[:ACTED_IN]->(m:Movie {{title: 'The Matrix'}}) RETURN p.name, p.born

Question: "Find actors who worked together"
Query: MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person) WHERE id(p1) < id(p2) RETURN p1.name, p2.name, m.title LIMIT 20
"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        cypher_query = response.choices[0].message.content.strip()
        
        # Clean up any markdown formatting that might have slipped through
        cypher_query = cypher_query.replace("```cypher", "").replace("```", "").strip()
        
        return cypher_query
    
    except Exception as e:
        st.error(f"Error generating Cypher query: {str(e)}")
        return None

# Execute query and return results
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
    net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
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

# Sample questions
SAMPLE_QUESTIONS = [
    "Show me all movies released after 2000",
    "Who are the actors in The Matrix?",
    "Which actors have worked together in multiple movies?",
    "What is the average rating of Sci-Fi movies?",
    "Find all directors and the movies they directed",
    "Show me the highest-paid actors",
    "Which studios produced The Matrix?",
    "Find all characters and who portrayed them",
    "What technologies are explored in The Matrix?",
    "Show me movies with a rating above 8.0",
    "Find the shortest path between Keanu Reeves and Warner Bros",
    "Which actors have worked with Lana Wachowski?",
    "Show me all relationships between characters",
    "What is the total budget spent by each studio?",
    "Find actors born in the 1960s",
]

# Main app
def main():
    # Connection management
    if 'driver' not in st.session_state:
        st.session_state.driver = None
    if 'schema_info' not in st.session_state:
        st.session_state.schema_info = None
    if 'sample_data' not in st.session_state:
        st.session_state.sample_data = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Connect button
    if st.sidebar.button("Connect to Neo4j"):
        try:
            st.session_state.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Test connection
            with st.session_state.driver.session() as session:
                session.run("RETURN 1")
            st.sidebar.success("✅ Connected to Neo4j!")
            
            # Load schema and sample data
            with st.spinner("Loading graph schema..."):
                st.session_state.schema_info = get_graph_schema(st.session_state.driver)
                st.session_state.sample_data = get_sample_data(st.session_state.driver)
            st.sidebar.success("✅ Schema loaded!")
            
        except Exception as e:
            st.sidebar.error(f"❌ Failed to connect: {str(e)}")
            st.session_state.driver = None
    
    # Main content
    if st.session_state.driver and openai_api_key:
        
        # Show schema info in expander
        with st.expander("📊 View Graph Schema"):
            if st.session_state.schema_info:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Node Types")
                    for node in st.session_state.schema_info.get("nodes", []):
                        st.markdown(f"**{node['nodeType']}**")
                        props = [p['property'] for p in node['properties']]
                        st.text(f"Properties: {', '.join(props)}")
                
                with col2:
                    st.subheader("Relationship Types")
                    for rel in st.session_state.schema_info.get("relationships", []):
                        st.markdown(f"**{rel['relType']}**")
                        props = [p['property'] for p in rel['properties']]
                        st.text(f"Properties: {', '.join(props)}")
        
        # Sample questions
        st.subheader("💡 Sample Questions")
        cols = st.columns(3)
        for idx, question in enumerate(SAMPLE_QUESTIONS[:6]):
            col_idx = idx % 3
            with cols[col_idx]:
                if st.button(question, key=f"sample_{idx}", use_container_width=True):
                    st.session_state.current_question = question
        
        # Question input
        st.subheader("Ask a Question")
        question = st.text_input(
            "Enter your question in natural language:",
            value=st.session_state.get('current_question', ''),
            placeholder="e.g., Show me all actors who worked in Sci-Fi movies"
        )
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            generate_button = st.button("🎯 Generate Cypher Query", type="primary")
        with col2:
            show_viz = st.checkbox("Show visualization", value=True)
        with col3:
            if st.button("🗑️ Clear History"):
                st.session_state.chat_history = []
                st.rerun()
        
        if generate_button and question:
            with st.spinner("🤔 Thinking..."):
                # Generate Cypher query
                cypher_query = text_to_cypher(
                    question, 
                    st.session_state.schema_info,
                    st.session_state.sample_data,
                    model=model_choice
                )
                
                if cypher_query:
                    st.subheader("Generated Cypher Query")
                    st.code(cypher_query, language="cypher")
                    
                    # Execute query
                    try:
                        with st.spinner("Executing query..."):
                            results = execute_query(st.session_state.driver, cypher_query)
                            
                            # Add to chat history
                            st.session_state.chat_history.append({
                                "question": question,
                                "query": cypher_query,
                                "results": results,
                                "success": True
                            })
                            
                            if results:
                                # Show results
                                st.subheader("Results")
                                df = pd.DataFrame(results)
                                st.dataframe(df, use_container_width=True)
                                
                                st.success(f"✅ Query returned {len(results)} results")
                                
                                # Download option
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Results as CSV",
                                    data=csv,
                                    file_name="query_results.csv",
                                    mime="text/csv"
                                )
                                
                                # Visualization
                                if show_viz:
                                    try:
                                        st.subheader("Graph Visualization")
                                        G = visualize_query_result(st.session_state.driver, cypher_query)
                                        
                                        if len(G.nodes()) > 0:
                                            temp_file = create_pyvis_network(G)
                                            with open(temp_file, 'r') as f:
                                                html = f.read()
                                            st.components.v1.html(html, height=500)
                                            os.unlink(temp_file)
                                        else:
                                            st.info("No graph structure to visualize (query returns scalar values)")
                                    except Exception as viz_error:
                                        st.warning(f"Visualization not available: {str(viz_error)}")
                            else:
                                st.info("Query executed successfully but returned no results")
                    
                    except Exception as e:
                        st.error(f"❌ Query execution failed: {str(e)}")
                        st.session_state.chat_history.append({
                            "question": question,
                            "query": cypher_query,
                            "error": str(e),
                            "success": False
                        })
        
        # Show chat history
        if st.session_state.chat_history:
            st.subheader("📜 Query History")
            for idx, item in enumerate(reversed(st.session_state.chat_history[-5:])):
                with st.expander(f"Q: {item['question']}", expanded=(idx == 0)):
                    st.code(item['query'], language="cypher")
                    if item['success']:
                        st.success(f"✅ Returned {len(item['results'])} results")
                    else:
                        st.error(f"❌ Error: {item.get('error', 'Unknown error')}")
    
    elif not st.session_state.driver:
        st.info("👈 Please connect to Neo4j using the sidebar to begin.")
        
        # Show sample questions even without connection
        st.subheader("💡 Example Questions You Can Ask")
        for i, question in enumerate(SAMPLE_QUESTIONS, 1):
            st.markdown(f"{i}. {question}")
    
    elif not openai_api_key:
        st.warning("⚠️ Please provide an OpenAI API key in the sidebar to use the AI Assistant.")
        st.info("You can get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    ### How it works
    1. **Connect** to your Neo4j database
    2. **Ask** questions in natural language
    3. **AI generates** Cypher queries automatically
    4. **View** results as tables and graphs
    
    The AI uses the graph schema and sample data to generate accurate Cypher queries.
    """)

if __name__ == "__main__":
    main()

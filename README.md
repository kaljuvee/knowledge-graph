# Knowledge Graph Explorer

A comprehensive Streamlit application for exploring and visualizing knowledge graphs using NetworkX and Neo4j, with advanced Cypher queries and AI-powered natural language to Cypher conversion.

## Demo

A live demo of this application is available at: [https://knowledge-graph-demo.streamlit.app/](https://knowledge-graph-demo.streamlit.app/)

## Features

### Core Features
- **Open-source knowledge graph visualization** using NetworkX and Pyvis
- **Neo4j integration** with sample movie database
- **Interactive graph visualization** with node and edge exploration
- **Graph statistics and analytics** including centrality measures
- **Sample queries and data exploration**

### Advanced Features (NEW!)
- **Advanced Cypher Queries**: 7 categories with 20+ pre-built complex queries
  - Pattern Matching
  - Path Finding
  - Aggregations & Analytics
  - Complex Relationships
  - Graph Algorithms
  - Temporal Queries
  - Recommendation Queries
- **AI Assistant (Text-to-Cypher)**: Convert natural language questions to Cypher queries using OpenAI
- **Enhanced sample dataset** with movies, actors, directors, studios, characters, and themes
- **Query history tracking** and result export capabilities

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/kaljuvee/knowledge-graph.git
cd knowledge-graph
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)

For the AI Assistant feature, you'll need an OpenAI API key:

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

Alternatively, you can enter the API key directly in the Streamlit UI.

### 5. Neo4j Setup Options

#### Option 1: Local Neo4j Installation (Ubuntu/Linux)

1. Add the Neo4j repository and update package list:
```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 4.1' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
```

2. Install Neo4j:
```bash
sudo apt-get install neo4j
```

3. Start Neo4j service:
```bash
sudo systemctl start neo4j
```

4. Enable Neo4j to start on boot:
```bash
sudo systemctl enable neo4j
```

5. Check Neo4j status:
```bash
sudo systemctl status neo4j
```

6. Set initial password (replace 'your-password' with your desired password):
```bash
sudo neo4j-admin set-initial-password your-password
```

#### Option 2: Neo4j Aura (Cloud Service - Recommended)

1. Go to [Neo4j Aura](https://neo4j.com/cloud/aura/)
2. Sign up for a free account
3. Create a new database instance
4. Note down the connection details:
   - URI (bolt:// or neo4j://)
   - Username (usually 'neo4j')
   - Password

#### Option 3: Neo4j Sandbox (Free Learning Environment)

1. Go to [Neo4j Sandbox](https://sandbox.neo4j.com/)
2. Sign up or log in
3. Choose a sample dataset (e.g., "Movies", "Northwind", "Game of Thrones")
4. Note down the connection details:
   - URI (bolt:// or neo4j://)
   - Username (usually 'neo4j')
   - Password

## Usage

1. Start the Streamlit application:
```bash
streamlit run Home.py
```

2. Access the application in your web browser at: `http://localhost:8501`

3. Navigate between pages:
   - **Home**: Open-source knowledge graph visualization with NetworkX
   - **Neo4j**: Basic Neo4j-based knowledge graph exploration
   - **NetworkX**: NetworkX-specific graph operations
   - **Advanced Cypher**: 20+ pre-built advanced Cypher queries
   - **AI Assistant**: Natural language to Cypher query conversion

### Neo4j Connection Settings

When using the Neo4j pages, you'll need to provide:
- **URI**: 
  - Local: `bolt://localhost:7687`
  - Aura/Sandbox: Use the provided URI
- **Username**: `neo4j`
- **Password**: Use the password you set or was provided

### Using the AI Assistant

1. Navigate to the **AI Assistant** page
2. Connect to your Neo4j database
3. Enter your OpenAI API key (or set it in `.env`)
4. Ask questions in natural language, such as:
   - "Show me all movies released after 2000"
   - "Who are the actors in The Matrix?"
   - "Which actors have worked together in multiple movies?"
   - "What is the average rating of Sci-Fi movies?"

The AI will automatically generate and execute the appropriate Cypher query!

## Advanced Cypher Query Examples

The **Advanced Cypher** page includes pre-built queries in these categories:

### Pattern Matching
```cypher
// Find actors who worked together multiple times
MATCH (p1:Person)-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(p2:Person)
WHERE id(p1) < id(p2)
WITH p1, p2, COUNT(DISTINCT m) as collaborations, COLLECT(m.title) as movies
WHERE collaborations > 1
RETURN p1.name, p2.name, collaborations, movies
ORDER BY collaborations DESC
```

### Path Finding
```cypher
// Shortest path between two actors
MATCH path = shortestPath(
    (keanu:Person {name: 'Keanu Reeves'})-[*]-(laurence:Person {name: 'Laurence Fishburne'})
)
RETURN path, length(path) as pathLength
```

### Aggregations & Analytics
```cypher
// Total earnings per actor
MATCH (p:Person)-[r:ACTED_IN]->(m:Movie)
WITH p, SUM(r.salary) as totalEarnings, COUNT(m) as movieCount
RETURN p.name, totalEarnings, movieCount
ORDER BY totalEarnings DESC
```

### Recommendation Queries
```cypher
// Recommend movies based on actor preferences
MATCH (p:Person {name: 'Keanu Reeves'})-[:ACTED_IN]->(m1:Movie)
MATCH (m1)<-[:ACTED_IN]-(other:Person)-[:ACTED_IN]->(m2:Movie)
WHERE NOT (p)-[:ACTED_IN]->(m2)
RETURN m2.title, m2.genre, COUNT(*) as recommendations, COLLECT(DISTINCT other.name) as coActors
ORDER BY recommendations DESC
LIMIT 5
```

## Sample Queries for Neo4j Sandbox

If you're using Neo4j Sandbox, try these sample queries:

### Movies Database:
```cypher
// Find all movies Tom Hanks acted in
MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m:Movie)
RETURN m.title, m.released

// Find all people who directed a movie
MATCH (p:Person)-[:DIRECTED]->(m:Movie)
RETURN p.name, m.title

// Find all co-actors of Tom Hanks
MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(coActor:Person)
RETURN coActor.name
```

### Northwind Database:
```cypher
// Find all products in a category
MATCH (c:Category {categoryName: 'Beverages'})<-[:PART_OF]-(p:Product)
RETURN p.productName, p.unitPrice

// Find all orders for a customer
MATCH (c:Customer {companyName: 'Alfreds Futterkiste'})<-[:PURCHASED]-(o:Order)
RETURN o.orderID, o.orderDate
```

## Troubleshooting

If you encounter any issues:

1. For local installation:
```bash
sudo systemctl status neo4j
sudo journalctl -u neo4j
```

2. For Aura/Sandbox:
- Check your internet connection
- Verify the connection details
- Try refreshing the database instance

3. Common connection issues:
- Check if ports are in use:
```bash
sudo lsof -i :7474
sudo lsof -i :7687
```

4. If you need to stop local Neo4j:
```bash
sudo systemctl stop neo4j
```

5. For AI Assistant issues:
- Verify your OpenAI API key is valid
- Check that you have sufficient API credits
- Ensure the graph schema is loaded (connect to Neo4j first)

## Project Structure

```
knowledge-graph/
├── Home.py                      # Main application with open-source visualization
├── pages/
│   ├── Neo4j.py                # Basic Neo4j integration and visualization
│   ├── NetworkX.py             # NetworkX-specific operations
│   ├── 3_Advanced_Cypher.py    # Advanced Cypher queries (NEW!)
│   └── 4_AI_Assistant.py       # Text-to-Cypher AI assistant (NEW!)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # This file
```

## Dependencies

- streamlit==1.32.0
- neo4j==5.17.0
- networkx==3.2.1
- matplotlib==3.8.2
- pyvis==0.3.2
- pandas==2.2.0
- numpy==1.26.3
- plotly
- openai>=1.0.0

## API Keys

The AI Assistant requires an OpenAI API key. You can:
1. Set it as an environment variable: `OPENAI_API_KEY`
2. Add it to a `.env` file (copy from `.env.example`)
3. Enter it directly in the Streamlit UI

Get your API key from: [OpenAI Platform](https://platform.openai.com/api-keys)

## Use Cases

This application is ideal for:
- **Learning Neo4j and Cypher**: Explore pre-built queries and see results instantly
- **Graph Database Prototyping**: Test queries and visualize results before production
- **Data Exploration**: Understand complex relationships in your data
- **AI-Powered Querying**: Let non-technical users query graph databases using natural language
- **Teaching and Demos**: Showcase graph database capabilities interactively

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License - feel free to use this project for learning and development.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Graph database powered by [Neo4j](https://neo4j.com/)
- Visualization using [Pyvis](https://pyvis.readthedocs.io/) and [NetworkX](https://networkx.org/)
- AI capabilities powered by [OpenAI](https://openai.com/)

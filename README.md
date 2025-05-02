# Knowledge Graph Explorer

A Streamlit application for exploring and visualizing knowledge graphs using NetworkX and Neo4j.

## Demo

A live demo of this application is available at: [https://knowledge-graph-demo.streamlit.app/](https://knowledge-graph-demo.streamlit.app/)

## Features

- Open-source knowledge graph visualization using NetworkX and Pyvis
- Neo4j integration with sample movie database
- Interactive graph visualization
- Graph statistics and analytics
- Sample queries and data exploration

## Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd knowledge-graph
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Neo4j Setup Options

#### Option 1: Local Neo4j Installation (Ubuntu)

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

#### Option 2: Neo4j Aura (Cloud Service)

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
- Home: Open-source knowledge graph visualization
- Neo4j: Neo4j-based knowledge graph exploration

### Neo4j Connection Settings

When using the Neo4j page, you'll need to provide:
- URI: 
  - Local: `bolt://localhost:7687`
  - Aura/Sandbox: Use the provided URI
- Username: `neo4j`
- Password: Use the password you set or was provided

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

## Project Structure

```
knowledge-graph/
├── Home.py              # Main application with open-source visualization
├── pages/
│   └── Neo4j.py        # Neo4j integration and visualization
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Dependencies

- streamlit==1.32.0
- neo4j==5.17.0
- networkx==3.2.1
- matplotlib==3.8.2
- pyvis==0.3.2
- pandas==2.2.0
- numpy==1.26.3

## License

[Your chosen license]

## Contributing

[Your contribution guidelines]
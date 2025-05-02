# Knowledge Graph Explorer

A Streamlit application that demonstrates knowledge graph visualization using both open-source tools and Neo4j. The application provides interactive visualizations of graph data and allows users to explore different aspects of knowledge graphs.

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

### 4. Install Neo4j on Ubuntu

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

7. Configure Neo4j to accept remote connections (optional):
```bash
sudo nano /etc/neo4j/neo4j.conf
```
Find and uncomment these lines:
```
#server.default_listen_address=0.0.0.0
#server.bolt.listen_address=:7687
```

8. Restart Neo4j to apply changes:
```bash
sudo systemctl restart neo4j
```

9. Access Neo4j Browser:
- Open your web browser and navigate to: `http://localhost:7474`
- Login with:
  - Username: `neo4j`
  - Password: `your-password`

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
- URI: `bolt://localhost:7687`
- Username: `neo4j`
- Password: `your-password`

## Troubleshooting

If you encounter any issues:

1. Check Neo4j service status:
```bash
sudo systemctl status neo4j
```

2. View Neo4j logs:
```bash
sudo journalctl -u neo4j
```

3. Check if ports are in use:
```bash
sudo lsof -i :7474
sudo lsof -i :7687
```

4. If you need to stop Neo4j:
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
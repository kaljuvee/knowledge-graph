# Architecture

## System Overview

```mermaid
graph TB
    subgraph "Data Sources"
        TMDB["TMDB API<br/>(movies, cast, crew)"]
        OMDB["OMDB API<br/>(ratings, awards)"]
    end

    subgraph "Storage Layer"
        Neo4j[("Neo4j Aura<br/>Knowledge Graph")]
        ChromaDB[("ChromaDB<br/>Vector Store")]
    end

    subgraph "AI Layer"
        Embed["OpenAI Embeddings<br/>text-embedding-3-small"]
        LLM["OpenAI LLM<br/>gpt-4.1-mini"]
    end

    subgraph "Utility Layer"
        config["utils/config.py"]
        tmdb["utils/tmdb_client.py"]
        neo4j_u["utils/neo4j_utils.py"]
        openai_u["utils/openai_utils.py"]
    end

    subgraph "Streamlit Pages"
        P1["Home.py<br/>NetworkX Demo"]
        P2["Neo4j.py<br/>Basic Queries"]
        P3["NetworkX.py<br/>Business Network"]
        P4["3_Advanced_Cypher.py<br/>Query Library"]
        P5["4_AI_Assistant.py<br/>Text-to-Cypher"]
        P6["5_TMDB_Data.py<br/>Data Pipeline"]
        P7["6_Conversational_Cypher.py<br/>Multi-Turn Analysis"]
        P8["7_Vector_Search.py<br/>Semantic Search"]
        P9["8_Evaluation.py<br/>KG vs Vector vs Hybrid"]
    end

    TMDB --> tmdb
    OMDB --> tmdb
    tmdb --> P6
    P6 --> Neo4j
    P6 --> ChromaDB
    Embed --> openai_u
    LLM --> openai_u
    neo4j_u --> Neo4j
    P7 --> neo4j_u
    P7 --> openai_u
    P8 --> ChromaDB
    P8 --> openai_u
    P9 --> neo4j_u
    P9 --> openai_u
    P9 --> ChromaDB
    config --> tmdb
    config --> neo4j_u
    config --> openai_u
```

## Data Model (Neo4j)

```mermaid
erDiagram
    Movie ||--o{ ACTED_IN : has
    Person ||--o{ ACTED_IN : performs
    Movie ||--o{ DIRECTED : has
    Person ||--o{ DIRECTED : directs
    Movie }o--o{ IN_GENRE : categorized
    Genre ||--o{ IN_GENRE : contains
    Movie }o--o{ PRODUCED_BY : made_by
    ProductionCompany ||--o{ PRODUCED_BY : produces
    Movie }o--o{ HAS_KEYWORD : tagged
    Keyword ||--o{ HAS_KEYWORD : tags

    Movie {
        int tmdb_id PK
        string title
        string overview
        string tagline
        string release_date
        float vote_average
        int vote_count
        float popularity
        int budget
        int revenue
        int runtime
        string original_language
    }
    Person {
        int tmdb_id PK
        string name
        float popularity
        string known_for_department
    }
    Genre {
        int tmdb_id PK
        string name
    }
    ProductionCompany {
        int tmdb_id PK
        string name
        string origin_country
    }
    Keyword {
        int tmdb_id PK
        string name
    }
    ACTED_IN {
        string character
        int credit_order
    }
```

## Data Pipeline

```mermaid
flowchart LR
    A["TMDB API"] -->|fetch_popular_movies| B["Raw JSON"]
    B -->|build_graph_data| C["Structured Dataset"]
    C -->|load_tmdb_to_neo4j| D[("Neo4j")]
    C -->|embed + index| E[("ChromaDB")]
    D -->|Cypher queries| F["KG Retrieval"]
    E -->|similarity search| G["Vector Retrieval"]
    F --> H["Hybrid Pipeline"]
    G --> H
    H --> I["Evaluation & Comparison"]
```

## Retrieval Strategy Comparison

```mermaid
flowchart TB
    Q["User Question"]

    subgraph KG["Knowledge Graph (KG)"]
        direction TB
        K1["Text-to-Cypher<br/>(LLM generates query)"]
        K2["Execute Cypher<br/>against Neo4j"]
        K3["Structured Results<br/>(exact matches, traversals)"]
        K1 --> K2 --> K3
    end

    subgraph VEC["Vector Search"]
        direction TB
        V1["Embed Question<br/>(text-embedding-3-small)"]
        V2["ChromaDB<br/>Similarity Search"]
        V3["Semantic Results<br/>(thematically similar)"]
        V1 --> V2 --> V3
    end

    subgraph HYB["Hybrid"]
        direction TB
        H1["Vector Search<br/>(find relevant entities)"]
        H2["Use entities as<br/>Cypher starting points"]
        H3["Graph Traversal<br/>(structural context)"]
        H4["Combined Results"]
        H1 --> H2 --> H3 --> H4
    end

    Q --> KG
    Q --> VEC
    Q --> HYB
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | Streamlit | Multi-page interactive UI |
| Graph Database | Neo4j Aura (cloud) | Knowledge graph storage and Cypher queries |
| Vector Database | ChromaDB (embedded) | Semantic similarity search |
| Embeddings | OpenAI text-embedding-3-small | Convert text to vectors |
| LLM | OpenAI gpt-4.1-mini | Text-to-Cypher, conversation |
| Data Source | TMDB + OMDB APIs | Movie metadata, cast, crew |
| Visualization | Pyvis, Plotly, Matplotlib | Graph and chart rendering |
| Graph Algorithms | NetworkX | Centrality, community detection |

## Page Dependencies

| Page | Neo4j | ChromaDB | OpenAI | TMDB API |
|------|-------|----------|--------|----------|
| Home | - | - | - | - |
| Neo4j | required | - | - | - |
| NetworkX | - | - | - | - |
| Advanced Cypher | required | - | - | - |
| AI Assistant | required | - | required | - |
| TMDB Data | required | optional | optional | required |
| Conversational Cypher | required | - | required | - |
| Vector Search | - | required | required | - |
| Evaluation | required | required | required | - |

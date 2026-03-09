import streamlit as st
import pandas as pd
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.neo4j_utils import (
    neo4j_sidebar_connect,
    execute_query,
    get_graph_schema,
    format_schema,
    query_to_networkx,
)
from utils.openai_utils import chat_completion
from utils.config import OPENAI_API_KEY, LLM_MODEL

st.set_page_config(page_title="Conversational Cypher", layout="wide")
st.title("Multi-Turn Conversational Cypher")
st.markdown("""
Explore your knowledge graph through **conversational, multi-turn queries**.
Each question builds on previous context — ask follow-ups like
*"now filter those by rating"* or *"who directed those movies?"*.
""")

# Sidebar
driver = neo4j_sidebar_connect(key_prefix="conv")

st.sidebar.header("AI Settings")
model = st.sidebar.selectbox("Model", ["gpt-4.1-mini", "gpt-4.1-nano"], key="conv_model")

# Pre-built analytical workflows
WORKFLOWS = {
    "Revenue Analysis": [
        "What are the top 10 highest-grossing movies?",
        "Who directed those movies?",
        "What genres do those directors typically work in?",
        "Among those genres, which has the highest average rating?",
    ],
    "Actor Network": [
        "Who are the 5 most prolific actors by movie count?",
        "Which of those actors have worked together?",
        "What are the shared movies between the most connected pair?",
        "What keywords are associated with those shared movies?",
    ],
    "Genre Deep Dive": [
        "What genres have the most movies?",
        "What is the average rating and total revenue per genre?",
        "For the top-rated genre, who are the most active directors?",
        "What keywords appear most often in that genre?",
    ],
}

# Session state
if "conv_messages" not in st.session_state:
    st.session_state.conv_messages = []
if "conv_context" not in st.session_state:
    st.session_state.conv_context = []
if "conv_schema" not in st.session_state:
    st.session_state.conv_schema = None


def generate_cypher(question, schema_str, context):
    """Generate Cypher query with conversation context."""
    context_str = ""
    for turn in context:
        context_str += f"\nUser: {turn['question']}\n"
        context_str += f"Cypher: {turn['query']}\n"
        if turn.get("result_summary"):
            context_str += f"Result: {turn['result_summary']}\n"

    system_prompt = f"""You are a Neo4j Cypher expert in a multi-turn conversation. Generate Cypher queries
that build on previous context.

{schema_str}

CONVERSATION SO FAR:
{context_str if context_str else "(This is the first question)"}

RULES:
1. Return ONLY a valid JSON object with keys: "cypher", "explanation", "follow_ups"
2. "cypher": the Cypher query string (no markdown, no backticks)
3. "explanation": brief natural language explanation of what the query does
4. "follow_ups": list of 2-3 suggested follow-up questions
5. When user says "those", "them", "that" etc., reference entities from previous results
6. Default LIMIT 20 for large result sets
7. Use property names exactly as they appear in the schema
8. For TMDB data: movies have tmdb_id, title, overview, vote_average, revenue, runtime, release_date;
   people have tmdb_id, name; relationships include ACTED_IN (character, credit_order), DIRECTED, IN_GENRE, PRODUCED_BY, HAS_KEYWORD"""

    response = chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        model=model,
        temperature=0.1,
        max_tokens=1000,
    )

    # Parse JSON response
    response = response.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[1] if "\n" in response else response[3:]
        response = response.rsplit("```", 1)[0]

    try:
        parsed = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        # Fallback: treat entire response as Cypher
        return {
            "cypher": response.replace("```cypher", "").replace("```", "").strip(),
            "explanation": "Generated query",
            "follow_ups": [],
        }


def summarize_results(results, max_rows=5):
    """Create a brief summary of query results for context."""
    if not results:
        return "No results returned"
    n = len(results)
    sample = results[:max_rows]
    cols = list(sample[0].keys()) if sample else []
    summary = f"{n} rows with columns: {', '.join(cols)}. "
    if n <= max_rows:
        summary += f"Data: {json.dumps(sample, default=str)}"
    else:
        summary += f"First {max_rows}: {json.dumps(sample, default=str)}"
    return summary


# Main
if not driver:
    st.info("Connect to Neo4j in the sidebar to begin.")
    st.subheader("Example Analytical Workflows")
    for name, steps in WORKFLOWS.items():
        with st.expander(name):
            for i, step in enumerate(steps, 1):
                st.markdown(f"{i}. {step}")
    st.stop()

if not OPENAI_API_KEY:
    st.warning("Set OPENAI_API_KEY in .env for AI query generation.")
    st.stop()

# Load schema
if not st.session_state.conv_schema:
    try:
        st.session_state.conv_schema = get_graph_schema(driver)
    except Exception as e:
        st.warning(f"Could not load schema: {e}. Queries may be less accurate.")
        st.session_state.conv_schema = {"nodes": [], "relationships": []}

schema_str = format_schema(st.session_state.conv_schema)

# Workflow sidebar
st.sidebar.header("Analytical Workflows")
selected_workflow = st.sidebar.selectbox(
    "Load a workflow", ["(none)"] + list(WORKFLOWS.keys()), key="conv_workflow"
)
if st.sidebar.button("Load Workflow Steps", key="conv_load_wf"):
    if selected_workflow != "(none)":
        st.session_state.conv_workflow_steps = WORKFLOWS[selected_workflow]
        st.session_state.conv_workflow_idx = 0

if st.sidebar.button("Clear Conversation", key="conv_clear"):
    st.session_state.conv_messages = []
    st.session_state.conv_context = []
    st.session_state.pop("conv_workflow_steps", None)
    st.session_state.pop("conv_workflow_idx", None)
    st.rerun()

# Display conversation history
for msg in st.session_state.conv_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("cypher"):
            st.code(msg["cypher"], language="cypher")
        if msg.get("dataframe") is not None:
            st.dataframe(pd.DataFrame(msg["dataframe"]), use_container_width=True)
        if msg.get("follow_ups"):
            st.caption("Suggested follow-ups: " + " | ".join(msg["follow_ups"]))

# Determine next question
next_question = None
workflow_steps = st.session_state.get("conv_workflow_steps")
workflow_idx = st.session_state.get("conv_workflow_idx", 0)

if workflow_steps and workflow_idx < len(workflow_steps):
    st.info(f"Workflow step {workflow_idx + 1}/{len(workflow_steps)}: **{workflow_steps[workflow_idx]}**")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Run Step", type="primary", key="conv_run_step"):
            next_question = workflow_steps[workflow_idx]
            st.session_state.conv_workflow_idx = workflow_idx + 1

# Free-form input
user_input = st.chat_input("Ask about your movie database...")
if user_input:
    next_question = user_input

# Process question
if next_question:
    # Add user message
    st.session_state.conv_messages.append({"role": "user", "content": next_question})
    with st.chat_message("user"):
        st.write(next_question)

    # Generate Cypher
    with st.chat_message("assistant"):
        with st.spinner("Generating query..."):
            parsed = generate_cypher(next_question, schema_str, st.session_state.conv_context)

        cypher = parsed.get("cypher", "")
        explanation = parsed.get("explanation", "")
        follow_ups = parsed.get("follow_ups", [])

        st.write(explanation)
        st.code(cypher, language="cypher")

        # Execute
        try:
            results = execute_query(driver, cypher)
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                st.caption(f"{len(results)} results returned")

                # Add to context
                st.session_state.conv_context.append(
                    {
                        "question": next_question,
                        "query": cypher,
                        "result_summary": summarize_results(results),
                    }
                )

                # Add assistant message
                st.session_state.conv_messages.append(
                    {
                        "role": "assistant",
                        "content": explanation,
                        "cypher": cypher,
                        "dataframe": results[:50],
                        "follow_ups": follow_ups,
                    }
                )
            else:
                st.info("Query returned no results.")
                st.session_state.conv_context.append(
                    {
                        "question": next_question,
                        "query": cypher,
                        "result_summary": "No results",
                    }
                )
                st.session_state.conv_messages.append(
                    {
                        "role": "assistant",
                        "content": f"{explanation}\n\n*No results returned.*",
                        "cypher": cypher,
                        "follow_ups": follow_ups,
                    }
                )

            if follow_ups:
                st.caption("Suggested follow-ups: " + " | ".join(follow_ups))

        except Exception as e:
            st.error(f"Query failed: {e}")
            st.session_state.conv_context.append(
                {
                    "question": next_question,
                    "query": cypher,
                    "result_summary": f"Error: {e}",
                }
            )
            st.session_state.conv_messages.append(
                {
                    "role": "assistant",
                    "content": f"{explanation}\n\nQuery failed: {e}",
                    "cypher": cypher,
                }
            )

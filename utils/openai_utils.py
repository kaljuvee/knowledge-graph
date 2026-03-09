import streamlit as st
from openai import OpenAI
from utils.config import OPENAI_API_KEY, EMBEDDING_MODEL, LLM_MODEL


@st.cache_resource
def get_client():
    """Cached OpenAI client singleton."""
    return OpenAI(api_key=OPENAI_API_KEY)


def get_embedding(text, model=EMBEDDING_MODEL):
    """Get embedding vector for a single text."""
    client = get_client()
    resp = client.embeddings.create(input=[text], model=model)
    return resp.data[0].embedding


def get_embeddings_batch(texts, model=EMBEDDING_MODEL, batch_size=100):
    """Batch embed texts. Returns list of embedding vectors."""
    client = get_client()
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([d.embedding for d in resp.data])
    return all_embeddings


def chat_completion(messages, model=LLM_MODEL, temperature=0.1, max_tokens=1000):
    """Chat completion returning content string."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()

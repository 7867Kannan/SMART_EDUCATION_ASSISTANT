import streamlit as st
from sentence_transformers import SentenceTransformer


# ============================================================
# MULTILINGUAL EMBEDDING MODEL
# ============================================================

MODEL_NAME = "Tamil-ai/tamil-embed-base"


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

@st.cache_resource
def load_embedding_model():

    model = SentenceTransformer(
        MODEL_NAME
    )

    return model


# ============================================================
# GENERATE DOCUMENT EMBEDDINGS
# ============================================================

def generate_embeddings(chunks):

    model = load_embedding_model()

    embeddings = model.encode(
        chunks,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    return embeddings


# ============================================================
# GENERATE QUERY EMBEDDING
# ============================================================

def generate_query_embedding(query):

    model = load_embedding_model()

    embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    return embedding


# ============================================================
# GET MODEL
# ============================================================

def get_model():

    return load_embedding_model()
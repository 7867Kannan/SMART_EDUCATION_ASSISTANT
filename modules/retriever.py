import numpy as np


# ============================================================
# RETRIEVAL CONFIGURATION
# ============================================================

DEFAULT_TOP_K = 3
DEFAULT_CANDIDATE_K = 8

# Minimum cosine similarity required for a result to be
# considered relevant.
#
# This is deliberately moderate because similarity scores
# depend on the embedding model and the document.
MIN_SIMILARITY = 0.45


# ============================================================
# RETRIEVE RELEVANT DOCUMENT CHUNKS
# ============================================================

def retrieve_chunks(
    query,
    model,
    index,
    chunks,
    top_k=DEFAULT_TOP_K,
    candidate_k=DEFAULT_CANDIDATE_K,
    min_similarity=MIN_SIMILARITY
):

    # --------------------------------------------------------
    # SAFETY CHECKS
    # --------------------------------------------------------

    if not query or not query.strip():
        return [], []

    if index is None:
        return [], []

    if not chunks:
        return [], []

    if index.ntotal == 0:
        return [], []


    # --------------------------------------------------------
    # CREATE QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )


    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )


    # --------------------------------------------------------
    # DETERMINE NUMBER OF CANDIDATES
    # --------------------------------------------------------

    candidate_k = min(
        candidate_k,
        index.ntotal
    )


    # --------------------------------------------------------
    # FAISS SEMANTIC SEARCH
    # --------------------------------------------------------

    scores, indices = index.search(
        query_embedding,
        candidate_k
    )


    retrieved_chunks = []
    retrieved_scores = []


    # --------------------------------------------------------
    # FILTER RESULTS USING SIMILARITY THRESHOLD
    # --------------------------------------------------------

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        # Ignore invalid FAISS indexes
        if idx == -1:
            continue


        # Convert similarity score to float
        score = float(score)


        # Ignore weakly related chunks
        if score < min_similarity:
            continue


        # Safety check for chunk index
        if idx >= len(chunks):
            continue


        retrieved_chunks.append(
            chunks[idx]
        )

        retrieved_scores.append(
            score
        )


        # Stop after collecting enough relevant chunks
        if len(retrieved_chunks) >= top_k:
            break


    return (
        retrieved_chunks,
        retrieved_scores
    )
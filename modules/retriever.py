import numpy as np


# ============================================================
# RETRIEVE RELEVANT CHUNKS
# ============================================================

def retrieve_chunks(
    query,
    model,
    index,
    chunks,
    top_k=3,
    candidate_k=8
):
    """
    Retrieve the most relevant chunks.

    candidate_k:
        Number of candidates initially retrieved
        from FAISS.

    top_k:
        Number of final results returned.
    """

    # --------------------------------------------------------
    # Generate query embedding
    # --------------------------------------------------------

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )


    # --------------------------------------------------------
    # Convert to float32
    # --------------------------------------------------------

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )


    # --------------------------------------------------------
    # Make sure candidate_k does not exceed
    # the number of vectors in FAISS
    # --------------------------------------------------------

    candidate_k = min(
        candidate_k,
        index.ntotal
    )


    # --------------------------------------------------------
    # Search FAISS
    # --------------------------------------------------------

    scores, indices = index.search(
        query_embedding,
        candidate_k
    )


    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    retrieved_chunks = []

    retrieved_scores = []


    # --------------------------------------------------------
    # Select best results
    # --------------------------------------------------------

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        if idx == -1:

            continue


        retrieved_chunks.append(
            chunks[idx]
        )

        retrieved_scores.append(
            float(score)
        )


        # Stop after top_k results
        if len(
            retrieved_chunks
        ) >= top_k:

            break


    return (
        retrieved_chunks,
        retrieved_scores
    )
import os

import faiss
import numpy as np


# ============================================================
# CREATE FAISS INDEX
# ============================================================

def create_faiss_index(embeddings):

    # Convert embeddings to float32
    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    # Get embedding dimension
    dimension = embeddings.shape[1]

    # --------------------------------------------------------
    # IndexFlatIP uses Inner Product.
    #
    # Since our embeddings are normalized,
    # Inner Product is equivalent to Cosine Similarity.
    # --------------------------------------------------------

    index = faiss.IndexFlatIP(
        dimension
    )

    # Add vectors
    index.add(
        embeddings
    )

    return index


# ============================================================
# SAVE FAISS INDEX
# ============================================================

def save_faiss_index(
    index,
    file_path
):

    directory = os.path.dirname(
        file_path
    )

    if directory:

        os.makedirs(
            directory,
            exist_ok=True
        )

    faiss.write_index(
        index,
        file_path
    )


# ============================================================
# LOAD FAISS INDEX
# ============================================================

def load_faiss_index(
    file_path
):

    if not os.path.exists(
        file_path
    ):

        return None

    return faiss.read_index(
        file_path
    )
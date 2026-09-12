import os
import pickle


# ============================================================
# SAVE CHUNKS
# ============================================================

def save_chunks(
    chunks,
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


    with open(
        file_path,
        "wb"
    ) as file:

        pickle.dump(
            chunks,
            file
        )


# ============================================================
# LOAD CHUNKS
# ============================================================

def load_chunks(
    file_path
):

    if not os.path.exists(
        file_path
    ):

        return None


    with open(
        file_path,
        "rb"
    ) as file:

        return pickle.load(
            file
        )
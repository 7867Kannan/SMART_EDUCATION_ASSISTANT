import re


def clean_text(text):
    """
    Clean extracted PDF text.
    """

    # Replace multiple spaces/newlines with one space
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Remove page markers
    text = re.sub(
        r"-{2,} Page \d+ -{2,}",
        "",
        text
    )

    return text.strip()


def create_chunks(
    text,
    chunk_size=400,
    overlap=80
):
    """
    Create overlapping word-based chunks.

    chunk_size:
        Number of words in each chunk.

    overlap:
        Number of words shared between
        consecutive chunks.
    """

    words = text.split()

    chunks = []

    # Move forward by chunk_size - overlap
    step = chunk_size - overlap

    for i in range(
        0,
        len(words),
        step
    ):

        chunk = " ".join(
            words[
                i:i + chunk_size
            ]
        )

        if chunk.strip():

            chunks.append(
                chunk
            )

        # Stop after final chunk
        if i + chunk_size >= len(words):

            break

    return chunks
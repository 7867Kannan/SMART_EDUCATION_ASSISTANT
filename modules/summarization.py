import ollama

MODEL_NAME = "phi3:mini"

FALLBACK_SUMMARY = (
    "A summary could not be generated from the uploaded document."
)

# Number of representative chunks sent to Phi-3
SUMMARY_CHUNKS = 24


def _select_representative_chunks(chunks):
    """
    Select representative chunks from across the document.

    This avoids sending all document chunks to Phi-3 while still
    providing coverage from the beginning, middle, and end.
    """

    if not chunks:
        return []

    if len(chunks) <= SUMMARY_CHUNKS:
        return chunks

    step = (len(chunks) - 1) / (SUMMARY_CHUNKS - 1)

    selected = []

    for i in range(SUMMARY_CHUNKS):
        index = round(i * step)
        selected.append(chunks[index])

    return selected


def generate_summary(chunks):
    """
    Generate a fast, source-faithful study summary.

    Only representative chunks are sent to Phi-3 Mini so that
    summarization remains fast on CPU-only systems.
    """

    if not chunks:
        return FALLBACK_SUMMARY

    selected_chunks = _select_representative_chunks(
        chunks
    )

    context_parts = []

    for i, chunk in enumerate(
        selected_chunks,
        start=1
    ):
        context_parts.append(
            f"[Document Section {i}]\n{chunk}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are an educational study-note summarization assistant.

Create a concise study summary using ONLY the information
contained in the DOCUMENT SECTIONS below.

The summary is for an engineering student who wants to revise
the uploaded educational material.

============================================================
STRICT SOURCE RULE
============================================================

Use ONLY information present in the provided document sections.

DO NOT use outside knowledge.

DO NOT invent information.

DO NOT invent examples.

DO NOT add definitions that are not present.

DO NOT add applications that are not present.

DO NOT add advantages or disadvantages unless they appear
in the document.

DO NOT make unsupported conclusions.

DO NOT change the technical meaning.

Preserve important technical terminology.

If a detail is not present in the provided sections,
do not mention it.

============================================================
SUMMARY REQUIREMENTS
============================================================

1. Start directly with the subject.

2. Do not write:
   "The document provides..."
   "This document discusses..."
   "The chapter explains..."

3. Remove unnecessary repetition.

4. Include the major concepts supported by the sections.

5. Keep the summary concise.

6. Make it useful for engineering exam revision.

7. Use headings and bullet points when appropriate.

8. Preserve important technical terms in English.

9. Do not introduce information from your general knowledge.

10. Do not create a generic conclusion.

============================================================
PREFERRED FORMAT
============================================================

## Main Topic

- Important point

## Key Concepts

- Concept: explanation

## Important Components

- Component: explanation

## Important Processes

- Process: explanation

Use only the headings that are supported by the
document content.

============================================================
IMPORTANT
============================================================

The document sections are representative portions of the
uploaded document.

Summarize ONLY what is actually present in these sections.

Do not guess missing information.

Do not mention:

RAG
FAISS
Phi-3
language model
retrieved chunks
prompt
context
AI system architecture

============================================================
DOCUMENT SECTIONS
============================================================

{context}

============================================================
FINAL OUTPUT
============================================================

Write ONLY the final study summary.

Do not include an introduction about the document.

Do not include a generic conclusion.
"""

    try:

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.0,
                "num_predict": 450
            }
        )

        summary = response[
            "message"
        ][
            "content"
        ].strip()

        if not summary:
            return FALLBACK_SUMMARY

        # Remove common unwanted prefixes
        prefixes = [
            "SUMMARY:",
            "Summary:",
            "FINAL SUMMARY:",
            "Final Summary:"
        ]

        for prefix in prefixes:

            if summary.startswith(prefix):

                summary = summary[
                    len(prefix):
                ].strip()

        # Correct only obvious generation errors.
        replacements = {

            "Artifics Intelligence":
                "Artificial Intelligence",

            "artifics intelligence":
                "Artificial Intelligence",

            "Artifical Intelligence":
                "Artificial Intelligence",

            "Artifical intelligence":
                "Artificial Intelligence",

            "insthood":
                "understanding"
        }

        for wrong, correct in replacements.items():

            summary = summary.replace(
                wrong,
                correct
            )

        if not summary:
            return FALLBACK_SUMMARY

        return summary

    except Exception as e:

        return (
            "Summary generation error: "
            + str(e)
        )
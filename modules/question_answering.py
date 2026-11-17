import ollama


# ============================================================
# LOCAL LLM CONFIGURATION
# ============================================================

MODEL_NAME = "phi3:mini"


# ============================================================
# FALLBACK ANSWER
# ============================================================

FALLBACK_ANSWER = (
    "I could not find the answer in the uploaded document."
)


# ============================================================
# QUESTION ANSWERING FUNCTION
# ============================================================

def generate_answer(
    question,
    retrieved_chunks
):

    # --------------------------------------------------------
    # CHECK RETRIEVED INFORMATION
    # --------------------------------------------------------

    if not retrieved_chunks:

        return FALLBACK_ANSWER


    # --------------------------------------------------------
    # PREPARE DOCUMENT CONTEXT
    # --------------------------------------------------------

    context_parts = []


    for i, chunk in enumerate(
        retrieved_chunks,
        start=1
    ):

        context_parts.append(
            f"[Document Section {i}]\n{chunk}"
        )


    context = "\n\n".join(
        context_parts
    )


    # ========================================================
    # STRICT DOCUMENT-GROUNDED PROMPT
    # ========================================================

    prompt = f"""
You are an educational question-answering assistant.

You must answer the student's question using ONLY the information
contained in the DOCUMENT SECTIONS below.

The document sections come from the student's uploaded educational
material.


============================================================
MOST IMPORTANT RULE
============================================================

DO NOT use outside knowledge.

DO NOT use information from your training knowledge.

DO NOT invent information.

DO NOT guess.

Every important statement in your answer must be supported by
the document sections.


============================================================
ANSWERING RULES
============================================================

1. Answer the student's question directly.

2. Use only information found in the document.

3. Do not add facts that are not present in the document.

4. Do not add examples that are not present in the document.

5. Do not add applications that are not present in the document.

6. Do not add advantages or disadvantages unless the document
   explicitly provides them.

7. Do not add modern or general definitions from outside knowledge.

8. Do not combine unrelated topics simply because they appear
   in the same document.

9. If several document sections are relevant, combine only the
   relevant information.

10. Avoid repeating the same point.

11. Keep the answer concise and educational.

12. Preserve important technical terminology.

13. Correct obvious spelling mistakes in the generated answer.

14. For example:

    Artifics Intelligence
    should be
    Artificial Intelligence

15. Do not change the technical meaning of the document.

16. Do not mention the document sections in the final answer.

17. Do not mention:
    RAG
    FAISS
    Phi-3
    language model
    retrieved chunks
    prompt
    context

18. If the document does not contain enough information to answer
    the question, return exactly:

I could not find the answer in the uploaded document.


============================================================
STUDENT QUESTION
============================================================

{question}


============================================================
DOCUMENT SECTIONS
============================================================

{context}


============================================================
FINAL ANSWER
============================================================

Write ONLY the answer to the student's question.
"""


    # ========================================================
    # CALL PHI-3 MINI
    # ========================================================

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
                "num_predict": 250
            }
        )


        # ----------------------------------------------------
        # EXTRACT RESPONSE
        # ----------------------------------------------------

        answer = response[
            "message"
        ][
            "content"
        ].strip()


        # ----------------------------------------------------
        # EMPTY RESPONSE CHECK
        # ----------------------------------------------------

        if not answer:

            return FALLBACK_ANSWER


        # ----------------------------------------------------
        # REMOVE ACCIDENTAL ANSWER LABELS
        # ----------------------------------------------------

        prefixes = [
            "ANSWER:",
            "Answer:",
            "FINAL ANSWER:",
            "Final Answer:"
        ]


        for prefix in prefixes:

            if answer.startswith(prefix):

                answer = answer[
                    len(prefix):
                ].strip()


        # ----------------------------------------------------
        # COMMON SPELLING CORRECTIONS
        # ----------------------------------------------------

        replacements = {

            "Artifics Intelligence":
                "Artificial Intelligence",

            "artifics intelligence":
                "Artificial Intelligence",

            "Artifical Intelligence":
                "Artificial Intelligence",

            "Artifical intelligence":
                "Artificial Intelligence"
        }


        for wrong, correct in replacements.items():

            answer = answer.replace(
                wrong,
                correct
            )


        # ----------------------------------------------------
        # FINAL CHECK
        # ----------------------------------------------------

        if not answer:

            return FALLBACK_ANSWER


        return answer


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        return (
            f"Error while generating answer: {e}"
        )
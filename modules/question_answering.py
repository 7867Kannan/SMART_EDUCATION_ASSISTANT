import ollama


MODEL_NAME = "phi3:mini"


def generate_answer(question, retrieved_chunks):
    """
    Generate an answer using Phi-3 Mini based only on
    the chunks retrieved from the student's uploaded document.
    """

    if not retrieved_chunks:
        return "I could not find relevant information in the uploaded document."

    context_parts = []

    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_parts.append(
            f"[Context {i}]\n{chunk}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are an educational assistant.

Answer the student's question using ONLY
the information provided in the CONTEXT below.

Do not use outside knowledge.

If the answer cannot be found in the context,
say:

"I could not find the answer in the uploaded document."

Give a clear and simple educational explanation.

Student Question:
{question}

CONTEXT:
{context}

Answer:
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
                "temperature": 0.2,
                "num_predict": 300
            }
        )

        answer = response["message"]["content"]

        return answer.strip()

    except Exception as e:
        return f"Error while generating answer: {e}"
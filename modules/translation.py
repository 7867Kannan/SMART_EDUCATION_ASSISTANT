import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.6-flash"

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL_NAME
    + ":generateContent?key="
    + API_KEY
)


def call_gemini(prompt):

    if not API_KEY:
        return "Gemini API key not found."

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:

        response = requests.post(
            API_URL,
            json=data,
            timeout=60
        )

        if response.status_code != 200:
            return (
                "Gemini API Error: "
                + str(response.status_code)
                + " - "
                + response.text
            )

        result = response.json()

        return result["candidates"][0]["content"]["parts"][0]["text"].strip()

    except Exception as e:

        return "Translation error: " + str(e)


def translate_to_tamil(english_text):

    prompt = f"""
Translate the following educational explanation into natural
Tamil-English bilingual language.

IMPORTANT RULES:

1. Preserve important technical terms in English.
2. Explain their meaning naturally in Tamil.
3. Do not translate technical terms unnecessarily.
4. Do not add information that is not present in the original explanation.
5. Keep the explanation suitable for an engineering student.
6. Use simple Tamil.
7. Give the English technical term followed by a simple Tamil explanation where useful.

English Explanation:

{english_text}

Return only the Tamil-English bilingual explanation.
"""

    return call_gemini(prompt)


def translate_quiz_to_tamil(quiz):

    if not quiz:
        return quiz

    import json

    prompt = f"""
Translate this educational quiz into simple natural Tamil-English
bilingual language.

IMPORTANT RULES:

- Keep the exact number of questions.
- Keep the question types unchanged.
- Keep MCQ option order unchanged.
- Do not change answer values.
- Do not change answer keys.
- Preserve technical terms in English.
- Translate question text naturally.
- Translate explanations naturally.
- Return valid JSON only.

QUIZ:

{json.dumps(quiz, ensure_ascii=False)}

Return ONLY JSON.
"""

    result = call_gemini(prompt)

    try:

        if result.startswith("```"):
            result = result.replace("```json", "")
            result = result.replace("```", "")
            result = result.strip()

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:
            result = result[start:end + 1]

        return json.loads(result)

    except Exception:

        return quiz
import random
import re
import time
import unicodedata
from collections import Counter


# ============================================================
# CONFIGURATION
# ============================================================

TOTAL_QUESTIONS = 10

QUESTION_DISTRIBUTION = {
    "mcq": 4,
    "true_false": 3,
    "fill_blank": 3
}

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were",
    "be", "been", "being", "of", "to", "in", "on",
    "for", "and", "or", "but", "that", "this",
    "these", "those", "with", "by", "from", "as",
    "at", "it", "its", "into", "their", "they",
    "them", "which", "who", "what", "when",
    "where", "why", "how", "can", "could",
    "should", "would", "will", "may", "might",
    "must", "do", "does", "did", "has", "have",
    "had", "not", "than", "then", "also", "more",
    "most", "less", "many", "much", "such",
    "each", "every", "other", "another", "some",
    "any", "all", "both", "only", "very", "often",
    "usually", "generally", "using", "used", "use",
    "based", "following", "shown", "given",
    "example", "examples", "chapter", "unit",
    "lecture", "page", "figure", "table",
    "important", "different", "within", "through",
    "across", "about", "after", "before",
    "between", "during", "over", "under",
    "because", "therefore", "however", "while",
    "information", "there", "being"
}

HEADING_WORDS = {
    "contents", "glossary", "references",
    "bibliography", "acknowledgements",
    "index", "chapter", "lecture",
    "learning", "objectives", "takeaways"
}

DIFFICULTY_LEVELS = {"easy", "medium", "hard"}


# ============================================================
# 1. ANSWER NORMALIZATION
# ============================================================

def normalize_answer(answer):
    """
    Normalize answers without changing their meaning.

    Handles:
    - Uppercase/lowercase differences
    - Extra spaces
    - Unicode normalization
    - Surrounding punctuation
    """

    if answer is None:
        return ""

    answer = unicodedata.normalize("NFKC", str(answer))

    answer = answer.casefold().strip()

    answer = re.sub(r"\s+", " ", answer)

    answer = answer.strip(" \t\n.,;:!?\"'`")

    return answer


def evaluate_answer(question, user_answer):
    """
    Evaluate a student's answer.

    Supports:
    - MCQ letter or option text
    - True/False
    - Fill-in-the-blank
    - Accepted answer variations

    Returns detailed feedback.
    """

    if not isinstance(question, dict):
        return {
            "is_correct": False,
            "correct_answer": "",
            "explanation": "Question data is invalid."
        }

    question_type = question.get("type", "")

    expected = question.get("answer", "")

    normalized_user = normalize_answer(user_answer)

    correct_answer = expected

    if question_type == "mcq":

        options = question.get("options", {})

        correct_answer = options.get(expected, expected)

        accepted = {
            normalize_answer(expected),
            normalize_answer(correct_answer)
        }

        # Accept either option letter or option text.
        if normalized_user in accepted:
            is_correct = True
        else:
            is_correct = False

    elif question_type == "true_false":

        accepted = {normalize_answer(expected)}

        is_correct = normalized_user in accepted

        correct_answer = expected

    elif question_type == "fill_blank":

        accepted = {
            normalize_answer(expected)
        }

        for alternative in question.get(
            "accepted_answers", []
        ):
            accepted.add(normalize_answer(alternative))

        is_correct = normalized_user in accepted

        correct_answer = expected

    else:

        is_correct = False

    explanation = question.get(
        "explanation",
        "Refer to the relevant passage in the uploaded document."
    )

    if is_correct:
        feedback = "Correct! Well done."
    else:
        feedback = (
            f"Incorrect. The correct answer is: "
            f"{correct_answer}."
        )

    return {
        "is_correct": is_correct,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "feedback": feedback,
        "explanation": explanation,
        "source_text": question.get("source_text", "")
    }


# ============================================================
# 2. NORMALIZE DOCUMENT CHUNKS
# ============================================================

def normalize_chunks(chunks):

    texts = []

    if not chunks:
        return texts

    for chunk in chunks:

        if isinstance(chunk, str):
            text = chunk

        elif isinstance(chunk, dict):

            text = (
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("page_content")
                or ""
            )

        else:
            text = str(chunk)

        text = text.replace("\x00", " ")

        text = re.sub(r"\s+", " ", text).strip()

        if len(text) >= 40:
            texts.append(text)

    return texts


# ============================================================
# 3. CLEAN AND FILTER SENTENCES
# ============================================================

def split_sentences(text):

    if not text:
        return []

    text = re.sub(r"\s+", " ", text)

    # Remove common PDF page information.

    text = re.sub(
        r"\b(?:page|pg)\.?\s*\d+\b",
        " ",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\b\d+\s*/\s*\d+\b",
        " ",
        text
    )

    # Remove common publication metadata.

    text = re.sub(
        r"\b(?:reprint|copyright|all rights reserved)"
        r"\b[^.!?]*",
        " ",
        text,
        flags=re.I
    )

    raw_sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    sentences = []

    seen = set()

    for sentence in raw_sentences:

        sentence = sentence.strip(" \t\n-•")

        words = re.findall(
            r"\b[A-Za-z][A-Za-z'-]*\b",
            sentence
        )

        if not 8 <= len(words) <= 35:
            continue

        letters = sum(
            char.isalpha()
            for char in sentence
        )

        if letters < 35:
            continue

        if not sentence.endswith((".", "!", "?")):
            continue

        # Reject sentences dominated by numbers.

        if sum(char.isdigit() for char in sentence) > 12:
            continue

        first_words = {
            word.lower()
            for word in words[:3]
        }

        if first_words & HEADING_WORDS:
            continue

        meaningful_words = [
            word for word in words
            if word.lower() not in STOP_WORDS
        ]

        if len(meaningful_words) < 3:
            continue

        # Reject publication-style metadata.

        if re.search(
            r"\b(?:ISBN|ISSN|DOI|Reprint|Vol\.|Volume)\b",
            sentence,
            re.I
        ):
            continue

        key = normalize_answer(sentence)

        if key not in seen:

            seen.add(key)

            sentences.append(sentence)

    return sentences


# ============================================================
# 4. EXTRACT CANDIDATE TERMS
# ============================================================

def extract_terms(text):

    words = re.findall(
        r"\b[A-Za-z][A-Za-z'-]{3,}\b",
        text
    )

    result = []

    for word in words:

        if word.lower() in STOP_WORDS:
            continue

        result.append(word)

    return result


def get_keyword(sentence):

    terms = extract_terms(sentence)

    if not terms:
        return None

    counts = Counter(
        term.lower()
        for term in terms
    )

    candidates = [
        term
        for term in terms
        if counts[term.lower()] == 1
    ]

    if not candidates:
        return None

    # Prefer meaningful terms.

    candidates.sort(
        key=lambda term: (
            -len(term),
            term.lower()
        )
    )

    return candidates[0]


def hide_term(sentence, term):

    pattern = re.compile(
        r"\b" + re.escape(term) + r"\b",
        flags=re.I
    )

    result, count = pattern.subn(
        "________",
        sentence,
        count=1
    )

    return result if count else None


# ============================================================
# 5. DIFFICULTY CLASSIFICATION
# ============================================================

def classify_difficulty(sentence):

    words = re.findall(
        r"\b[A-Za-z]+\b",
        sentence
    )

    word_count = len(words)

    technical_count = sum(
        len(word) >= 9
        for word in words
    )

    if word_count <= 15 and technical_count <= 2:
        return "easy"

    if word_count <= 25:
        return "medium"

    return "hard"


# ============================================================
# 6. CREATE DISTRACTORS
# ============================================================

def get_distractors(correct_answer, term_pool):

    candidates = []

    seen = {
        normalize_answer(correct_answer)
    }

    for term in term_pool:

        term = term.strip()

        key = normalize_answer(term)

        if len(term) < 4:
            continue

        if key in seen:
            continue

        seen.add(key)

        candidates.append(term)

    # Prefer words of similar length.

    candidates.sort(
        key=lambda term: abs(
            len(term) - len(correct_answer)
        )
    )

    return candidates[:3]


# ============================================================
# 7. SOURCE-BASED EXPLANATIONS
# ============================================================

def create_explanation(sentence, answer):

    return (
        f"The correct answer is '{answer}'. "
        f"According to the uploaded study material: "
        f"{sentence}"
    )


# ============================================================
# 8. CREATE FOUR-OPTION MCQs
# ============================================================

def make_mcq(
    sentence,
    keyword,
    term_pool,
    number,
    difficulty
):

    hidden_sentence = hide_term(
        sentence,
        keyword
    )

    if not hidden_sentence:
        return None

    distractors = get_distractors(
        keyword,
        term_pool
    )

    # Exactly three distractors are required.

    if len(distractors) != 3:
        return None

    options = [
        keyword
    ] + distractors

    random.shuffle(options)

    option_dict = {}

    correct_letter = None

    for index, option in enumerate(options):

        letter = chr(ord("A") + index)

        option_dict[letter] = option

        if normalize_answer(option) == normalize_answer(keyword):
            correct_letter = letter

    if not correct_letter:
        return None

    return {
        "id": f"q{number}",

        "type": "mcq",

        "difficulty": difficulty,

        "question": (
            "Choose the correct answer:\n"
            + hidden_sentence
        ),

        "options": option_dict,

        # Preserve letter-based answer compatibility.
        "answer": correct_letter,

        "correct_answer": keyword,

        "explanation": create_explanation(
            sentence,
            keyword
        ),

        "source_text": sentence
    }


# ============================================================
# 9. TRUE/FALSE QUESTIONS
# ============================================================

def make_true_false(
    sentence,
    number,
    difficulty
):

    return {
        "id": f"q{number}",

        "type": "true_false",

        "difficulty": difficulty,

        "question": (
            "State whether the following statement is "
            "True or False:\n"
            + sentence
        ),

        "options": ["True", "False"],

        "answer": "True",

        "correct_answer": "True",

        "explanation": (
            "This statement is directly supported by "
            "the uploaded study material. "
            + sentence
        ),

        "source_text": sentence
    }


# ============================================================
# 10. FILL-IN-THE-BLANK QUESTIONS
# ============================================================

def make_fill_blank(
    sentence,
    keyword,
    number,
    difficulty
):

    hidden_sentence = hide_term(
        sentence,
        keyword
    )

    if not hidden_sentence:
        return None

    return {
        "id": f"q{number}",

        "type": "fill_blank",

        "difficulty": difficulty,

        "question": (
            "Fill in the missing term:\n"
            + hidden_sentence
        ),

        "answer": keyword,

        "correct_answer": keyword,

        "accepted_answers": [keyword],

        "explanation": create_explanation(
            sentence,
            keyword
        ),

        "source_text": sentence
    }


# ============================================================
# 11. VALIDATE QUESTION STRUCTURE
# ============================================================

def validate_question(question):

    if not isinstance(question, dict):
        return False

    if not question.get("question"):
        return False

    if not question.get("answer"):
        return False

    if not question.get("explanation"):
        return False

    if not question.get("source_text"):
        return False

    question_type = question.get("type")

    if question_type == "mcq":

        options = question.get("options")

        if not isinstance(options, dict):
            return False

        if set(options.keys()) != {
            "A", "B", "C", "D"
        }:
            return False

        if question["answer"] not in options:
            return False

        normalized_options = {
            normalize_answer(value)
            for value in options.values()
        }

        if len(normalized_options) != 4:
            return False

    elif question_type == "true_false":

        if question["answer"] not in {
            "True", "False"
        }:
            return False

        if question.get("options") != [
            "True", "False"
        ]:
            return False

    elif question_type == "fill_blank":

        if "________" not in question["question"]:
            return False

    else:
        return False

    return True


# ============================================================
# 12. MAIN QUIZ GENERATOR
# ============================================================

def generate_quiz(
    chunks,
    difficulty="medium",
    total_questions=TOTAL_QUESTIONS
):

    start_time = time.time()

    difficulty = str(difficulty).lower().strip()

    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = "medium"

    try:
        total_questions = int(total_questions)
    except (TypeError, ValueError):
        total_questions = TOTAL_QUESTIONS

    total_questions = max(
        1,
        min(total_questions, 30)
    )

    source_chunks = normalize_chunks(chunks)

    if not source_chunks:
        return {"questions": []}

    # --------------------------------------------------------
    # Extract complete sentences.
    # --------------------------------------------------------

    sentences = []

    for chunk in source_chunks:

        sentences.extend(
            split_sentences(chunk)
        )

    # Remove duplicate sentences.

    unique_sentences = []

    seen = set()

    for sentence in sentences:

        key = normalize_answer(sentence)

        if key not in seen:

            seen.add(key)

            unique_sentences.append(sentence)

    if not unique_sentences:

        print(
            "Quiz: no suitable complete sentences found."
        )

        return {"questions": []}

    # --------------------------------------------------------
    # Difficulty filtering.
    # --------------------------------------------------------

    classified = []

    for sentence in unique_sentences:

        level = classify_difficulty(sentence)

        classified.append(
            (sentence, level)
        )

    selected = [
        sentence
        for sentence, level in classified
        if level == difficulty
    ]

    # Fallback if the document does not contain enough
    # sentences for the requested difficulty.

    if len(selected) < total_questions:

        selected = unique_sentences.copy()

    random.shuffle(selected)

    # --------------------------------------------------------
    # Build term pool.
    # --------------------------------------------------------

    term_pool = []

    for sentence in unique_sentences:

        term_pool.extend(
            extract_terms(sentence)
        )

    unique_terms = list({
        normalize_answer(term): term
        for term in term_pool
    }.values())

    # --------------------------------------------------------
    # Determine question distribution.
    # --------------------------------------------------------

    mcq_count = round(total_questions * 0.4)

    tf_count = round(total_questions * 0.3)

    fill_count = total_questions - mcq_count - tf_count

    questions = []

    used_sentences = set()

    used_keywords = set()

    # --------------------------------------------------------
    # Generate MCQs.
    # --------------------------------------------------------

    for sentence in selected:

        if sum(
            q["type"] == "mcq"
            for q in questions
        ) >= mcq_count:
            break

        if sentence.lower() in used_sentences:
            continue

        keyword = get_keyword(sentence)

        if not keyword:
            continue

        if keyword.lower() in used_keywords:
            continue

        question = make_mcq(
            sentence,
            keyword,
            unique_terms,
            len(questions) + 1,
            difficulty
        )

        if question and validate_question(question):

            questions.append(question)

            used_sentences.add(sentence.lower())

            used_keywords.add(keyword.lower())

    # --------------------------------------------------------
    # Generate True/False questions.
    # --------------------------------------------------------

    for sentence in selected:

        if sum(
            q["type"] == "true_false"
            for q in questions
        ) >= tf_count:
            break

        if sentence.lower() in used_sentences:
            continue

        question = make_true_false(
            sentence,
            len(questions) + 1,
            difficulty
        )

        if validate_question(question):

            questions.append(question)

            used_sentences.add(sentence.lower())

    # --------------------------------------------------------
    # Generate Fill-in-the-blank questions.
    # --------------------------------------------------------

    for sentence in selected:

        if sum(
            q["type"] == "fill_blank"
            for q in questions
        ) >= fill_count:
            break

        if sentence.lower() in used_sentences:
            continue

        keyword = get_keyword(sentence)

        if not keyword:
            continue

        if keyword.lower() in used_keywords:
            continue

        question = make_fill_blank(
            sentence,
            keyword,
            len(questions) + 1,
            difficulty
        )

        if question and validate_question(question):

            questions.append(question)

            used_sentences.add(sentence.lower())

            used_keywords.add(keyword.lower())

    # --------------------------------------------------------
    # Fill remaining slots if one category lacks candidates.
    # --------------------------------------------------------

    for sentence in selected:

        if len(questions) >= total_questions:
            break

        if sentence.lower() in used_sentences:
            continue

        keyword = get_keyword(sentence)

        if not keyword:
            continue

        if keyword.lower() in used_keywords:
            continue

        question = make_fill_blank(
            sentence,
            keyword,
            len(questions) + 1,
            difficulty
        )

        if question and validate_question(question):

            questions.append(question)

            used_sentences.add(sentence.lower())

            used_keywords.add(keyword.lower())

    # --------------------------------------------------------
    # Final validation and numbering.
    # --------------------------------------------------------

    final_questions = []

    for index, question in enumerate(
        questions[:total_questions],
        start=1
    ):

        if not validate_question(question):
            continue

        question["id"] = f"q{index}"

        final_questions.append(question)

    elapsed = time.time() - start_time

    print(
        f"Quiz generated in {elapsed:.2f} seconds. "
        f"Questions: {len(final_questions)}. "
        f"Difficulty: {difficulty}."
    )

    return {
        "questions": final_questions,
        "difficulty": difficulty,
        "total_questions": len(final_questions)
    }
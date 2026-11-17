import os
import json
import hashlib
import logging
from pathlib import Path
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

import numpy as np
import faiss

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel, Field

from modules.document_processing import extract_text
from modules.preprocessing import clean_text, create_chunks
from modules.embedding_generator import generate_embeddings, get_model
from modules.vector_store import (
    create_faiss_index,
    save_faiss_index,
    load_faiss_index,
)
from modules.retriever import retrieve_chunks
from modules.question_answering import generate_answer
from modules.summarization import generate_summary
from modules.translation import translate_to_tamil
from modules.quiz_generation import generate_quiz


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Smart Education Assistant",
    description=(
        "An educational assistant using RAG, "
        "semantic retrieval, local LLMs, and Tamil translation."
    ),
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GLOBAL STATE
# ============================================================

current_document = None
current_chunks = []
current_index = None

last_answer = ""
last_summary = ""

last_quiz = {
    "questions": []
}


# ============================================================
# REQUEST MODELS
# ============================================================

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    translate: bool = True


class QuizAnswerSubmission(BaseModel):
    answers: list[dict[str, Any]] = Field(default_factory=list)
    score: int = 0
    total: int = 0
    percentage: float = 0.0


# ============================================================
# GENERAL HELPER FUNCTIONS
# ============================================================

def get_embedding_model():
    """
    Return the embedding model used by the existing project.
    """
    try:
        return get_model()

    except Exception as exc:
        logger.exception("Could not load embedding model")

        raise HTTPException(
            status_code=500,
            detail=f"Embedding model error: {str(exc)}",
        )


def get_chunk_text(chunk):
    """
    Support chunks represented as strings or dictionaries.
    """
    if isinstance(chunk, str):
        return chunk

    if isinstance(chunk, dict):
        for key in ("text", "content", "page_content", "chunk"):
            value = chunk.get(key)

            if isinstance(value, str):
                return value

    return str(chunk)


def normalize_text(value):
    """
    Normalize text for answer comparison.
    """
    if value is None:
        return ""

    value = str(value).strip().lower()

    for character in (
        "\\", ".", ",", ":", ";", "!", "?", "'", '"', "(", ")"
    ):
        value = value.replace(character, "")

    return " ".join(value.split())


def get_option_text(options, answer):
    """
    Convert an option key such as A or B into its option text.
    Supports dictionary and list formats.
    """
    if answer is None:
        return ""

    answer_text = str(answer).strip()

    if isinstance(options, dict):
        for key, value in options.items():

            if str(key).strip().lower() == answer_text.lower():

                if isinstance(value, dict):
                    return str(
                        value.get("text", value.get("value", value))
                    )

                return str(value)

        return answer_text

    if isinstance(options, list):

        for index, option in enumerate(options):

            if isinstance(option, dict):

                key = option.get(
                    "key",
                    option.get("label", option.get("id", index))
                )

                text = option.get(
                    "text",
                    option.get("value", option.get("option", ""))
                )

                if str(key).strip().lower() == answer_text.lower():
                    return str(text)

                if str(index).strip() == answer_text:
                    return str(text)

            else:

                if str(index).strip() == answer_text:
                    return str(option)

        return answer_text

    return answer_text


def get_question_answer(question):
    """
    Retrieve the expected answer from different common quiz formats.
    """
    if not isinstance(question, dict):
        return ""

    for key in (
        "answer",
        "correct_answer",
        "correctAnswer",
        "correct_option",
        "correctOption",
        "answer_key",
    ):

        value = question.get(key)

        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def get_question_options(question):
    """
    Retrieve options from a quiz question.
    """
    if not isinstance(question, dict):
        return []

    for key in ("options", "choices", "answers"):

        value = question.get(key)

        if isinstance(value, (list, dict)):
            return value

    return []


def is_answer_correct(question, student_answer):
    """
    Compare the student's answer with the expected answer.
    """
    if not isinstance(question, dict):
        return False

    if student_answer is None:
        return False

    student_text = str(student_answer).strip()

    if not student_text:
        return False

    correct_answer = get_question_answer(question)

    if not correct_answer:
        return False

    options = get_question_options(question)

    student_option_text = get_option_text(
        options,
        student_text
    )

    correct_option_text = get_option_text(
        options,
        correct_answer
    )

    student_normalized = normalize_text(student_text)
    correct_normalized = normalize_text(correct_answer)

    student_option_normalized = normalize_text(
        student_option_text
    )

    correct_option_normalized = normalize_text(
        correct_option_text
    )

    possible_matches = {
        correct_normalized,
        correct_option_normalized,
    }

    return (
        student_normalized in possible_matches
        or student_option_normalized in possible_matches
    )


def get_student_answer_text(question, student_answer):
    """
    Convert the submitted answer key into readable answer text.
    """
    if student_answer is None:
        return "Not answered"

    student_answer = str(student_answer).strip()

    if not student_answer:
        return "Not answered"

    options = get_question_options(question)

    option_text = get_option_text(
        options,
        student_answer
    )

    return option_text or student_answer


def get_correct_answer_text(question):
    """
    Convert the expected answer key into readable answer text.
    """
    answer = get_question_answer(question)

    if not answer:
        return "Not available"

    options = get_question_options(question)

    option_text = get_option_text(
        options,
        answer
    )

    return option_text or answer


def safe_pdf_text(value):
    """
    Escape text before placing it inside a ReportLab Paragraph.
    """
    if value is None:
        return ""

    return escape(str(value)).replace("\n", "<br/>")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Smart Education Assistant",
        "document_loaded": current_document is not None,
        "chunks": len(current_chunks),
    }

# ============================================================
# PROCESS PDF
# ============================================================

@app.post("/process-pdf")
async def process_pdf(file: UploadFile = File(...)):

    global current_document
    global current_chunks
    global current_index
    global last_answer
    global last_summary
    global last_quiz

    # Validate uploaded file
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a PDF file.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    try:
        # Read uploaded PDF
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty.",
            )

        # Generate unique document hash
        file_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        chunks_file = DATA_DIR / f"{file_hash}_chunks.json"
        index_file = DATA_DIR / f"{file_hash}.faiss"

        # ----------------------------------------------------
        # LOAD CACHED DOCUMENT
        # ----------------------------------------------------

        if chunks_file.exists() and index_file.exists():

            try:
                with open(
                    chunks_file,
                    "r",
                    encoding="utf-8",
                ) as file_handle:

                    cached_chunks = json.load(file_handle)

                cached_index = load_faiss_index(
                    str(index_file)
                )

                if cached_chunks and cached_index is not None:

                    current_chunks = cached_chunks
                    current_index = cached_index
                    current_document = file.filename

                    last_answer = ""
                    last_summary = ""
                    last_quiz = {"questions": []}

                    return {
                        "success": True,
                        "message": "Document loaded from cache.",
                        "document_name": current_document,
                        "cached": True,
                        "chunks": len(current_chunks),
                    }

            except Exception:
                logger.exception(
                    "Cached document could not be loaded"
                )

        # ----------------------------------------------------
        # EXTRACT PDF TEXT
        # ----------------------------------------------------

        import tempfile

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False,
            ) as temporary_file:

                temporary_file.write(file_bytes)
                temporary_path = temporary_file.name

            extracted_text = extract_text(temporary_path)

        finally:

            if temporary_path and os.path.exists(temporary_path):

                try:
                    os.remove(temporary_path)

                except OSError:
                    logger.warning(
                        "Could not remove temporary PDF file"
                    )

        if not extracted_text or not str(extracted_text).strip():

            raise HTTPException(
                status_code=400,
                detail=(
                    "No readable text was found in the PDF. "
                    "The document may be scanned or image-based."
                ),
            )

        # ----------------------------------------------------
        # CLEAN TEXT
        # ----------------------------------------------------

        cleaned_text = clean_text(extracted_text)

        if not cleaned_text or not str(cleaned_text).strip():

            raise HTTPException(
                status_code=400,
                detail="The extracted document text is empty.",
            )

        # ----------------------------------------------------
        # CREATE CHUNKS
        # ----------------------------------------------------

        new_chunks = create_chunks(
            cleaned_text,
            chunk_size=400,
            overlap=80,
        )

        if not new_chunks:

            raise HTTPException(
                status_code=400,
                detail="Could not create chunks from the PDF.",
            )

        # ----------------------------------------------------
        # GENERATE EMBEDDINGS
        # ----------------------------------------------------

        embeddings = generate_embeddings(new_chunks)

        if embeddings is None:

            raise HTTPException(
                status_code=500,
                detail="Embedding generation returned no result.",
            )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        if embeddings.ndim != 2 or embeddings.shape[0] == 0:

            raise HTTPException(
                status_code=500,
                detail="Generated embeddings have an invalid shape.",
            )

        # ----------------------------------------------------
        # CREATE FAISS INDEX
        # ----------------------------------------------------

        new_index = create_faiss_index(embeddings)

        if new_index is None:

            raise HTTPException(
                status_code=500,
                detail="Could not create the FAISS index.",
            )

        # ----------------------------------------------------
        # SAVE CACHE
        # ----------------------------------------------------

        with open(
            chunks_file,
            "w",
            encoding="utf-8",
        ) as file_handle:

            json.dump(
                new_chunks,
                file_handle,
                ensure_ascii=False,
                indent=2,
            )

        save_faiss_index(
            new_index,
            str(index_file),
        )

        # ----------------------------------------------------
        # UPDATE GLOBAL STATE
        # ----------------------------------------------------

        current_document = file.filename
        current_chunks = new_chunks
        current_index = new_index

        last_answer = ""
        last_summary = ""
        last_quiz = {"questions": []}

        logger.info(
            "Processed PDF %s with %s chunks",
            current_document,
            len(current_chunks),
        )

        return {
            "success": True,
            "message": "PDF processed successfully.",
            "document_name": current_document,
            "cached": False,
            "chunks": len(current_chunks),
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("PDF processing failed")

        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(exc)}",
        )


# ============================================================
# ASK AI
# ============================================================

@app.post("/ask")
async def ask_question(request: QuestionRequest):

    global last_answer

    # Check whether a document has been processed
    if not current_chunks or current_index is None:

        raise HTTPException(
            status_code=400,
            detail="Please upload and process a PDF first.",
        )

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    try:
        # ----------------------------------------------------
        # LOAD EMBEDDING MODEL
        # ----------------------------------------------------

        model = get_embedding_model()

        # ----------------------------------------------------
        # RETRIEVE RELEVANT DOCUMENT CHUNKS
        # ----------------------------------------------------

        retrieved_chunks, retrieved_scores = retrieve_chunks(
            question,
            model,
            current_index,
            current_chunks,
            top_k=3,
            candidate_k=8,
            min_similarity=0.45,
        )

        if not retrieved_chunks:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No relevant information was found "
                    "in the uploaded document."
                ),
            )

        # ----------------------------------------------------
        # GENERATE ENGLISH ANSWER
        # ----------------------------------------------------

        english_answer = generate_answer(
            question,
            retrieved_chunks,
        )

        if not english_answer:

            raise HTTPException(
                status_code=500,
                detail=(
                    "The answer generation module "
                    "returned an empty answer."
                ),
            )

        # ----------------------------------------------------
        # TRANSLATE ANSWER INTO TAMIL
        # ----------------------------------------------------

        final_answer = str(english_answer)
        tamil_answer = ""

        if request.translate:

            try:
                translated = translate_to_tamil(
                    str(english_answer)
                )

                if translated:
                    tamil_answer = str(translated)
                    final_answer = tamil_answer

            except Exception:

                logger.exception("Tamil translation failed")

                # Preserve English answer if translation fails.
                tamil_answer = ""

        # ----------------------------------------------------
        # SAVE LAST ANSWER
        # ----------------------------------------------------

        last_answer = final_answer

        # ----------------------------------------------------
        # API RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,
            "question": question,
            "answer": final_answer,
            "english_answer": str(english_answer),
            "tamil_answer": tamil_answer,
            "retrieved_sections": len(retrieved_chunks),
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("Question answering failed")

        raise HTTPException(
            status_code=500,
            detail=f"Could not answer the question: {str(exc)}",
        )
    # ============================================================
# SUMMARY GENERATION
# ============================================================

@app.post("/summary")
async def create_summary():

    global last_summary

    # Check whether a document has been uploaded
    if not current_chunks:

        raise HTTPException(
            status_code=400,
            detail="Please upload and process a PDF first.",
        )

    try:
        # ----------------------------------------------------
        # GENERATE ENGLISH SUMMARY
        # ----------------------------------------------------

        english_summary = generate_summary(
            current_chunks
        )

        if not english_summary:

            raise HTTPException(
                status_code=500,
                detail=(
                    "The summarization module "
                    "returned an empty summary."
                ),
            )

        # ----------------------------------------------------
        # TRANSLATE SUMMARY INTO TAMIL
        # ----------------------------------------------------

        tamil_summary = ""

        try:
            translated = translate_to_tamil(
                str(english_summary)
            )

            if translated:
                tamil_summary = str(translated)

        except Exception:

            logger.exception("Summary translation failed")

        # ----------------------------------------------------
        # SAVE SUMMARY
        # ----------------------------------------------------

        last_summary = (
            tamil_summary
            if tamil_summary
            else str(english_summary)
        )

        # ----------------------------------------------------
        # API RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,
            "summary": last_summary,
            "english_summary": str(english_summary),
            "tamil_summary": tamil_summary,
            "document_name": current_document,
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("Summary generation failed")

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate summary: {str(exc)}",
        )


# ============================================================
# QUIZ GENERATION
# ============================================================

@app.post("/quiz")
async def create_quiz():

    global last_quiz

    # Check whether a document has been uploaded
    if not current_chunks:

        raise HTTPException(
            status_code=400,
            detail="Please upload and process a PDF first.",
        )

    try:
        # ----------------------------------------------------
        # GENERATE QUIZ QUESTIONS
        # ----------------------------------------------------

        quiz = generate_quiz(
            current_chunks
        )

        # Handle list-based quiz output
        if isinstance(quiz, list):
            quiz = {"questions": quiz}

        # Validate quiz output
        if not isinstance(quiz, dict):
            quiz = {"questions": []}

        questions = quiz.get("questions", [])

        if not isinstance(questions, list):
            questions = []

        if not questions:

            raise HTTPException(
                status_code=500,
                detail=(
                    "No quiz questions could be generated. "
                    "Please try again."
                ),
            )

        # ----------------------------------------------------
        # SAVE GENERATED QUIZ
        # ----------------------------------------------------

        last_quiz = {
            **quiz,
            "questions": questions,
        }

        # ----------------------------------------------------
        # API RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,
            "message": "Quiz generated successfully.",
            "quiz": last_quiz,
            "questions": questions,
            "total": len(questions),
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("Quiz generation failed")

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate quiz: {str(exc)}",
        )


# ============================================================
# DOWNLOAD ANSWER
# ============================================================

@app.get("/download/answer")
async def download_answer():

    if not last_answer:

        raise HTTPException(
            status_code=404,
            detail="No answer is available to download.",
        )

    return PlainTextResponse(
        content=last_answer,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="answer.txt"'
        },
    )


# ============================================================
# DOWNLOAD SUMMARY
# ============================================================

@app.get("/download/summary")
async def download_summary():

    if not last_summary:

        raise HTTPException(
            status_code=404,
            detail="No summary is available to download.",
        )

    return PlainTextResponse(
        content=last_summary,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="summary.txt"'
        },
    )
# ============================================================
# DOWNLOAD QUIZ ANSWER REVIEW AS PDF
# ============================================================

@app.post("/download/quiz")
async def download_quiz(data: QuizAnswerSubmission):
    """
    Generate a PDF report containing:
    - Quiz score
    - Student's submitted answers
    - Correct answers
    - Correct/incorrect status
    - Explanations, when available
    """

    questions = last_quiz.get("questions", [])

    if not questions:
        raise HTTPException(
            status_code=404,
            detail="No quiz is available. Generate a quiz first.",
        )

    if not data.answers:
        raise HTTPException(
            status_code=400,
            detail="No submitted answers were received.",
        )

    # --------------------------------------------------------
    # MAP SUBMITTED ANSWERS TO QUESTIONS
    # --------------------------------------------------------

    submitted_answers = {}

    for item in data.answers:

        if not isinstance(item, dict):
            continue

        question_index = item.get("question_index")

        if question_index is not None:
            try:
                submitted_answers[int(question_index)] = item.get(
                    "student_answer",
                    item.get("answer", ""),
                )
                continue

            except (ValueError, TypeError):
                pass

        question_id = str(item.get("question_id", ""))

        if question_id.startswith("q"):
            try:
                index = int(question_id[1:]) - 1

                submitted_answers[index] = item.get(
                    "student_answer",
                    item.get("answer", ""),
                )

            except (ValueError, TypeError):
                pass

    # --------------------------------------------------------
    # CALCULATE SCORE ON THE SERVER
    # --------------------------------------------------------

    correct_count = 0
    report_items = []

    for index, question in enumerate(questions):

        if not isinstance(question, dict):
            question = {
                "question": str(question)
            }

        student_answer = submitted_answers.get(
            index,
            "",
        )

        correct_answer = get_correct_answer_text(
            question
        )

        student_answer_text = get_student_answer_text(
            question,
            student_answer,
        )

        correct = is_answer_correct(
            question,
            student_answer,
        )

        if correct:
            correct_count += 1

        report_items.append({
            "number": index + 1,
            "question": question.get(
                "question",
                question.get("text", "Question"),
            ),
            "student_answer": student_answer_text,
            "correct_answer": correct_answer,
            "correct": correct,
            "explanation": question.get(
                "explanation",
                question.get("reason", ""),
            ),
        })

    total_questions = len(questions)

    percentage = (
        round(correct_count / total_questions * 100, 2)
        if total_questions
        else 0
    )

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            KeepTogether,
        )

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="Quiz Answer Review",
            author="Smart Education Assistant",
        )

        styles = getSampleStyleSheet()

        # ----------------------------------------------------
        # PDF STYLES
        # ----------------------------------------------------

        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                alignment=TA_CENTER,
                fontSize=19,
                leading=24,
                spaceAfter=10,
            )
        )

        styles.add(
            ParagraphStyle(
                name="QuestionHeading",
                parent=styles["Heading2"],
                fontSize=11,
                leading=15,
                spaceBefore=8,
                spaceAfter=6,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SmallText",
                parent=styles["BodyText"],
                fontSize=9,
                leading=13,
            )
        )

        styles.add(
            ParagraphStyle(
                name="StatusText",
                parent=styles["BodyText"],
                fontSize=10,
                leading=14,
            )
        )

        story = []

        # ----------------------------------------------------
        # PDF TITLE
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Quiz Answer Review",
                styles["ReportTitle"],
            )
        )

        # Document name
        if current_document:
            story.append(
                Paragraph(
                    "<b>Document:</b> "
                    + safe_pdf_text(current_document),
                    styles["BodyText"],
                )
            )

        # Generation date
        story.append(
            Paragraph(
                "<b>Generated:</b> "
                + safe_pdf_text(
                    __import__("datetime").datetime.now().strftime(
                        "%d-%m-%Y %H:%M"
                    )
                ),
                styles["BodyText"],
            )
        )

        story.append(Spacer(1, 12))

        # ----------------------------------------------------
        # SCORE TABLE
        # ----------------------------------------------------

        score_table = Table(
            [
                ["Correct Answers", "Total Questions", "Score"],
                [
                    str(correct_count),
                    str(total_questions),
                    f"{percentage:.2f}%",
                ],
            ],
            colWidths=[
                52 * mm,
                52 * mm,
                52 * mm,
            ],
        )

        score_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#243B53"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ])
        )

        story.append(score_table)
        story.append(Spacer(1, 18))

        # ----------------------------------------------------
        # DETAILED ANSWERS
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Detailed Answers",
                styles["Heading1"],
            )
        )

        for item in report_items:

            status = (
                "CORRECT"
                if item["correct"]
                else "INCORRECT"
            )

            question_block = []

            question_block.append(
                Paragraph(
                    f"Question {item['number']}: "
                    + safe_pdf_text(item["question"]),
                    styles["QuestionHeading"],
                )
            )

            details = [
                [
                    Paragraph(
                        "<b>Your Answer</b>",
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe_pdf_text(item["student_answer"]),
                        styles["SmallText"],
                    ),
                ],
                [
                    Paragraph(
                        "<b>Correct Answer</b>",
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe_pdf_text(item["correct_answer"]),
                        styles["SmallText"],
                    ),
                ],
                [
                    Paragraph(
                        "<b>Result</b>",
                        styles["SmallText"],
                    ),
                    Paragraph(
                        status,
                        styles["StatusText"],
                    ),
                ],
            ]

            # Add explanation when available
            if item["explanation"]:
                details.append([
                    Paragraph(
                        "<b>Explanation</b>",
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe_pdf_text(item["explanation"]),
                        styles["SmallText"],
                    ),
                ])

            details_table = Table(
                details,
                colWidths=[
                    38 * mm,
                    118 * mm,
                ],
            )

            result_color = (
                colors.HexColor("#DCFCE7")
                if item["correct"]
                else colors.HexColor("#FEE2E2")
            )

            details_table.setStyle(
                TableStyle([
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.HexColor("#F1F5F9"),
                    ),
                    (
                        "BACKGROUND",
                        (1, 2),
                        (1, 2),
                        result_color,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ])
            )

            question_block.append(details_table)
            question_block.append(Spacer(1, 12))

            story.append(
                KeepTogether(question_block)
            )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        def add_page_number(canvas, doc):

            canvas.saveState()

            canvas.setFont("Helvetica", 8)

            canvas.setFillColor(
                colors.HexColor("#64748B")
            )

            canvas.drawCentredString(
                A4[0] / 2,
                10 * mm,
                f"Smart Education Assistant | Page {doc.page}",
            )

            canvas.restoreState()

        # ----------------------------------------------------
        # GENERATE PDF
        # ----------------------------------------------------

        document.build(
            story,
            onFirstPage=add_page_number,
            onLaterPages=add_page_number,
        )

        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="practice_quiz_answer_review.pdf"'
                )
            },
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("Quiz PDF generation failed")

        raise HTTPException(
            status_code=500,
            detail=f"Could not generate quiz review PDF: {str(exc)}",
        )


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():

    return {
        "success": True,
        "message": "Smart Education Assistant API is running.",
        "health_endpoint": "/health",
        "documentation": "/docs",
    }

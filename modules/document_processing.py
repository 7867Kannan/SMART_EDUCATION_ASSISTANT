import pdfplumber
import PyPDF2


def extract_text_pdfplumber(pdf_path):
    """
    Extract text from PDF using pdfplumber.
    """

    text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for page_number, page in enumerate(pdf.pages):

                page_text = page.extract_text()

                if page_text:
                    text += f"\n----- Page {page_number + 1} -----\n"
                    text += page_text

    except Exception as e:
        print("pdfplumber error:", e)

    return text


def extract_text_pypdf2(pdf_path):
    """
    Extract text from PDF using PyPDF2.
    """

    text = ""

    try:
        with open(pdf_path, "rb") as file:

            reader = PyPDF2.PdfReader(file)

            for page_number, page in enumerate(reader.pages):

                page_text = page.extract_text()

                if page_text:
                    text += f"\n----- Page {page_number + 1} -----\n"
                    text += page_text

    except Exception as e:
        print("PyPDF2 error:", e)

    return text


def extract_text(pdf_path):
    """
    Try pdfplumber first.
    If no text is extracted, use PyPDF2.
    """

    text = extract_text_pdfplumber(pdf_path)

    if not text.strip():

        text = extract_text_pypdf2(pdf_path)

    return text
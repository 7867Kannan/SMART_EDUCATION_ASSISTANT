import os
import streamlit as st

from modules.document_processing import extract_text
from modules.preprocessing import clean_text, create_chunks

from modules.embedding_generator import (
    generate_embeddings,
    get_model
)

from modules.vector_store import (
    create_faiss_index,
    save_faiss_index,
    load_faiss_index
)

from modules.retriever import retrieve_chunks
from modules.question_answering import generate_answer

from modules.metadata import (
    save_chunks,
    load_chunks
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart Education Assistant",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# APPLICATION TITLE
# ============================================================

st.title("📚 Smart Education Assistant")

st.write(
    "Upload your educational PDF and ask questions "
    "from its content."
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

os.makedirs(
    "data/uploaded_pdfs",
    exist_ok=True
)

os.makedirs(
    "data/faiss_index",
    exist_ok=True
)

os.makedirs(
    "data/metadata",
    exist_ok=True
)


# ============================================================
# PDF UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload your PDF",
    type=["pdf"]
)


# ============================================================
# PROCESS UPLOADED PDF
# ============================================================

if uploaded_file:

    # --------------------------------------------------------
    # SAVE PDF
    # --------------------------------------------------------

    file_path = os.path.join(
        "data",
        "uploaded_pdfs",
        uploaded_file.name
    )

    with open(file_path, "wb") as file:
        file.write(
            uploaded_file.getbuffer()
        )

    st.success(
        "PDF uploaded successfully."
    )


    # --------------------------------------------------------
    # CREATE FILE NAME
    # --------------------------------------------------------

    base_name = os.path.splitext(
        uploaded_file.name
    )[0]


    # --------------------------------------------------------
    # INDEX VERSION
    # --------------------------------------------------------
    #
    # We are using V2 because we changed:
    #
    # 1. Chunk size
    # 2. Chunk overlap
    # 3. Embedding normalization
    # 4. FAISS similarity method
    #
    # Therefore the old FAISS index must not be used.
    # --------------------------------------------------------

    INDEX_VERSION = "v2"


    index_path = os.path.join(
        "data",
        "faiss_index",
        f"{base_name}_{INDEX_VERSION}.faiss"
    )


    chunks_path = os.path.join(
        "data",
        "metadata",
        f"{base_name}_{INDEX_VERSION}.pkl"
    )


    # ========================================================
    # LOAD EXISTING INDEX OR PROCESS PDF
    # ========================================================

    if (
        os.path.exists(index_path)
        and os.path.exists(chunks_path)
    ):

        # ----------------------------------------------------
        # LOAD SAVED DATA
        # ----------------------------------------------------

        st.info(
            "⚡ This PDF was already processed. "
            "Loading improved FAISS data..."
        )


        index = load_faiss_index(
            index_path
        )


        chunks = load_chunks(
            chunks_path
        )


        # ----------------------------------------------------
        # SAFETY CHECK
        # ----------------------------------------------------

        if (
            index is None
            or chunks is None
        ):

            st.error(
                "Saved FAISS data could not be loaded. "
                "Please rebuild the document index."
            )

            st.stop()


        st.success(
            "Improved FAISS index loaded successfully."
        )


    else:

        # ====================================================
        # NEW PDF PROCESSING
        # ====================================================

        st.info(
            "🔄 Processing PDF using improved "
            "retrieval settings..."
        )


        # ----------------------------------------------------
        # STEP 1: EXTRACT TEXT
        # ----------------------------------------------------

        with st.spinner(
            "Extracting text from PDF..."
        ):

            extracted_text = extract_text(
                file_path
            )


        # ----------------------------------------------------
        # CHECK TEXT
        # ----------------------------------------------------

        if not extracted_text.strip():

            st.error(
                "No readable text was found in this PDF."
            )

            st.stop()


        # ----------------------------------------------------
        # STEP 2: CLEAN TEXT
        # ----------------------------------------------------

        with st.spinner(
            "Cleaning extracted text..."
        ):

            cleaned_text = clean_text(
                extracted_text
            )


        # ----------------------------------------------------
        # STEP 3: CREATE OVERLAPPING CHUNKS
        # ----------------------------------------------------

        with st.spinner(
            "Creating overlapping text chunks..."
        ):

            chunks = create_chunks(
                cleaned_text,
                chunk_size=400,
                overlap=80
            )


        st.write(
            f"📄 Created {len(chunks)} overlapping chunks."
        )


        # ----------------------------------------------------
        # STEP 4: GENERATE NORMALIZED EMBEDDINGS
        # ----------------------------------------------------

        with st.spinner(
            "Generating normalized embeddings..."
        ):

            embeddings = generate_embeddings(
                chunks
            )


        # ----------------------------------------------------
        # STEP 5: CREATE FAISS INDEX
        # ----------------------------------------------------

        with st.spinner(
            "Creating FAISS semantic search index..."
        ):

            index = create_faiss_index(
                embeddings
            )


        # ----------------------------------------------------
        # STEP 6: SAVE FAISS INDEX
        # ----------------------------------------------------

        save_faiss_index(
            index,
            index_path
        )


        # ----------------------------------------------------
        # STEP 7: SAVE CHUNKS
        # ----------------------------------------------------

        save_chunks(
            chunks,
            chunks_path
        )


        st.success(
            "✅ Improved FAISS index created and saved."
        )


    # ========================================================
    # DOCUMENT INFORMATION
    # ========================================================

    st.subheader(
        "📊 Document Information"
    )


    col1, col2, col3 = st.columns(3)


    # --------------------------------------------------------
    # NUMBER OF CHUNKS
    # --------------------------------------------------------

    with col1:

        st.metric(
            "Text Chunks",
            len(chunks)
        )


    # --------------------------------------------------------
    # EMBEDDING DIMENSION
    # --------------------------------------------------------

    with col2:

        st.metric(
            "Embedding Dimension",
            384
        )


    # --------------------------------------------------------
    # NUMBER OF FAISS VECTORS
    # --------------------------------------------------------

    with col3:

        st.metric(
            "FAISS Vectors",
            len(chunks)
        )


    # ========================================================
    # QUESTION SECTION
    # ========================================================

    st.subheader(
        "💬 Ask Questions"
    )


    query = st.text_input(
        "Enter your question"
    )


    # ========================================================
    # RETRIEVAL
    # ========================================================

    if query:

        with st.spinner(
            "Searching your document..."
        ):

            # ------------------------------------------------
            # LOAD EMBEDDING MODEL
            # ------------------------------------------------

            model = get_model()


            # ------------------------------------------------
            # RETRIEVE RELEVANT CHUNKS
            # ------------------------------------------------

            results, scores = retrieve_chunks(
                query,
                model,
                index,
                chunks,
                top_k=3,
                candidate_k=8
            )


        # ====================================================
        # DISPLAY RESULTS
        # ====================================================

        st.subheader(
            "🔎 Retrieved Information"
        )


        if not results:

            st.warning(
                "No relevant information was found "
                "in the uploaded document."
            )


        else:

            for i, result in enumerate(
                results
            ):

                with st.expander(
                    f"Result {i + 1}"
                ):

                    st.write(
                        result
                    )


                    st.caption(
                        f"Cosine Similarity: "
                        f"{scores[i]:.4f}"
                    )
                # ====================================================
        # AI QUESTION ANSWER
        # ====================================================

        if results:

            st.subheader(
                "🤖 AI Answer"
            )

            with st.spinner(
                "Generating answer using Phi-3 Mini..."
            ):

                answer = generate_answer(
                    query,
                    results
                )

            st.write(answer)
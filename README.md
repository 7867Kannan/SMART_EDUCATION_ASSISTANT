# ECHO BRIDGE
## Bridging Knowledge: A Smart Education Assistant for Regional Language Learning

An AI-powered educational assistant that helps students understand English educational materials through document-based question answering, Tamil translation, chapter summarization, and automatic quiz generation.

---

## 📌 Project Overview

ECHO BRIDGE is an intelligent educational platform designed to reduce language barriers faced by engineering students who study using English textbooks but are more comfortable understanding technical concepts in Tamil.

The system allows students to upload educational PDF documents and interact with their study materials through an AI-powered assistant.

Instead of providing generic chatbot responses, the application uses Retrieval-Augmented Generation (RAG) to retrieve relevant information from uploaded documents before generating answers.

The platform also supports Tamil translation, chapter summarization, and quiz generation to improve understanding, revision, and self-assessment.

## 🎯 Objectives

- Make technical education accessible to regional-language learners.
- Enable intelligent interaction with uploaded educational PDFs.
- Generate context-aware answers using Retrieval-Augmented Generation.
- Support Tamil explanations of technical concepts.
- Generate concise summaries for examination preparation.
- Create quizzes and MCQs for self-assessment.
- Provide a simple and interactive browser-based learning environment.

## ✨ Key Features

### 1. PDF Document Processing
- Upload educational PDF documents.
- Extract text from uploaded documents.
- Clean and preprocess extracted content.
- Divide content into smaller chunks.

### 2. Semantic Search
- Convert document chunks into semantic embeddings.
- Store embeddings using FAISS.
- Retrieve relevant document content based on student questions.

### 3. AI-Based Question Answering
- Ask questions about uploaded study materials.
- Retrieve relevant information using semantic similarity.
- Generate context-aware responses using Phi-3 Mini through Ollama.

### 4. Tamil Language Support
- Generate Tamil translations of educational explanations.
- Preserve important technical terminology.
- Use Gemini API for Tamil translation in the current implementation.

### 5. Chapter Summarization
- Generate concise summaries from uploaded educational content.
- Support faster revision and concept understanding.

### 6. Automatic Quiz Generation
- Generate practice questions from educational documents.
- Support multiple-choice questions and other question formats implemented in the quiz module.
- Enable students to assess their understanding.

### 7. Interactive Web Interface
- Browser-based frontend.
- PDF upload and document management.
- Ask AI, Summary, and Quiz sections.
- Loading indicators and notifications.

---

## 🏗️ System Architecture

The project follows a Retrieval-Augmented Generation (RAG) architecture.

```text
             STUDENT
                |
                v
       HTML / CSS / JavaScript
             FRONTEND
                |
                v
          FASTAPI BACKEND
                |
                v
        PDF DOCUMENT UPLOAD
                |
                v
         TEXT EXTRACTION
                |
                v
       TEXT PREPROCESSING
          AND CHUNKING
                |
                v
       SEMANTIC EMBEDDINGS
                |
                v
          FAISS VECTOR
             STORAGE
                |
                v
        STUDENT QUESTION
                |
                v
       QUESTION EMBEDDING
                |
                v
        SEMANTIC RETRIEVAL
                |
                v
       RELEVANT DOCUMENT
             CHUNKS
                |
                v
       PHI-3 MINI (OLLAMA)
                |
                v
       CONTEXT-AWARE ANSWER
                |
                v
       GEMINI API TRANSLATION
                |
                v
       ENGLISH / TAMIL OUTPUT
                |
                v
          STUDENT RESPONSE
```

The summarization and quiz generation modules process the uploaded document content through their respective backend workflows.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Frontend | HTML, CSS, JavaScript |
| Backend Framework | FastAPI |
| PDF Processing | pdfplumber, PyPDF2 |
| Text Preprocessing | Python |
| Embedding Model | Tamil-ai/tamil-embed-base |
| Vector Database | FAISS |
| Local Language Model | Phi-3 Mini |
| Local Model Runtime | Ollama |
| Tamil Translation | Gemini API |
| Database | SQLite |
| PDF Report Generation | ReportLab |
| API Communication | REST API |

---

## 📂 Project Structure

```text
SMART_EDUCATION_ASSISTANT/
│
├── backend/
│   └── api.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── modules/
│   ├── embedding_generator.py
│   ├── question_answering.py
│   ├── quiz_generation.py
│   ├── retriever.py
│   ├── summarization.py
│   └── translation.py
│
├── assets/
│   └── fonts/
│
├── data/
│   └── Generated document data and indexes
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation and Setup

### Prerequisites

Install the following before running the application:

- Python 3.10 or a compatible supported version.
- Git.
- Ollama.
- Phi-3 Mini model.
- Gemini API key for translation functionality.

### Step 1: Clone the Repository

```bash
git clone https://github.com/7867Kannan/SMART_EDUCATION_ASSISTANT.git
```

### Step 2: Navigate to the Project

```bash
cd SMART_EDUCATION_ASSISTANT
```

### Step 3: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Install and Run Ollama

Install Ollama and download the Phi-3 Mini model:

```bash
ollama pull phi3:mini
```

Verify the model:

```bash
ollama list
```

Test the model:

```bash
ollama run phi3:mini
```

### Step 6: Configure Environment Variables

Create a `.env` file in the project root if required by the translation module.

Add your Gemini API key using the variable name expected by your `modules/translation.py` implementation.

Example:

```env
GEMINI_API_KEY=your_api_key_here
```

**Security:** Never upload `.env` or expose your API key on GitHub.

### Step 7: Start the Backend

Open Terminal 1:

```powershell
python -m uvicorn backend.api:app --reload
```

Backend address:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

### Step 8: Start the Frontend

Open Terminal 2:

```powershell
cd frontend
python -m http.server 5500
```

Open the application:

```text
http://127.0.0.1:5500
```

---

## 🔄 Application Workflow

1. The student opens the web application.
2. An educational PDF is uploaded.
3. The backend extracts and preprocesses the PDF text.
4. The extracted content is divided into smaller chunks.
5. The embedding model converts chunks into vector representations.
6. FAISS stores the vectors for semantic retrieval.
7. The student submits a question.
8. The retriever identifies relevant document chunks.
9. Phi-3 Mini generates an answer using the retrieved context.
10. The translation module provides Tamil translation.
11. Students can also generate summaries and quizzes.

---

## 🔌 Main API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | API status |
| `/health` | GET | Backend health check |
| `/process-pdf` | POST | Upload and process PDF |
| `/ask` | POST | Ask questions about uploaded content |
| `/summary` | POST | Generate document summary |
| `/quiz` | POST | Generate practice quiz |
| `/download/answer` | GET | Download answer |
| `/download/summary` | GET | Download summary |
| `/download/quiz` | POST | Download quiz answer review |

---

## 🌐 Deployment and Offline Considerations

The application uses a local-first architecture.

- PDF processing runs locally.
- Semantic embedding and FAISS retrieval run locally.
- Phi-3 Mini inference runs locally through Ollama.
- Gemini-based Tamil translation requires internet connectivity and an API key.

Therefore, the current implementation is a hybrid local/cloud application rather than a completely offline system.

---

## 🚀 Future Enhancements

- Speech recognition and voice-based interaction.
- Tamil text-to-speech support.
- Handwritten note recognition.
- Support for additional Indian languages.
- Adaptive learning recommendations.
- Mobile application development.
- Improved quiz difficulty and personalized assessment.
- Additional document formats such as DOCX and PPTX.

---

## 👨‍💻 Project Team

**Project Title:** Bridging Knowledge: A Smart Education Assistant for Regional Language Learning

**Institution:** Sri Shakthi Institute of Engineering and Technology

**Department:** Artificial Intelligence and Data Science

**Project Guide:** Dr. V. Kamalav​​eni

**Team Members:**

1. Kannan N
2. K. S. Rosenpranav
3. Jeeva S
4. Mohanraja V

---

## 📚 References

1. Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, NeurIPS, 2020.
2. Devlin et al., BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding, 2019.
3. Reimers and Gurevych, Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks, 2019.
4. Johnson, Douze, and Jégou, Billion-scale Similarity Search with FAISS, 2019.
5. Microsoft Research, Phi-3 Technical Report, 2024.
6. AI4Bharat, IndicTrans2 Research and Documentation.

---

**ECHO BRIDGE – Making Technical Education More Accessible Through AI and Regional Languages.**

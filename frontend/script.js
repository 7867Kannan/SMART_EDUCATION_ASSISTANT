/* ============================================================
   Smart Education Assistant
   Frontend JavaScript — FastAPI Integration
   ============================================================ */

"use strict";

const API_BASE = "http://127.0.0.1:8000";

/* ------------------------- Application State ------------------------- */

const state = {
    documents: [],
    selectedFile: null,
    currentQuiz: [],
    currentQuestionIndex: 0,
    userAnswers: {},
    checkedAnswers: {},
    quizFinished: false,
    apiOnline: false,
    isProcessing: false
};

/* ------------------------- DOM Utilities ------------------------- */

function $(selector, root = document) {
    return root.querySelector(selector);
}

function $$(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return entities[character];
    });
}

function formatText(value) {
    let text = escapeHTML(value);

    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

    return text
        .split(/\n{2,}/)
        .map(paragraph => paragraph.replace(/\n/g, "<br>"))
        .map(paragraph => `<p>${paragraph}</p>`)
        .join("");
}

async function readResponse(response) {
    const text = await response.text();

    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { detail: text };
    }

    if (!response.ok) {
        const message =
            data.detail ||
            data.message ||
            `Request failed with status ${response.status}`;

        throw new Error(
            typeof message === "string"
                ? message
                : JSON.stringify(message)
        );
    }

    return data;
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(options.body instanceof FormData
                ? {}
                : options.body
                    ? { "Content-Type": "application/json" }
                    : {}),
            ...(options.headers || {})
        }
    });

    return readResponse(response);
}

/* ------------------------- Toast Notifications ------------------------- */

let toastTimer = null;

function showToast(message, type = "info") {
    const toast = $("#toast");

    if (!toast) {
        console.log(`[${type}] ${message}`);
        return;
    }

    toast.textContent = message;
    toast.className = "toast show";

    if (type === "success") {
        toast.classList.add("toast-success");
    } else if (type === "error") {
        toast.classList.add("toast-error");
    } else if (type === "warning") {
        toast.classList.add("toast-warning");
    }

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3500);
}

/* ------------------------- Loading Overlay ------------------------- */

function showLoading(
    title = "Please wait",
    message = "Processing your request..."
) {
    const overlay = $("#loadingOverlay");

    if (!overlay) return;

    const titleElement = $("#loadingTitle");
    const messageElement = $("#loadingMessage");

    if (titleElement) {
        titleElement.textContent = title;
    }

    if (messageElement) {
        messageElement.textContent = message;
    }

    overlay.classList.remove("hidden");
    overlay.classList.add("active");
    overlay.setAttribute("aria-hidden", "false");
}

function hideLoading() {
    const overlay = $("#loadingOverlay");

    if (!overlay) return;

    overlay.classList.remove("active");
    overlay.classList.add("hidden");
    overlay.setAttribute("aria-hidden", "true");
}

/* ------------------------- API Health Status ------------------------- */

function setApiStatus(isOnline) {
    state.apiOnline = isOnline;

    const indicators = [
        $("#sideDot"),
        $("#topDot"),
        $("#chatStatusDot")
    ].filter(Boolean);

    indicators.forEach(dot => {
        dot.classList.toggle("offline", !isOnline);
    });

    const statusElements = [
        $("#sideStatus"),
        $("#topStatus")
    ].filter(Boolean);

    statusElements.forEach(element => {
        element.textContent = isOnline ? "Connected" : "Offline";
    });
}

async function checkApiHealth() {
    try {
        const data = await apiRequest("/health");

        const healthy =
            data.status === "ok" ||
            data.status === "healthy" ||
            data.success === true;

        setApiStatus(healthy);

        return healthy;
    } catch (error) {
        setApiStatus(false);
        console.warn("API health check failed:", error.message);

        return false;
    }
}

/* ------------------------- Navigation ------------------------- */

const pageNames = {
    dashboard: "Dashboard",
    documents: "Documents",
    ask: "Ask AI",
    summary: "Chapter Summary",
    quiz: "Quiz Generator"
};

function navigateToPage(pageName) {
    const page = $(`#page-${pageName}`);

    if (!page) {
        console.warn(`Page not found: ${pageName}`);
        return;
    }

    $$(".page-container").forEach(container => {
        container.classList.remove("active");
    });

    page.classList.add("active");

    $$(".nav-item[data-page]").forEach(item => {
        item.classList.toggle(
            "active",
            item.dataset.page === pageName
        );
    });

    const breadcrumb = $("#breadcrumb");

    if (breadcrumb) {
        breadcrumb.textContent = pageNames[pageName] || "Dashboard";
    }

    $("#sidebar")?.classList.remove("open");

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

function initializeNavigation() {
    $$("[data-page]").forEach(element => {
        element.addEventListener("click", event => {
            event.preventDefault();

            const pageName = element.dataset.page;

            if (pageName) {
                navigateToPage(pageName);
            }
        });
    });

    $("#menuButton")?.addEventListener("click", () => {
        $("#sidebar")?.classList.toggle("open");
    });

    document.addEventListener("click", event => {
        const sidebar = $("#sidebar");
        const menuButton = $("#menuButton");

        if (
            window.innerWidth <= 900 &&
            sidebar &&
            sidebar.classList.contains("open") &&
            !sidebar.contains(event.target) &&
            !menuButton?.contains(event.target)
        ) {
            sidebar.classList.remove("open");
        }
    });
}

/* ------------------------- Theme Toggle ------------------------- */

function initializeTheme() {
    const savedTheme = localStorage.getItem("smartedu-theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark-theme");
    }

    $("#themeToggle")?.addEventListener("click", () => {
        document.body.classList.toggle("dark-theme");

        const theme = document.body.classList.contains("dark-theme")
            ? "dark"
            : "light";

        localStorage.setItem("smartedu-theme", theme);
    });
}

/* ------------------------- File Size ------------------------- */

function formatFileSize(bytes) {
    if (!Number.isFinite(bytes) || bytes < 0) {
        return "Unknown size";
    }

    if (bytes < 1024) {
        return `${bytes} B`;
    }

    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/* ------------------------- PDF Selection ------------------------- */

function selectPDF(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showToast("Please select a PDF file.", "error");
        return;
    }

    if (file.size === 0) {
        showToast("The selected file is empty.", "error");
        return;
    }

    state.selectedFile = file;

    const selectedFile = $("#selectedFile");
    const fileName = $("#selectedFileName");
    const fileSize = $("#selectedFileSize");

    if (fileName) {
        fileName.textContent = file.name;
    }

    if (fileSize) {
        fileSize.textContent = formatFileSize(file.size);
    }

    if (selectedFile) {
        selectedFile.hidden = false;
        selectedFile.classList.add("visible");
    }

    const processButton = $("#processButton");

    if (processButton) {
        processButton.disabled = false;
    }

    showToast("PDF selected successfully.", "success");
}

function clearSelectedPDF() {
    state.selectedFile = null;

    const input = $("#pdfInput");
    const selectedFile = $("#selectedFile");
    const processButton = $("#processButton");

    if (input) {
        input.value = "";
    }

    if (selectedFile) {
        selectedFile.hidden = true;
        selectedFile.classList.remove("visible");
    }

    if (processButton) {
        processButton.disabled = true;
    }

    updateProcessingProgress(
        0,
        "Ready to upload",
        "Select a PDF to begin."
    );
}

function initializeFileSelection() {
    const input = $("#pdfInput");
    const dropZone = $("#dropZone");
    const chooseButton = $("#chooseFileButton");

    if (!input || !dropZone) {
        console.warn("PDF upload elements were not found.");
        return;
    }

    input.addEventListener("change", () => {
        selectPDF(input.files?.[0]);
    });

    chooseButton?.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        input.click();
    });

    dropZone.addEventListener("click", event => {
        if (
            event.target.closest("#chooseFileButton") ||
            event.target.closest("#removeFile")
        ) {
            return;
        }

        input.click();
    });

    dropZone.addEventListener("dragover", event => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", event => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", event => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");

        const file = event.dataTransfer?.files?.[0];

        if (file) {
            selectPDF(file);
        }
    });

    $("#removeFile")?.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        clearSelectedPDF();
    });

    $("#processButton")?.addEventListener("click", processPDF);
}

/* ------------------------- Processing Progress ------------------------- */

function updateProcessingProgress(percent, status, detail) {
    const progress = Math.max(0, Math.min(100, percent));

    const progressBar = $(".progress-fill");
    const percentElement = $("#processPercent");
    const statusElement = $("#processStatus");
    const detailElement = $("#processDetail");

    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }

    if (percentElement) {
        percentElement.textContent = `${progress}%`;
    }

    if (statusElement) {
        statusElement.textContent = status;
    }

    if (detailElement) {
        detailElement.textContent = detail;
    }
}

/* ------------------------- PDF Processing ------------------------- */

async function processPDF() {
    if (state.isProcessing) return;

    if (!state.selectedFile) {
        showToast("Please select a PDF first.", "warning");
        return;
    }

    state.isProcessing = true;

    const processButton = $("#processButton");

    if (processButton) {
        processButton.disabled = true;
        processButton.textContent = "Processing...";
    }

    const progressContainer = $("#processProgress");

    if (progressContainer) {
        progressContainer.hidden = false;
        progressContainer.classList.add("visible");
    }

    updateProcessingProgress(
        10,
        "Uploading document",
        "Sending the PDF to the local backend..."
    );

    showLoading(
        "Processing your document",
        "Extracting text and preparing semantic search..."
    );

    try {
        const formData = new FormData();
        formData.append("file", state.selectedFile);

        updateProcessingProgress(
            35,
            "Extracting text",
            "The backend is reading the PDF content."
        );

        const data = await apiRequest("/process-pdf", {
            method: "POST",
            body: formData
        });

        if (data.success === false) {
            throw new Error(
                data.message ||
                data.detail ||
                "PDF processing failed."
            );
        }

        const documentName =
            data.document_name ||
            data.filename ||
            state.selectedFile.name;

        const chunkCount = Number(
            data.chunks ??
            data.chunk_count ??
            data.total_chunks ??
            0
        );

        const existingIndex = state.documents.findIndex(
            document => document.name === documentName
        );

        const documentInfo = {
            name: documentName,
            size: state.selectedFile.size,
            chunks: chunkCount,
            processedAt: new Date()
        };

        if (existingIndex >= 0) {
            state.documents[existingIndex] = documentInfo;
        } else {
            state.documents.push(documentInfo);
        }

        updateProcessingProgress(
            100,
            "Processing completed",
            "Your document is ready to use."
        );

        updateDocumentStatistics();
        renderDocumentList();

        showToast("PDF processed successfully!", "success");

        clearSelectedPDF();

        navigateToPage("documents");
    } catch (error) {
        console.error("PDF processing error:", error);

        updateProcessingProgress(
            0,
            "Processing failed",
            error.message || "Could not process the PDF."
        );

        showToast(
            `PDF processing failed: ${error.message}`,
            "error"
        );
    } finally {
        hideLoading();

        state.isProcessing = false;

        if (progressContainer) {
            progressContainer.hidden = true;
            progressContainer.classList.remove("visible");
        }

        if (processButton) {
            processButton.disabled = !state.selectedFile;
            processButton.textContent = "Process Document";
        }
    }
}

/* ------------------------- Document Statistics ------------------------- */

function updateDocumentStatistics() {
    const documentCount = state.documents.length;

    const totalChunks = state.documents.reduce(
        (total, document) => total + (document.chunks || 0),
        0
    );

    const documentCountElement = $("#documentCount");
    const navDocumentCount = $("#navDocumentCount");
    const chunkCountElement = $("#chunkCount");

    if (documentCountElement) {
        documentCountElement.textContent = documentCount;
    }

    if (navDocumentCount) {
        navDocumentCount.textContent = documentCount;
    }

    if (chunkCountElement) {
        chunkCountElement.textContent = totalChunks;
    }

    const libraryCaption = $("#libraryCaption");

    if (libraryCaption) {
        libraryCaption.textContent = documentCount
            ? `${documentCount} document${documentCount === 1 ? "" : "s"} processed in this session`
            : "Upload a PDF to build your document library";
    }
}

/* ------------------------- Document List ------------------------- */

function renderDocumentList() {
    const container = $("#documentList");

    if (!container) return;

    if (state.documents.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📄</div>
                <h3>No documents yet</h3>
                <p>Upload an educational PDF to get started.</p>
                <button class="btn btn-primary" data-page="documents">
                    Upload a document
                </button>
            </div>
        `;

        container.querySelector("[data-page]")?.addEventListener(
            "click",
            () => navigateToPage("documents")
        );

        return;
    }

    container.innerHTML = state.documents.map((document, index) => `
        <div class="document-card">
            <div class="document-icon">📄</div>

            <div class="document-info">
                <h3>${escapeHTML(document.name)}</h3>
                <p>
                    ${escapeHTML(formatFileSize(document.size))}
                    &nbsp;•&nbsp;
                    ${document.chunks} chunks
                </p>
            </div>

            <div class="document-status">
                <span class="status-badge success">Processed</span>
            </div>

            <button
                type="button"
                class="btn btn-secondary document-ask-button"
                data-document-index="${index}"
            >
                Ask AI
            </button>
        </div>
    `).join("");

    $$(".document-ask-button", container).forEach(button => {
        button.addEventListener("click", () => {
            navigateToPage("ask");
            $("#questionInput")?.focus();
        });
    });
}

/* ------------------------- Ask AI ------------------------- */

function addMessage(container, role, content, label) {
    const message = document.createElement("div");
    message.className = `chat-message ${role}`;

    const heading = document.createElement("div");
    heading.className = "message-label";
    heading.textContent = label;

    const body = document.createElement("div");
    body.className = "message-content";
    body.innerHTML = formatText(content);

    message.appendChild(heading);
    message.appendChild(body);

    container.appendChild(message);

    return message;
}

function renderAnswer(data) {
    const container = $("#answerArea");

    if (!container) return;

    container.innerHTML = "";

    const englishAnswer =
        data.english_answer ||
        data.answer ||
        data.response ||
        "";

    const tamilAnswer =
        data.tamil_answer ||
        data.translated_answer ||
        "";

    if (!englishAnswer && !tamilAnswer) {
        addMessage(
            container,
            "assistant",
            "The backend returned no answer. Please try asking again.",
            "SmartEdu"
        );

        return;
    }

    if (
        englishAnswer &&
        tamilAnswer &&
        englishAnswer !== tamilAnswer
    ) {
        addMessage(
            container,
            "assistant",
            englishAnswer,
            "English Explanation"
        );

        addMessage(
            container,
            "assistant tamil-message",
            tamilAnswer,
            "தமிழ் விளக்கம்"
        );
    } else {
        addMessage(
            container,
            "assistant",
            tamilAnswer || englishAnswer,
            tamilAnswer ? "தமிழ் விளக்கம்" : "SmartEdu Answer"
        );
    }

    container.scrollTop = container.scrollHeight;
}

async function askQuestion(question) {
    const cleanedQuestion = String(question || "").trim();

    if (!cleanedQuestion) {
        showToast("Please enter a question.", "warning");
        return;
    }

    if (state.documents.length === 0) {
        showToast(
            "Please upload and process a PDF before asking questions.",
            "warning"
        );

        navigateToPage("documents");
        return;
    }

    const container = $("#answerArea");

    if (!container) return;

    addMessage(
        container,
        "user",
        cleanedQuestion,
        "You"
    );

    const loadingMessage = addMessage(
        container,
        "assistant",
        "Searching your document and generating an answer...",
        "SmartEdu"
    );

    const askButton = $("#askButton");

    if (askButton) {
        askButton.disabled = true;
    }

    showLoading(
        "Finding your answer",
        "Searching relevant content in your study material..."
    );

    try {
        const data = await apiRequest("/ask", {
            method: "POST",
            body: JSON.stringify({
                question: cleanedQuestion,
                translate: true
            })
        });

        if (data.success === false) {
            throw new Error(
                data.message ||
                data.detail ||
                "Question answering failed."
            );
        }

        loadingMessage.remove();
        renderAnswer(data);
    } catch (error) {
        console.error("Question answering error:", error);

        loadingMessage.remove();

        addMessage(
            container,
            "assistant error-message",
            `Sorry, I could not answer this question. ${error.message}`,
            "Error"
        );

        showToast("Unable to generate an answer.", "error");
    } finally {
        hideLoading();

        if (askButton) {
            askButton.disabled = false;
        }
    }
}

function initializeAskForm() {
    $("#askForm")?.addEventListener("submit", event => {
        event.preventDefault();

        const input = $("#questionInput");

        if (!input) return;

        const question = input.value.trim();

        if (!question) return;

        input.value = "";

        askQuestion(question);
    });

    $$(".suggestion-chip[data-question]").forEach(button => {
        button.addEventListener("click", () => {
            const question = button.dataset.question || "";

            navigateToPage("ask");

            const input = $("#questionInput");

            if (input) {
                input.value = question;
                input.focus();
            }
        });
    });
}

/* ------------------------- Summary ------------------------- */

function renderSummary(data) {
    const container = $("#summaryArea");

    if (!container) return;

    const englishSummary =
        data.english_summary ||
        data.summary ||
        data.english ||
        data.response ||
        "";

    const tamilSummary =
        data.tamil_summary ||
        data.translated_summary ||
        data.tamil ||
        "";

    if (!englishSummary && !tamilSummary) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No summary returned</h3>
                <p>Please check the backend response and try again.</p>
            </div>
        `;

        return;
    }

    container.innerHTML = "";

    if (
        englishSummary &&
        tamilSummary &&
        englishSummary !== tamilSummary
    ) {
        const englishSection = document.createElement("section");
        englishSection.className = "summary-section";

        const englishHeading = document.createElement("h3");
        englishHeading.textContent = "English Summary";

        const englishBody = document.createElement("div");
        englishBody.className = "summary-content";
        englishBody.innerHTML = formatText(englishSummary);

        englishSection.append(englishHeading, englishBody);

        const tamilSection = document.createElement("section");
        tamilSection.className = "summary-section";

        const tamilHeading = document.createElement("h3");
        tamilHeading.textContent = "தமிழ் சுருக்கம்";

        const tamilBody = document.createElement("div");
        tamilBody.className = "summary-content";
        tamilBody.innerHTML = formatText(tamilSummary);

        tamilSection.append(tamilHeading, tamilBody);

        container.append(englishSection, tamilSection);
    } else {
        container.innerHTML = formatText(
            tamilSummary || englishSummary
        );
    }

    $("#summaryActions")?.classList.remove("hidden");
    $("#summaryActions")?.classList.add("visible");
}

async function generateSummary() {
    if (state.documents.length === 0) {
        showToast(
            "Please process a PDF before generating a summary.",
            "warning"
        );

        navigateToPage("documents");
        return;
    }

    const button = $("#summaryButton");

    if (button) {
        button.disabled = true;
        button.textContent = "Generating...";
    }

    showLoading(
        "Generating chapter summary",
        "Summarizing the content of your study material..."
    );

    try {
        const data = await apiRequest("/summary", {
            method: "POST"
        });

        if (data.success === false) {
            throw new Error(
                data.message ||
                data.detail ||
                "Summary generation failed."
            );
        }

        renderSummary(data);

        showToast("Summary generated successfully.", "success");
    } catch (error) {
        console.error("Summary error:", error);

        showToast(`Summary failed: ${error.message}`, "error");
    } finally {
        hideLoading();

        if (button) {
            button.disabled = false;
            button.textContent = "Generate Summary";
        }
    }
}

function initializeSummary() {
    $("#summaryButton")?.addEventListener(
        "click",
        generateSummary
    );

    $("#copySummaryButton")?.addEventListener(
        "click",
        async () => {
            const container = $("#summaryArea");

            if (!container || !container.innerText.trim()) {
                showToast("Generate a summary first.", "warning");
                return;
            }

            try {
                await navigator.clipboard.writeText(
                    container.innerText
                );

                showToast(
                    "Summary copied to clipboard.",
                    "success"
                );
            } catch {
                showToast(
                    "Unable to copy. Please select and copy the text manually.",
                    "error"
                );
            }
        }
    );

    $("#downloadSummaryButton")?.addEventListener(
        "click",
        () => {
            downloadFromEndpoint(
                "/download/summary",
                "summary.txt"
            );
        }
    );
}

/* ------------------------- File Downloads ------------------------- */

async function downloadFromEndpoint(endpoint, fallbackName) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);

        if (!response.ok) {
            const errorData = await readResponse(response);

            throw new Error(
                errorData.detail ||
                errorData.message ||
                "Download failed."
            );
        }

        const blob = await response.blob();

        const disposition =
            response.headers.get("Content-Disposition") || "";

        const match = disposition.match(
            /filename="?([^";]+)"?/i
        );

        const filename = match?.[1] || fallbackName;

        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");

        anchor.href = url;
        anchor.download = filename;

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        window.setTimeout(() => {
            URL.revokeObjectURL(url);
        }, 1000);

        showToast("Download started.", "success");
    } catch (error) {
        console.error("Download error:", error);

        showToast(
            `Download failed: ${error.message}`,
            "error"
        );
    }
}

/* ------------------------- Quiz Answer Review PDF ------------------------- */

async function downloadQuizPDF() {
    if (!state.quizFinished || state.currentQuiz.length === 0) {
        showToast(
            "Please finish the quiz before downloading the answer review.",
            "warning"
        );

        return;
    }

    const button = $("#downloadQuizButton");

    if (button) {
        button.disabled = true;
    }

    try {
        const answers = state.currentQuiz.map(
            (question, index) => {
                const studentAnswer =
                    state.userAnswers[index] ?? "";

                const correct = isCorrectAnswer(
                    question,
                    studentAnswer
                );

                return {
                    question_id: `q${index + 1}`,
                    question_index: index,
                    student_answer: String(studentAnswer),
                    is_correct: correct
                };
            }
        );

        const correctCount = answers.filter(
            answer => answer.is_correct
        ).length;

        const total = answers.length;

        const percentage = total
            ? Math.round((correctCount / total) * 100)
            : 0;

        const response = await fetch(
            `${API_BASE}/download/quiz`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    answers,
                    score: correctCount,
                    total,
                    percentage
                })
            }
        );

        if (!response.ok) {
            let message =
                `Quiz PDF download failed (HTTP ${response.status}).`;

            try {
                const errorData = await readResponse(response);

                message =
                    errorData.detail ||
                    errorData.message ||
                    message;
            } catch (error) {
                message = error.message || message;
            }

            throw new Error(message);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");

        const disposition =
            response.headers.get("Content-Disposition") || "";

        const filenameMatch = disposition.match(
            /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i
        );

        const filename = filenameMatch
            ? decodeURIComponent(
                filenameMatch[1] || filenameMatch[2]
            )
            : "practice_quiz_answer_review.pdf";

        anchor.href = url;
        anchor.download = filename;

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        window.setTimeout(() => {
            URL.revokeObjectURL(url);
        }, 1000);

        showToast(
            "Quiz answer review PDF downloaded successfully.",
            "success"
        );
    } catch (error) {
        console.error(
            "Quiz answer review PDF error:",
            error
        );

        showToast(
            `Quiz PDF download failed: ${error.message}`,
            "error"
        );
    } finally {
        if (button) {
            button.disabled = false;
        }
    }
}

/* ------------------------- Quiz Data Normalization ------------------------- */

function normalizeQuizType(value) {
    const type = String(value || "mcq").toLowerCase();

    if (
        type.includes("true") ||
        type.includes("false") ||
        type.includes("boolean")
    ) {
        return "true_false";
    }

    if (
        type.includes("fill") ||
        type.includes("blank")
    ) {
        return "fill_blank";
    }

    return "mcq";
}

function normalizeOptions(options) {
    if (Array.isArray(options)) {
        return options.map((option, index) => {
            if (typeof option === "object" && option !== null) {
                return {
                    key: String(
                        option.key ??
                        option.label ??
                        String.fromCharCode(65 + index)
                    ),
                    text: String(
                        option.text ??
                        option.value ??
                        option.option ??
                        ""
                    )
                };
            }

            return {
                key: String.fromCharCode(65 + index),
                text: String(option)
            };
        });
    }

    if (options && typeof options === "object") {
        return Object.entries(options).map(
            ([key, value]) => ({
                key: String(key),
                text: String(value)
            })
        );
    }

    return [];
}

function normalizeQuestion(question, index) {
    const type = normalizeQuizType(
        question.type ||
        question.question_type ||
        question.questionType
    );

    const rawOptions =
        question.options ||
        question.choices ||
        question.answers ||
        [];

    return {
        id: index,
        type,

        question: String(
            question.question ||
            question.text ||
            question.prompt ||
            `Question ${index + 1}`
        ),

        options: type === "true_false"
            ? [
                { key: "True", text: "True" },
                { key: "False", text: "False" }
            ]
            : normalizeOptions(rawOptions),

        answer:
            question.correct_answer ??
            question.correctAnswer ??
            question.answer ??
            "",

        explanation: String(
            question.explanation ||
            question.reason ||
            ""
        )
    };
}

function extractQuizQuestions(data) {
    let questions = [];

    if (Array.isArray(data.questions)) {
        questions = data.questions;
    } else if (Array.isArray(data.quiz)) {
        questions = data.quiz;
    } else if (
        data.quiz &&
        Array.isArray(data.quiz.questions)
    ) {
        questions = data.quiz.questions;
    } else if (
        data.data &&
        Array.isArray(data.data.questions)
    ) {
        questions = data.data.questions;
    }

    return questions.map(normalizeQuestion);
}

/* ------------------------- Quiz Generation ------------------------- */

async function generateQuiz() {
    if (state.documents.length === 0) {
        showToast(
            "Please process a PDF before generating a quiz.",
            "warning"
        );

        navigateToPage("documents");
        return;
    }

    const button = $("#quizButton");

    if (button) {
        button.disabled = true;
        button.textContent = "Generating...";
    }

    showLoading(
        "Creating your quiz",
        "Generating questions from your study material..."
    );

    try {
        const data = await apiRequest("/quiz", {
            method: "POST"
        });

        if (data.success === false) {
            throw new Error(
                data.message ||
                data.detail ||
                "Quiz generation failed."
            );
        }

        const questions = extractQuizQuestions(data);

        if (questions.length === 0) {
            throw new Error(
                "The backend did not return any questions in the expected format."
            );
        }

        state.currentQuiz = questions;
        state.currentQuestionIndex = 0;
        state.userAnswers = {};
        state.checkedAnswers = {};
        state.quizFinished = false;

        $("#quizIntro")?.classList.add("hidden");
        $("#quizWorkspace")?.classList.remove("hidden");
        $("#quizResults")?.classList.add("hidden");

        renderQuizQuestion();

        showToast(
            `${questions.length} quiz questions generated.`,
            "success"
        );
    } catch (error) {
        console.error("Quiz generation error:", error);

        showToast(
            `Quiz generation failed: ${error.message}`,
            "error"
        );
    } finally {
        hideLoading();

        if (button) {
            button.disabled = false;
            button.textContent = "Generate Quiz";
        }
    }
}

/* ------------------------- Quiz Rendering ------------------------- */

function renderQuizQuestion() {
    const container = $("#quizArea");

    if (!container || state.currentQuiz.length === 0) {
        return;
    }

    const index = state.currentQuestionIndex;
    const question = state.currentQuiz[index];

    const progress = Math.round(
        ((index + 1) / state.currentQuiz.length) * 100
    );

    if ($("#quizProgressLabel")) {
        $("#quizProgressLabel").textContent =
            `Question ${index + 1} of ${state.currentQuiz.length}`;
    }

    if ($("#quizProgressPercent")) {
        $("#quizProgressPercent").textContent =
            `${progress}%`;
    }

    if ($("#quizProgressBar")) {
        $("#quizProgressBar").style.width = `${progress}%`;
    }

    const savedAnswer = state.userAnswers[index] ?? "";
    const checked = Boolean(state.checkedAnswers[index]);

    let answerControls = "";

    if (question.type === "fill_blank") {
        answerControls = `
            <label
                class="quiz-answer-label"
                for="fillBlankAnswer"
            >
                Your answer
            </label>

            <input
                type="text"
                id="fillBlankAnswer"
                class="quiz-fill-input"
                placeholder="Type your answer..."
                value="${escapeHTML(savedAnswer)}"
                ${checked ? "disabled" : ""}
                autocomplete="off"
            >
        `;
    } else {
        const options = question.options.length
            ? question.options
            : question.type === "true_false"
                ? [
                    { key: "True", text: "True" },
                    { key: "False", text: "False" }
                ]
                : [];

        answerControls = `
            <div class="quiz-options">
                ${options.map((option, optionIndex) => {
                    const value = option.key;

                    const isSelected =
                        String(savedAnswer) === String(value);

                    let resultClass = "";

                    if (checked) {
                        const correct = isCorrectAnswer(
                            question,
                            value
                        );

                        if (correct) {
                            resultClass = "correct-option";
                        } else if (isSelected) {
                            resultClass = "incorrect-option";
                        }
                    }

                    return `
                        <label
                            class="quiz-option ${isSelected ? "selected" : ""} ${resultClass}"
                        >
                            <input
                                type="radio"
                                name="quizAnswer"
                                value="${escapeHTML(value)}"
                                ${isSelected ? "checked" : ""}
                                ${checked ? "disabled" : ""}
                            >

                            <span class="option-letter">
                                ${escapeHTML(
                                    String.fromCharCode(65 + optionIndex)
                                )}
                            </span>

                            <span class="option-text">
                                ${escapeHTML(option.text)}
                            </span>
                        </label>
                    `;
                }).join("")}
            </div>
        `;
    }

    container.innerHTML = `
        <div class="quiz-question-card">
            <div class="quiz-question-meta">
                <span class="quiz-question-number">
                    Question ${index + 1}
                </span>

                <span class="quiz-question-type">
                    ${escapeHTML(
                        question.type === "mcq"
                            ? "Multiple Choice"
                            : question.type === "true_false"
                                ? "True or False"
                                : "Fill in the Blank"
                    )}
                </span>
            </div>

            <h3 class="quiz-question-text">
                ${escapeHTML(question.question)}
            </h3>

            ${answerControls}

            <div
                id="quizFeedback"
                class="quiz-feedback ${checked ? "visible" : ""}"
            >
                ${checked
                    ? renderQuizFeedback(question, savedAnswer)
                    : ""}
            </div>

            <div class="quiz-question-actions">
                <button
                    type="button"
                    class="btn btn-secondary"
                    id="checkAnswerButton"
                    ${checked ? "disabled" : ""}
                >
                    Check Answer
                </button>
            </div>
        </div>
    `;

    $$('input[name="quizAnswer"]', container).forEach(input => {
        input.addEventListener("change", () => {
            state.userAnswers[index] = input.value;

            $$(".quiz-option", container).forEach(option => {
                option.classList.remove("selected");
            });

            input.closest(".quiz-option")?.classList.add("selected");
        });
    });

    $("#fillBlankAnswer", container)?.addEventListener(
        "input",
        event => {
            state.userAnswers[index] = event.target.value;
        }
    );

    $("#checkAnswerButton", container)?.addEventListener(
        "click",
        checkCurrentAnswer
    );

    const previousButton = $("#prevQuestionButton");
    const nextButton = $("#nextQuestionButton");

    if (previousButton) {
        previousButton.disabled = index === 0;
    }

    if (nextButton) {
        nextButton.disabled = !checked;

        nextButton.textContent =
            index === state.currentQuiz.length - 1
                ? "Finish Quiz"
                : "Next Question";
    }
}

/* ------------------------- Quiz Answer Checking ------------------------- */

function normalizedAnswer(value) {
    return String(value ?? "")
        .trim()
        .toLowerCase()
        .replace(/[.!?]+$/g, "")
        .replace(/\s+/g, " ");
}

function isCorrectAnswer(question, selectedAnswer) {
    const expected = question.answer;

    if (
        expected === null ||
        expected === undefined ||
        String(expected).trim() === ""
    ) {
        return false;
    }

    const selected = normalizedAnswer(selectedAnswer);
    const answer = normalizedAnswer(expected);

    if (selected === answer) {
        return true;
    }

    const selectedOption = question.options.find(
        option => normalizedAnswer(option.key) === selected
    );

    if (
        selectedOption &&
        normalizedAnswer(selectedOption.text) === answer
    ) {
        return true;
    }

    const answerOption = question.options.find(
        option =>
            normalizedAnswer(option.key) === answer ||
            normalizedAnswer(option.text) === answer
    );

    if (
        selectedOption &&
        answerOption &&
        selectedOption.key === answerOption.key
    ) {
        return true;
    }

    if (question.type === "true_false") {
        const normalizeBoolean = value => {
            const v = normalizedAnswer(value);

            if (["true", "t", "yes", "1"].includes(v)) {
                return "true";
            }

            if (["false", "f", "no", "0"].includes(v)) {
                return "false";
            }

            return v;
        };

        return (
            normalizeBoolean(selectedAnswer) ===
            normalizeBoolean(expected)
        );
    }

    return false;
}

function getCorrectAnswerText(question) {
    const expected = String(question.answer ?? "");

    const correctOption = question.options.find(
        option =>
            normalizedAnswer(option.key) === normalizedAnswer(expected) ||
            normalizedAnswer(option.text) === normalizedAnswer(expected)
    );

    return correctOption
        ? `${correctOption.key}. ${correctOption.text}`
        : expected;
}

function getStudentAnswerText(question, selectedAnswer) {
    const answer = String(selectedAnswer ?? "").trim();

    if (!answer) {
        return "Not answered";
    }

    const selectedOption = question.options.find(
        option =>
            normalizedAnswer(option.key) === normalizedAnswer(answer)
    );

    if (selectedOption) {
        return `${selectedOption.key}. ${selectedOption.text}`;
    }

    return answer;
}

function renderQuizFeedback(question, selectedAnswer) {
    const correct = isCorrectAnswer(question, selectedAnswer);

    let html = correct
        ? "<strong>Correct!</strong> Well done."
        : "<strong>Not quite.</strong> Review the correct answer below.";

    if (!correct && question.answer !== "") {
        html += `
            <p>
                <strong>Correct answer:</strong>
                ${escapeHTML(getCorrectAnswerText(question))}
            </p>
        `;
    }

    if (question.explanation) {
        html += `
            <p>${escapeHTML(question.explanation)}</p>
        `;
    }

    return html;
}

function checkCurrentAnswer() {
    const index = state.currentQuestionIndex;
    const question = state.currentQuiz[index];

    if (!question) return;

    let answer = state.userAnswers[index];

    if (question.type === "fill_blank") {
        answer = $("#fillBlankAnswer")?.value?.trim() || "";
    }

    if (
        answer === undefined ||
        String(answer).trim() === ""
    ) {
        showToast(
            "Please select or enter an answer first.",
            "warning"
        );

        return;
    }

    state.userAnswers[index] = answer;
    state.checkedAnswers[index] = true;

    renderQuizQuestion();
    updateQuizNavigation();
}

function updateQuizNavigation() {
    const previousButton = $("#prevQuestionButton");
    const nextButton = $("#nextQuestionButton");

    if (previousButton) {
        previousButton.disabled =
            state.currentQuestionIndex === 0;
    }

    if (nextButton) {
        nextButton.disabled =
            !state.checkedAnswers[state.currentQuestionIndex];

        nextButton.textContent =
            state.currentQuestionIndex === state.currentQuiz.length - 1
                ? "Finish Quiz"
                : "Next Question";
    }
}

/* ------------------------- Quiz Navigation and Results ------------------------- */

function goToPreviousQuestion() {
    if (state.currentQuestionIndex <= 0) return;

    state.currentQuestionIndex -= 1;

    renderQuizQuestion();
}

function goToNextQuestion() {
    const index = state.currentQuestionIndex;

    if (!state.checkedAnswers[index]) {
        showToast(
            "Check your answer before continuing.",
            "warning"
        );

        return;
    }

    if (index < state.currentQuiz.length - 1) {
        state.currentQuestionIndex += 1;
        renderQuizQuestion();
        return;
    }

    finishQuiz();
}

function finishQuiz() {
    state.quizFinished = true;

    const total = state.currentQuiz.length;
    let correctCount = 0;

    state.currentQuiz.forEach((question, index) => {
        if (
            isCorrectAnswer(
                question,
                state.userAnswers[index]
            )
        ) {
            correctCount += 1;
        }
    });

    const percentage = total
        ? Math.round((correctCount / total) * 100)
        : 0;

    $("#quizWorkspace")?.classList.add("hidden");
    $("#quizResults")?.classList.remove("hidden");

    const scoreElement = $("#quizScore");

    if (scoreElement) {
        scoreElement.textContent = `${percentage}%`;
    }

    const finalText = $("#quizFinalText");

    if (finalText) {
        finalText.textContent =
            `You answered ${correctCount} out of ${total} questions correctly.`;
    }

    showToast("Quiz completed!", "success");
}

function retryQuiz() {
    state.currentQuestionIndex = 0;
    state.userAnswers = {};
    state.checkedAnswers = {};
    state.quizFinished = false;

    $("#quizResults")?.classList.add("hidden");
    $("#quizWorkspace")?.classList.remove("hidden");

    renderQuizQuestion();
}

/* ------------------------- Quiz Initialization ------------------------- */

function initializeQuiz() {
    $("#quizButton")?.addEventListener(
        "click",
        generateQuiz
    );

    $("#prevQuestionButton")?.addEventListener(
        "click",
        goToPreviousQuestion
    );

    $("#nextQuestionButton")?.addEventListener(
        "click",
        goToNextQuestion
    );

    $("#retryQuizButton")?.addEventListener(
        "click",
        retryQuiz
    );

    $("#downloadQuizButton")?.addEventListener(
        "click",
        downloadQuizPDF
    );
}

/* ------------------------- Initial Application Setup ------------------------- */

function initializeApplication() {
    const year = $("#currentYear");

    if (year) {
        year.textContent = new Date().getFullYear();
    }

    initializeNavigation();
    initializeTheme();
    initializeFileSelection();
    initializeAskForm();
    initializeSummary();
    initializeQuiz();

    updateDocumentStatistics();
    renderDocumentList();

    clearSelectedPDF();

    checkApiHealth();

    setInterval(checkApiHealth, 15000);

    console.log(
        "Smart Education Assistant frontend initialized."
    );
}

document.addEventListener(
    "DOMContentLoaded",
    initializeApplication
);

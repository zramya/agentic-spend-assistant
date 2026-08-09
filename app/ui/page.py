import streamlit as st
import requests
import uuid
import re

# =============================================================================
# Configuration
# =============================================================================

API_BASE_URL = "http://localhost:8000"

UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v1/credit-card/ingestion"

QUERY_ENDPOINT = f"{API_BASE_URL}/api/v1/credit-card/query"


# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="NorthStar AI Spend Assistant",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Session State
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "user_name" not in st.session_state:
    st.session_state.user_name = None

if "ingestion_result" not in st.session_state:
    st.session_state.ingestion_result = None

if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None


# =============================================================================
# Helper: Personal / Simple Conversation
# =============================================================================
# These messages are handled locally so they don't make unnecessary
# FastAPI / LangGraph / LLM calls.
# =============================================================================


def handle_personal_conversation(message: str):

    text = message.strip()
    lower_text = text.lower()

    # -------------------------------------------------------------------------
    # Capture user name
    # -------------------------------------------------------------------------

    name_patterns = [
        r"my name is (.+)",
        r"i am (.+)",
        r"i'm (.+)",
        r"call me (.+)",
    ]

    for pattern in name_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            name = match.group(1).strip().title()

            st.session_state.user_name = name

            return (
                f"Hi {name}! 👋 "
                "Welcome to your NorthStar Spend Assistant. "
                "How can I help you understand your spending, rewards, or card benefits today?"
            )

    # -------------------------------------------------------------------------
    # Greetings
    # -------------------------------------------------------------------------

    greetings = [
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    if lower_text in greetings:

        if st.session_state.user_name:

            return (
                f"Hi {st.session_state.user_name}! 👋 "
                "Welcome to your NorthStar Spend Assistant. "
                "How can I help you understand your spending, rewards, or card benefits today?"
            )

        return (
            "Hello! 👋 "
            "I can help you analyze credit-card spending, "
            "rewards, fees, benefits and NorthStar card rules."
        )

    # -------------------------------------------------------------------------
    # Identity questions
    # -------------------------------------------------------------------------

    identity_questions = [
        "who am i",
        "what is my name",
        "do you know my name",
    ]

    if lower_text in identity_questions:

        if st.session_state.user_name:

            return f"You're {st.session_state.user_name}. 😊"

        return "You haven't shared your name with me yet."

    # -------------------------------------------------------------------------
    # Thanks / simple acknowledgements
    # -------------------------------------------------------------------------

    acknowledgements = [
        "thanks",
        "thank you",
        "thanks!",
        "thank you!",
        "great",
        "good",
        "awesome",
        "excellent",
        "nice",
        "perfect",
        "well done",
    ]

    if lower_text in acknowledgements:

        if st.session_state.user_name:

            return f"You're welcome, " f"{st.session_state.user_name}! 😊"

        return "You're welcome! 😊"

    return None


# =============================================================================
# Helper: Save Message
# =============================================================================


def add_message(role: str, content: str):

    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
        }
    )


# =============================================================================
# Header
# =============================================================================

st.title("💳 NorthStar AI Spend Assistant")

st.caption("Multimodal RAG • Credit Card Spend Intelligence • LangGraph")

st.markdown("""
    Ask questions about **credit-card spending, rewards, fees,
    benefits, transactions and NorthStar card rules**.
    """)


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------

    st.header("💳 NorthStar AI")

    st.caption("Credit Card Spend Intelligence")

    st.divider()

    # -------------------------------------------------------------------------
    # Knowledge Base Ingestion
    # -------------------------------------------------------------------------

    st.subheader("📚 Knowledge Base")

    st.caption(
        "Upload the NorthStar Credit Card Product Guide "
        "to create the multimodal RAG knowledge base."
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF",
        type=["pdf"],
        help=(
            "Upload the NorthStar Credit Card Product Guide. "
            "The document will be parsed into text, tables and "
            "images, followed by embedding generation."
        ),
    )

    if uploaded_file is not None:

        st.write(f"📄 **{uploaded_file.name}**")

        if st.button(
            "🚀 Ingest Document",
            type="primary",
            use_container_width=True,
        ):

            files = {
                "pdf_file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            }

            with st.spinner("Processing document and creating embeddings..."):

                try:

                    response = requests.post(
                        UPLOAD_ENDPOINT,
                        files=files,
                        timeout=600,
                    )

                    if response.status_code == 200:

                        data = response.json()

                        st.session_state.ingestion_result = data.get("data", {})

                        st.session_state.last_uploaded = uploaded_file.name

                        st.success("Document ingested successfully.")

                    else:

                        st.error(f"Ingestion failed " f"({response.status_code})")

                        st.code(response.text)

                except requests.exceptions.Timeout:

                    st.error(
                        "The ingestion request timed out. "
                        "The document may still require additional "
                        "processing time."
                    )

                except requests.exceptions.RequestException as e:

                    st.error("Unable to connect to the backend.")

                    st.code(str(e))

    # -------------------------------------------------------------------------
    # Knowledge Base Status
    # -------------------------------------------------------------------------

    if st.session_state.ingestion_result:

        result = st.session_state.ingestion_result

        st.divider()

        st.subheader("🔎 Knowledge Base Status")

        ingestion_status = result.get(
            "status",
            "unknown",
        )

        if ingestion_status == "success":

            st.success("Knowledge base ready")

        else:

            st.warning(str(ingestion_status))

        # ---------------------------------------------------------------------
        # Chunk Metrics
        # ---------------------------------------------------------------------

        chunks = result.get(
            "chunks_ingested",
            0,
        )

        st.metric(
            "🧩 Total Chunks",
            chunks,
        )

        # Current ingestion API returns the total number of chunks.
        # Detailed modality counts can be added later to the API response.
        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "🔢 Embeddings",
                chunks,
            )

        with col2:

            st.metric(
                "📐 Dimensions",
                "1536",
            )

        doc_id = result.get("doc_id")

        if doc_id:

            st.caption(f"Document ID: `{doc_id}`")

    # -------------------------------------------------------------------------
    # Architecture
    # -------------------------------------------------------------------------

    st.divider()

    st.subheader("⚙️ AI Pipeline")

    st.markdown("""
        **Multimodal Ingestion**
        
        📄 PDF  
        ↓  
        🔍 Docling  
        ↓  
        📝 Text + 📊 Tables + 🖼 Images  
        ↓  
        🔢 Embeddings  
        ↓  
        🗄️ PostgreSQL + pgvector  
        
        **Query Pipeline**
        
        💬 User Query  
        ↓  
        🧠 LangGraph  
        ↓  
        🔎 Vector Search + SQL  
        ↓  
        🤖 LLM Response
        """)

    # -------------------------------------------------------------------------
    # Recent Questions
    # -------------------------------------------------------------------------

    if st.session_state.messages:

        st.divider()

        st.subheader("💬 Recent Questions")

        user_questions = [
            message["content"]
            for message in st.session_state.messages
            if message["role"] == "user"
        ]

        for index, question in enumerate(reversed(user_questions[-5:])):

            display_question = question

            if len(display_question) > 45:

                display_question = display_question[:42] + "..."

            if st.button(
                display_question,
                key=f"previous_question_{index}",
                use_container_width=True,
                help=question,
            ):

                st.session_state.selected_question = question

                st.rerun()


# =============================================================================
# Main: Knowledge Base Overview
# =============================================================================

if st.session_state.ingestion_result:

    result = st.session_state.ingestion_result

    st.subheader("🧠 Multimodal Knowledge Base")

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:

        st.metric(
            "📄 Document",
            "Ready",
        )

    with metric2:

        st.metric(
            "🧩 Chunks",
            result.get(
                "chunks_ingested",
                0,
            ),
        )

    with metric3:

        st.metric(
            "🔢 Embeddings",
            result.get(
                "chunks_ingested",
                0,
            ),
        )

    with metric4:

        st.metric(
            "📐 Vector Size",
            "1536",
        )

    st.caption(
        "The NorthStar product guide is represented as "
        "embedded text, table and image knowledge for "
        "semantic retrieval."
    )

    st.divider()


# =============================================================================
# Suggested Questions
# =============================================================================

if not st.session_state.messages:

    st.subheader("💡 Try asking")

    suggestion_col1, suggestion_col2 = st.columns(2)

    with suggestion_col1:

        if st.button(
            "📊 Summarize my March spending",
            use_container_width=True,
        ):

            st.session_state.selected_question = "Summarize my March spending"

            st.rerun()

        if st.button(
            "⭐ How are reward points calculated?",
            use_container_width=True,
        ):

            st.session_state.selected_question = "How are reward points calculated?"

            st.rerun()

    with suggestion_col2:

        if st.button(
            "💰 What are the card fees?",
            use_container_width=True,
        ):

            st.session_state.selected_question = "What are the card fees?"

            st.rerun()

        if st.button(
            "✈️ What is the foreign currency markup?",
            use_container_width=True,
        ):

            st.session_state.selected_question = "What is the foreign currency markup?"

            st.rerun()


# =============================================================================
# Chat History
# =============================================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# =============================================================================
# Determine Current Prompt
# =============================================================================

prompt = st.chat_input("Ask about spending, rewards, fees, benefits or card rules...")

# Allow sidebar/suggestion buttons to populate the chat.
if not prompt and "selected_question" in st.session_state:

    prompt = st.session_state.selected_question

    del st.session_state.selected_question


# =============================================================================
# Process Prompt
# =============================================================================

if prompt:

    # -------------------------------------------------------------------------
    # Save and display user message
    # -------------------------------------------------------------------------

    with st.chat_message("user"):

        st.markdown(prompt)

    add_message(
        "user",
        prompt,
    )

    # -------------------------------------------------------------------------
    # Fast local conversation
    #
    # Greetings, name questions and acknowledgements do NOT go to the
    # backend/LangGraph/LLM.
    # -------------------------------------------------------------------------

    personal_response = handle_personal_conversation(prompt)

    if personal_response:

        with st.chat_message("assistant"):

            st.markdown(personal_response)

        add_message(
            "assistant",
            personal_response,
        )

        st.stop()

    # -------------------------------------------------------------------------
    # Actual Credit Card / RAG Question
    # -------------------------------------------------------------------------

    with st.chat_message("assistant"):

        message_placeholder = st.empty()

        with st.spinner("Analyzing your request..."):

            try:

                payload = {
                    "query": prompt,
                    "thread_id": st.session_state.thread_id,
                    "chat_history": st.session_state.messages,
                }

                response = requests.post(
                    QUERY_ENDPOINT,
                    json=payload,
                    timeout=120,
                )

                # -----------------------------------------------------------------
                # Successful response
                # -----------------------------------------------------------------

                if response.status_code == 200:

                    data = response.json()

                    answer = data.get(
                        "answer",
                        "No answer available.",
                    )

                    # -------------------------------------------------------------
                    # Display Answer
                    # -------------------------------------------------------------

                    message_placeholder.markdown(answer)

                    # -------------------------------------------------------------
                    # Optional citations
                    # -------------------------------------------------------------

                    citations = data.get(
                        "citations",
                        [],
                    )

                    if citations:

                        with st.expander("📚 Sources / Retrieved Knowledge"):

                            for index, citation in enumerate(
                                citations,
                                start=1,
                            ):

                                st.markdown(f"**{index}.** {citation}")

                    # -------------------------------------------------------------
                    # Optional metadata
                    # -------------------------------------------------------------

                    retrieval_info = data.get(
                        "retrieval",
                        None,
                    )

                    if retrieval_info:

                        with st.expander("🔎 Retrieval Details"):

                            st.json(retrieval_info)

                    # -------------------------------------------------------------
                    # Save assistant response
                    # -------------------------------------------------------------

                    add_message(
                        "assistant",
                        answer,
                    )

                # -----------------------------------------------------------------
                # Backend error
                # -----------------------------------------------------------------

                else:

                    error_msg = (
                        f"Backend error "
                        f"({response.status_code})\n\n"
                        f"{response.text}"
                    )

                    message_placeholder.error(error_msg)

                    add_message(
                        "assistant",
                        error_msg,
                    )

            # ---------------------------------------------------------------------
            # Connection error
            # ---------------------------------------------------------------------

            except requests.exceptions.Timeout:

                error_msg = (
                    "The request took too long to complete. " "Please try again."
                )

                message_placeholder.error(error_msg)

                add_message(
                    "assistant",
                    error_msg,
                )

            except requests.exceptions.RequestException as e:

                error_msg = (
                    "Unable to connect to the NorthStar " "AI backend.\n\n" f"{e}"
                )

                message_placeholder.error(error_msg)

                add_message(
                    "assistant",
                    error_msg,
                )

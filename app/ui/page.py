from pathlib import Path

import streamlit as st
import requests
import uuid
import re

# =============================================================================
# Configuration
# =============================================================================

API_BASE_URL = "http://localhost:9000"

UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v1/credit-card/ingestion"
QUERY_ENDPOINT = f"{API_BASE_URL}/api/v1/credit-card/query"


# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="NorthStar AI Spend Assistant",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Minimal / Clean UI Styling
# =============================================================================

st.markdown(
    """
<style>
    /* -----------------------------------------------------------------
       Main page - centered like the reference Regulatory UI
       ----------------------------------------------------------------- */
    .block-container {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding-top: 4rem !important;
        padding-bottom: 6rem !important;
    }

    /* Keep the existing NorthStar heading, only align it */
    h1 {
        text-align: center !important;
        font-size: 2rem !important;
        margin-bottom: 0.35rem !important;
    }

    /* Existing subtitle */
    .block-container > div > div > div > div:first-child p {
        text-align: center;
    }

    /* -----------------------------------------------------------------
       Sidebar - clean, compact, reference-style
       ----------------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        width: 300px !important;
    }

    section[data-testid="stSidebar"] > div {
        padding: 3.5rem 1.25rem 1.5rem 1.25rem !important;
    }

    section[data-testid="stSidebar"] .stFileUploader {
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }

    section[data-testid="stSidebar"] button {
        border-radius: 8px !important;
    }

    /* -----------------------------------------------------------------
       Chat input - same 800px alignment as the main content
       ----------------------------------------------------------------- */
    div[data-testid="stBottomBlockContainer"] {
        width: 100% !important;
    }

    div[data-testid="stBottomBlockContainer"] > div {
        width: 800px !important;
        max-width: calc(100% - 2rem) !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    div[data-testid="stChatInput"] {
        width: 100% !important;
        max-width: 800px !important;
        margin: 0 auto !important;
    }
</style>
""",
    unsafe_allow_html=True,
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

            # Store latest user name
            st.session_state.user_name = name

            # IMPORTANT:
            # Reset LangGraph memory when user changes
            st.session_state.thread_id = str(uuid.uuid4())

            print("USER NAME STORED:", st.session_state.user_name)
            print("NEW THREAD ID:", st.session_state.thread_id)

            return (
                f"Hi {name}! 👋 "
                "Welcome to your Credit Card Spend Summarizer. "
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
         "how are you",
         "greet me"
    ]

    if lower_text in greetings:

        if lower_text in ["how are you", "how are you?"]:
            return (
                "I'm doing great! 😊 "
                "I'm here to help you with your credit card spending, "
                "rewards, fees, benefits, and card-related questions."
            )

        if st.session_state.user_name:

            return (
                f"Hi {st.session_state.user_name}! 👋 "
                "Welcome to your Credit card Spend Assistant. "
                "How can I help you understand your spending, rewards, or card benefits today?"
            )

        return (
            "Hello! 👋 "
            "I can help you analyze credit-card spending, "
            "rewards, fees, benefits and NorthStar card rules."
        )

    # -------------------------------------------------------------------------
# Identity / assistant questions
# -------------------------------------------------------------------------

    assistant_identity_questions = [
        "who are you",
        "what are you",
        "tell me about yourself",
        "introduce yourself",
    ]

    if lower_text in assistant_identity_questions:

            return (
                "I'm NorthStar AI Credit Card Spend Assistant. 🤖 "
                "I can help you with credit card spending analysis, "
                "transactions, rewards, fees, benefits, and card-related information."
            )

    # -------------------------------------------------------------------------
    # Identity questions
    # -------------------------------------------------------------------------

    identity_questions = [
        "who am i",
        "what is my name",
        "do you know my name",
        "who are you talking to"
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
# Sidebar - Upload + Previous Chat History
# =============================================================================

with st.sidebar:

    # -------------------------------------------------------------------------
    # Ingestion Upload
    # -------------------------------------------------------------------------

    st.markdown("📤 Ingestion")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help=(
            "Upload the NorthStar Credit Card Product Guide. "
            "The document will be parsed and indexed."
        ),
    )

    if uploaded_file is not None:

        st.caption(f"📄 {uploaded_file.name}")

        if st.button(
            "Upload",
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

            with st.spinner("Processing document..."):

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

                        st.error(f"Ingestion failed ({response.status_code})")
                        st.code(response.text)

                except requests.exceptions.Timeout:

                    st.error(
                        "The ingestion request timed out. "
                        "The document may still require additional processing time."
                    )

                except requests.exceptions.RequestException as e:

                    st.error("Unable to connect to the backend.")
                    st.code(str(e))

# =============================================================================
# Main Header
# =============================================================================

st.title("💳 Credit Card Spend Summarizer")

st.caption("Ask about spending, rewards, fees, benefits and card rules.")


# =============================================================================
# Chat History
# =============================================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =============================================================================
# Determine Current Prompt
# =============================================================================

prompt = st.chat_input("Ask about spends, rewards, fees, benefits and card rules..")

# Allow sidebar previous-question buttons to populate the chat.
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
    print("========== PROMPT RECEIVED ==========")
    print("PROMPT:", prompt)

    personal_response = handle_personal_conversation(prompt)

    print("========== PERSONAL CHECK ==========")
    print("PERSONAL RESPONSE:", personal_response)


  
    if personal_response:
        
        with st.chat_message("assistant"):

            st.markdown(personal_response)

        add_message(
            "assistant",
            personal_response,
        )

    else:

    # Actual Credit Card / RAG Question

        # ---------------------------------------------------------------------
        # Actual Credit Card / RAG Question
        # ---------------------------------------------------------------------

        with st.chat_message("assistant"):

            message_placeholder = st.empty()

            with st.spinner("Processing your request..."):

                try:

                    payload = {
                        "query": prompt,
                        "thread_id": st.session_state.thread_id,
                        "chat_history": st.session_state.messages[:-1],
                        "customer_name": st.session_state.user_name,
                    }
                    print("PAYLOAD SENT TO BACKEND:", payload)   
                    response = requests.post(
                        QUERY_ENDPOINT,
                        json=payload,
                        timeout=120,
                    )
                    print("STATUS CODE:", response.status_code)
                    print("RESPONSE:", response.text)
                    # -----------------------------------------------------------------
                    # Successful response
                    # -----------------------------------------------------------------

                                        # -----------------------------------------------------------------
                    # Successful response
                    # -----------------------------------------------------------------

                    if response.status_code == 200:

                        data = response.json()

                        answer = data.get(
                            "answer",
                            "No answer available.",
                        )

                        images = data.get(
                            "images",
                            [],
                        )

                        # -------------------------------------------------------------
                        # Display answer OR image
                        # -------------------------------------------------------------

                        if images:

                            # Image question:
                            # Show ONLY the retrieved image.
                            for image in images:

                                image_path = image.get("image_path")

                                if image_path:

                                    st.image(
                                        image_path,
                                        use_container_width=True,
                                    )

                        else:

                            # Normal text question:
                            # Show ONLY the generated answer.
                            message_placeholder.markdown(answer)

                        # -------------------------------------------------------------
                        # Optional citations
                        # -------------------------------------------------------------

                        citations = data.get(
                            "policy_citations",
                            []
                        )

                        if citations:

                            with st.expander("📚 Sources"):

                                for index, citation in enumerate(
                                    citations,
                                    start=1,
                                ):

                                    st.markdown(
                                        f"""
                                        **{index}. {citation.get('source_file')}**

                                        - Page: {citation.get('page_number')}
                                        - Section: {citation.get('section')}
                                        """
                                    )

                        # -------------------------------------------------------------
                        # Optional retrieval metadata
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

                    error_msg = "Unable to connect to the backend. \n \n"
                    print(f"{e}")

                    message_placeholder.error(error_msg)

                    add_message(
                        "assistant",
                        error_msg,
                    )

# =============================================================================
# Previous Chat
# =============================================================================
# Render after prompt processing so the latest submitted question is already
# present in session_state during this same Streamlit run.

with st.sidebar:

    st.divider()
    st.markdown("#### 💬 Previous Chat")

    user_questions = [
        message["content"]
        for message in st.session_state.messages
        if message["role"] == "user"
    ]

    if user_questions:

        for index, question in enumerate(reversed(user_questions[-10:])):

            display_question = question

            if len(display_question) > 70:
                display_question = display_question[:67] + "..."

            if st.button(
                display_question,
                key=f"previous_question_{index}",
                use_container_width=True,
                help=question,
            ):
                st.session_state.selected_question = question
                st.rerun()

    else:
        st.caption("Your previous questions will appear here.")

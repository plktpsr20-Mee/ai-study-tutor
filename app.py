
import os
import hashlib
from io import BytesIO

import streamlit as st
from groq import Groq
from pypdf import PdfReader


# ==================================================
# 1. CONFIGURATION
# ==================================================

MODEL = "openai/gpt-oss-20b"

st.set_page_config(
    page_title="AI Study Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================================================
# 2. PREMIUM DESIGN
# ==================================================

st.markdown("""
<style>

/* Main background */
.stApp {
    background:
        radial-gradient(ellipse at top left, #263b70 0%, transparent 45%),
        radial-gradient(ellipse at bottom right, #35205f 0%, transparent 40%),
        #090e1c;
    color: #f8fafc;
}

/* Main container */
.block-container {
    max-width: 1100px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Headings */
h1, h2, h3 {
    color: #ffffff !important;
    font-weight: 750 !important;
}

/* General text */
p, label {
    color: #d5dcef;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111a30, #0b1020);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(100deg, #635bff, #9333ea);
    color: white !important;
    border: 0;
    border-radius: 12px;
    padding: 0.65rem 1rem;
    font-weight: 650;
    min-height: 45px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(100deg, #817aff, #a855f7);
    border: 0;
    transform: translateY(-2px);
    box-shadow: 0 7px 24px rgba(124, 58, 237, 0.25);
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 15px;
    margin-bottom: 12px;
}

/* Chat input */
[data-testid="stChatInput"] {
    border: 1px solid rgba(139, 92, 246, 0.5);
    border-radius: 16px;
    background: rgba(255,255,255,0.06);
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.045);
    border: 1px dashed rgba(167,139,250,0.5);
    border-radius: 14px;
    padding: 12px;
}

/* Dividers */
hr {
    border-color: rgba(255,255,255,0.12);
}

/* Captions */
[data-testid="stCaptionContainer"] {
    color: #a5b4d4;
}

/* Intro card */
.intro-card {
    padding: 32px;
    border-radius: 22px;
    background: linear-gradient(120deg, #242e59, #542d82);
    border: 1px solid rgba(255,255,255,0.15);
    margin-bottom: 25px;
    box-shadow: 0 15px 45px rgba(0,0,0,0.25);
}

/* Feature cards */
.feature-card {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 18px;
    min-height: 125px;
}

/* Hide Streamlit branding */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# 3. API KEY
# ==================================================

try:
    API_KEY = st.secrets.get(
        "GROQ_API_KEY",
        os.environ.get("GROQ_API_KEY", "")
    )
except Exception:
    API_KEY = os.environ.get("GROQ_API_KEY", "")

if not API_KEY:
    st.error("Groq API key is missing.")
    st.info(
        "Open Streamlit Settings → Secrets and add "
        "GROQ_API_KEY."
    )
    st.stop()


@st.cache_resource
def create_client(api_key):
    return Groq(
        api_key=api_key,
        timeout=60,
        max_retries=2
    )


client = create_client(API_KEY)


# ==================================================
# 4. SESSION STATE
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_digest" not in st.session_state:
    st.session_state.pdf_digest = ""

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ==================================================
# 5. SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown("## 🎓 Study Tutor")

    st.caption("YOUR PERSONAL LEARNING SPACE")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.markdown("### 📚 Study Resources")

    uploaded_file = st.file_uploader(
        "Upload your study notes",
        type=["pdf"],
        help="Upload a PDF to let your tutor study your notes."
    )

    if uploaded_file is not None:

        file_bytes = uploaded_file.getvalue()

        digest = hashlib.sha256(file_bytes).hexdigest()

        if digest != st.session_state.pdf_digest:

            try:
                reader = PdfReader(BytesIO(file_bytes))

                extracted_text = ""

                for page in reader.pages[:20]:
                    extracted_text += (
                        page.extract_text() or ""
                    ) + "\n"

                st.session_state.pdf_text = extracted_text[:10000]
                st.session_state.pdf_digest = digest

                if st.session_state.pdf_text.strip():
                    st.success("PDF uploaded successfully!")
                else:
                    st.warning(
                        "No readable text found. "
                        "Your PDF may contain scanned images."
                    )

            except Exception as error:
                st.error(f"PDF error: {error}")

    if st.session_state.pdf_text:

        st.success("Your notes are ready.")

        if st.button("Remove PDF", use_container_width=True):
            st.session_state.pdf_text = ""
            st.session_state.pdf_digest = ""
            st.rerun()

    st.divider()

    st.markdown("### ⚙️ AI Information")

    st.caption("Model: GPT-OSS 20B")
    st.caption("Provider: Groq")
    st.caption("Interface: Streamlit")


# ==================================================
# 6. INTRODUCTION / HERO SECTION
# ==================================================

st.markdown("""
<div class="intro-card">

    <div style="
        color: #c4b5fd;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 2px;
    ">
        YOUR PERSONAL LEARNING SPACE
    </div>

    <h1 style="
        font-size: clamp(30px, 5vw, 42px);
        margin: 15px 0;
        color: white;
    ">
        🎓 AI Study Tutor
    </h1>

    <p style="
        font-size: 17px;
        color: #e0e7ff;
        line-height: 1.7;
        margin-bottom: 18px;
    ">
        Learn smarter. Understand deeper.
        Prepare better for your exams.
    </p>

    <div style="
        display: inline-block;
        padding: 8px 15px;
        border-radius: 30px;
        background: rgba(255,255,255,0.12);
        color: #ddd6fe;
        font-size: 13px;
    ">
        ✨ Your AI-powered study companion
    </div>

</div>
""", unsafe_allow_html=True)


# ==================================================
# 7. FEATURE CARDS
# ==================================================

st.markdown("### What would you like to do today?")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>📖 Learn</h3>
        <p>Understand difficult concepts
        with simple explanations.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📝 Revise</h3>
        <p>Summarize your notes and
        prepare for examinations.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>🧠 Practice</h3>
        <p>Test your knowledge with
        interactive quizzes.</p>
    </div>
    """, unsafe_allow_html=True)


st.write("")
st.divider()


# ==================================================
# 8. QUICK ACTIONS
# ==================================================

st.markdown("### ⚡ Quick Study Actions")

col1, col2 = st.columns(2)

with col1:

    if st.button(
        "📝 Summarize My Notes",
        use_container_width=True
    ):

        if st.session_state.pdf_text:
            st.session_state.pending_prompt = (
                "Summarize my uploaded notes. Explain all "
                "important concepts in simple English. "
                "Include important exam definitions and points."
            )
        else:
            st.session_state.pending_prompt = (
                "Help me summarize a topic. First ask me "
                "which subject and topic I want to study."
            )

        st.rerun()


with col2:

    if st.button(
        "❓ Start a Quiz",
        use_container_width=True
    ):

        if st.session_state.pdf_text:
            st.session_state.pending_prompt = (
                "Create a 5-question quiz based on my uploaded "
                "notes. Ask one question at a time and wait "
                "for my answer before continuing."
            )
        else:
            st.session_state.pending_prompt = (
                "Start a study quiz. First ask me which "
                "subject and topic I want to practice."
            )

        st.rerun()


# ==================================================
# 9. CHAT HISTORY
# ==================================================

st.divider()

st.markdown("### 💬 Chat with Your AI Tutor")

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ==================================================
# 10. CHAT INPUT
# ==================================================

prompt = st.chat_input(
    "Ask anything about your studies..."
)

if st.session_state.pending_prompt:

    prompt = st.session_state.pending_prompt

    st.session_state.pending_prompt = None


# ==================================================
# 11. AI RESPONSE
# ==================================================

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = """
You are an expert AI study tutor.

Your purpose is to help students learn effectively.

TEACHING RULES:

1. Explain concepts in simple and clear English.
2. Teach step by step.
3. Give practical real-life examples.
4. Use headings and bullet points.
5. Include important definitions for exams.
6. Never invent facts.
7. If a student does not understand, explain differently.
8. Be friendly, patient and encouraging.
9. For quizzes, ask one question at a time.
10. Give detailed answers when requested.
11. Help students understand instead of simply memorizing.
"""

    if st.session_state.pdf_text:

        system_prompt += """

The student has uploaded study notes.

Use these notes as the main reference
when answering questions related to them.

UPLOADED NOTES:

""" + st.session_state.pdf_text

    recent_messages = st.session_state.messages[-8:]

    api_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ] + recent_messages

    with st.chat_message("assistant"):

        with st.spinner("✨ Your AI tutor is thinking..."):

            try:

                response = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages
                )

                answer = response.choices[0].message.content

                if not answer:
                    answer = (
                        "I couldn't generate a response. "
                        "Please try again."
                    )

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:

                status = getattr(error, "status_code", None)

                if status == 401:

                    st.error(
                        "Invalid API key. Check your "
                        "Groq API key in Streamlit Secrets."
                    )

                elif status == 404:

                    st.error(
                        "Model not found. Check the "
                        "Groq model ID."
                    )

                elif status == 429:

                    st.error(
                        "Groq usage limit reached. "
                        "Please wait and try again."
                    )

                elif status and status >= 500:

                    st.error(
                        "Groq service is temporarily unavailable. "
                        "Please try again later."
                    )

                else:

                    st.error(f"Something went wrong: {error}")

                st.info(
                    "Your question is saved in the chat. "
                    "You can try sending it again."
                )


# ==================================================
# 12. FOOTER
# ==================================================

st.divider()

st.markdown("""
<div style="
    text-align: center;
    padding: 15px;
    color: #94a3b8;
    font-size: 13px;
">
    Built with ❤️ for smarter learning
    <br><br>
    AI Study Tutor · Powered by Groq
</div>
""", unsafe_allow_html=True)

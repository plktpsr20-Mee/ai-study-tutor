
import os
import hashlib
from io import BytesIO

import streamlit as st
from groq import Groq
from pypdf import PdfReader

# =====================================
# CONFIGURATION
# =====================================

MODEL = "openai/gpt-oss-20b"

st.set_page_config(
    page_title="AI Study Tutor",
    page_icon="🎓",
    layout="centered"
)

# =====================================
# DESIGN
# =====================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #101827, #172554);
}
h1, h2, h3, p, label {
    color: white;
}
.stChatMessage {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# API KEY
# =====================================

try:
    API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    API_KEY = os.environ.get("GROQ_API_KEY", "")

if not API_KEY:
    st.error("Groq API key is missing.")
    st.info(
        "Open your Streamlit app settings, go to Secrets, "
        "and add GROQ_API_KEY."
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

# =====================================
# SESSION STATE
# =====================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_digest" not in st.session_state:
    st.session_state.pdf_digest = ""

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# =====================================
# SIDEBAR
# =====================================

with st.sidebar:
    st.title("📚 Study Tools")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("Upload Your Notes")

    uploaded_file = st.file_uploader(
        "Upload a PDF",
        type=["pdf"]
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        digest = hashlib.sha256(file_bytes).hexdigest()

        if digest != st.session_state.pdf_digest:
            try:
                reader = PdfReader(BytesIO(file_bytes))
                extracted_text = ""

                for page in reader.pages[:20]:
                    extracted_text += (page.extract_text() or "") + "\n"

                st.session_state.pdf_text = extracted_text[:10000]
                st.session_state.pdf_digest = digest

                if st.session_state.pdf_text.strip():
                    st.success("PDF loaded successfully!")
                else:
                    st.warning(
                        "No readable text found. "
                        "This may be a scanned PDF."
                    )

            except Exception as error:
                st.error(f"PDF error: {error}")

    if st.session_state.pdf_text:
        st.caption("Your notes are ready.")

        if st.button("Remove PDF", use_container_width=True):
            st.session_state.pdf_text = ""
            st.session_state.pdf_digest = ""
            st.rerun()

# =====================================
# MAIN PAGE
# =====================================

st.title("🎓 AI Study Tutor")

st.write(
    "Learn smarter. Understand concepts. "
    "Prepare for your exams."
)

st.caption(f"AI Model: {MODEL}")

# =====================================
# PRESET BUTTONS
# =====================================

col1, col2 = st.columns(2)

with col1:
    if st.button("📝 Summarize Notes", use_container_width=True):
        st.session_state.pending_prompt = (
            "Summarize my uploaded notes. Explain the important "
            "concepts in simple English and include exam points."
        )
        st.rerun()

with col2:
    if st.button("❓ Quiz Me", use_container_width=True):
        st.session_state.pending_prompt = (
            "Create a 5-question quiz based on my uploaded notes. "
            "Ask one question at a time and wait for my answer."
        )
        st.rerun()

# =====================================
# DISPLAY CHAT HISTORY
# =====================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =====================================
# CHAT INPUT
# =====================================

prompt = st.chat_input("Ask your study question...")

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

# =====================================
# AI RESPONSE
# =====================================

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = """
You are an expert AI study tutor.

Your job is to help students understand their subjects.

Rules:
1. Explain everything in simple English.
2. Teach concepts step by step.
3. Give practical and real-life examples.
4. Use headings and bullet points.
5. Include important definitions for exams.
6. Do not invent information.
7. If a student does not understand, explain it differently.
8. Be friendly, patient and encouraging.
9. For quizzes, ask one question at a time.
10. Give detailed answers when the student asks for detail.
"""

    if st.session_state.pdf_text:
        system_prompt += """

The student has uploaded study notes.
Use the following notes as the main reference
when answering questions about those notes:

""" + st.session_state.pdf_text

    recent_messages = st.session_state.messages[-8:]

    api_messages = [
        {"role": "system", "content": system_prompt}
    ] + recent_messages

    with st.chat_message("assistant"):

        with st.spinner("Your AI tutor is thinking..."):

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages
                )

                answer = response.choices[0].message.content

                if not answer:
                    answer = "The AI returned an empty response. Please try again."

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:

                status = getattr(error, "status_code", None)

                if status == 401:
                    st.error(
                        "Invalid API key. Check your Groq API key "
                        "in Streamlit Secrets."
                    )

                elif status == 404:
                    st.error(
                        "Model not found. Check the model ID "
                        "in the official Groq model list."
                    )

                elif status == 429:
                    st.error(
                        "Groq rate limit reached. Wait a little "
                        "and try again."
                    )

                elif status and status >= 500:
                    st.error(
                        "Groq server is temporarily unavailable. "
                        "Please try again later."
                    )

                else:
                    st.error(f"API error: {error}")

                st.info(
                    "Your question is still saved in the chat. "
                    "You can send it again when the service is ready."
                )

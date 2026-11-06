import streamlit as st
import pypdf
from openai import OpenAI
from io import BytesIO

# Page Config
st.set_page_config(page_title="GPT Study Tutor", page_icon="⚡", layout="wide")

# --- Glassmorphism Custom CSS Injection ---
glassy_css = """
<style>
.stApp {
    background: linear-gradient(-45deg, #0f172a, #1e1b4b, #311042, #0284c7);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
    color: #ffffff;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
}
.stChatMessage {
    background: rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 16px !important;
    padding: 15px !important;
    margin-bottom: 12px !important;
}
.stTextInput > div > div > input, .stFileUploader section {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: white !important;
    border-radius: 12px !important;
}
</style>
"""
st.markdown(glassy_css, unsafe_allow_html=True)

st.title("⚡ GPT Study Tutor")
st.markdown("Powered by OpenAI's stable, high-reliability server infrastructure.")

with st.sidebar:
    st.header("⚙️ Configuration")
    openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    st.divider()
    uploaded_file = st.file_uploader("Upload Notes (PDF)", type=["pdf"])

@st.cache_data
def extract_pdf_text(file_bytes):
    reader = pypdf.PdfReader(BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

context_text = ""
if uploaded_file:
    context_text = extract_pdf_text(uploaded_file.read())
    st.sidebar.success(f"Loaded: {uploaded_file.name}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask a question or request a summary...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        if not openai_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
        else:
            with st.spinner("Processing request..."):
                try:
                    client = OpenAI(api_key=openai_key)
                    messages_payload = [
                        {"role": "system", "content": f"You are a helpful college tutor. Context Material: {context_text if context_text else 'None'}"},
                        {"role": "user", "content": user_input}
                    ]
                    
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages_payload
                    )
                    
                    ai_response = res.choices[0].message.content
                    st.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                except Exception as err:
                    st.error(f"Error: {str(err)}")

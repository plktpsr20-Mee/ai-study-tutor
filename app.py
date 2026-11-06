import streamlit as st
import pypdf
from google import genai
from io import BytesIO

# Page Config
st.set_page_config(page_title="Gemini Flash Study Tutor", page_icon="⚡", layout="wide")

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
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
}

.stTextInput > div > div > input, .stFileUploader section {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: white !important;
    border-radius: 12px !important;
}

.stButton > button {
    background: rgba(255, 255, 255, 0.15) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    color: white !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    background: rgba(255, 255, 255, 0.3) !important;
    transform: translateY(-2px);
}
</style>
"""
st.markdown(glassy_css, unsafe_allow_html=True)

# Title Header
st.title("⚡ Gemini Flash Study Tutor")
st.markdown("Your lightning-fast, single-model AI study companion powered by Google Gemini.")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="Paste free key here...")
    st.caption("Get a free key instantly at [Google AI Studio](https://aistudio.google.com/)")
    
    st.divider()
    st.subheader("📄 Study Material")
    uploaded_file = st.file_uploader("Upload Notes (PDF)", type=["pdf"])

# --- Cached PDF Text Extraction ---
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

# --- Chat Interface State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask a question, request a summary, or type 'Quiz me'...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        if not gemini_key:
            st.error("Please enter your Gemini API key in the sidebar to begin.")
        else:
            with st.spinner("Thinking at lightning speed..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    
                    # Single-model prompt construction
                    prompt_content = f"""
                    You are an expert, friendly college study tutor. Explain concepts simply, provide bullet points for clarity, and quiz the user when requested.
                    
                    Uploaded Document Context:
                    {context_text if context_text else 'No specific document uploaded yet. Answer based on general academic knowledge.'}
                    
                    User Request: {user_input}
                    """
                    
                    res = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt_content
                    )
                    
                    ai_response = res.text
                    st.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    
                except Exception as err:
                    st.error(f"Error: {str(err)}. Please verify your API key.")
                    

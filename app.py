import streamlit as st
import pypdf
from google import genai
from openai import OpenAI

# Page Config
st.set_page_config(page_title="Glassy AI Study Tutor", page_icon="🔮", layout="wide")

# --- Glassmorphism Custom CSS Injection ---
glassy_css = """
<style>
/* Gradient Animated Background */
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

/* Glass Panels & Sidebar */
[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* Glass Cards for Chat Messages */
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

/* Glass Inputs & Buttons */
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

# Title
st.title("🔮 Glassy Dual-Model AI Tutor")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    model_choice = st.radio("AI Engine", ["Gemini (Flash)", "GPT-4o-mini"])
    
    st.subheader("🔑 API Key")
    gemini_key = st.text_input("Gemini API Key", type="password")
    openai_key = st.text_input("OpenAI API Key", type="password")
    
    st.subheader("📄 Material")
    uploaded_file = st.file_uploader("Upload Notes (PDF)", type=["pdf"])

# --- PDF Extract Function ---
def extract_pdf_text(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

context_text = ""
if uploaded_file:
    context_text = extract_pdf_text(uploaded_file)
    st.success(f"Loaded: {uploaded_file.name}")

# --- Chat State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask a question, request an explanation, or type 'Quiz me'...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    system_prompt = f"""
    You are an expert interactive college tutor. 
    Use the provided study materials to explain concepts simply, quiz the user, evaluate their answers, 
    and explicitly correct them when they give wrong or incomplete answers.
    
    Provided Study Material:
    {context_text if context_text else 'No document uploaded yet.'}
    """

    full_payload = f"{system_prompt}\n\nUser Question: {user_input}"
    ai_response = ""

    with st.chat_message("assistant"):
        try:
            if "Gemini" in model_choice:
                if not gemini_key:
                    st.error("Please enter your Gemini API key in the sidebar.")
                else:
                    client = genai.Client(api_key=gemini_key)
                    res = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=full_payload
                    )
                    ai_response = res.text

            elif "GPT" in model_choice:
                if not openai_key:
                    st.error("Please enter your OpenAI API key in the sidebar.")
                else:
                    client = OpenAI(api_key=openai_key)
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": full_payload}]
                    )
                    ai_response = res.choices[0].message.content

            if ai_response:
                st.write(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
        except Exception as err:
            st.error(f"Execution Error: {str(err)}")

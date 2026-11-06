import streamlit as st
import pypdf
from groq import Groq
from io import BytesIO

# Page Config
st.set_page_config(page_title="Groq Glassy Study Tutor", page_icon="⚡", layout="wide")

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
    width: 100%;
}

.stButton > button:hover {
    background: rgba(255, 255, 255, 0.3) !important;
    transform: translateY(-2px);
}
</style>
"""
st.markdown(glassy_css, unsafe_allow_html=True)

# Title Header
st.title("⚡ Groq-Powered Study Tutor")
st.markdown("Blazing-fast, 100% free AI study assistant powered by Llama.")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.caption("Get a free key instantly at [Groq Console](https://console.groq.com/)")
    
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

# --- Quick-Action Preset Buttons ---
st.write("") 
col1, col2 = st.columns(2)
preset_input = None

with col1:
    if st.button("📝 Summarize Document"):
        preset_input = "Please provide a clear, concise summary of the uploaded document, highlighting key concepts and takeaways."
with col2:
    if st.button("❓ Quiz Me"):
        preset_input = "Please generate a 3-question practice quiz based on the uploaded document to test my understanding."

# Handle Chat Input or Preset Trigger
user_input = st.chat_input("Ask a question, request a summary, or type 'Quiz me'...")
final_query = preset_input if preset_input else user_input

if final_query:
    st.session_state.messages.append({"role": "user", "content": final_query})
    with st.chat_message("user"):
        st.write(final_query)

    with st.chat_message("assistant"):
        if not groq_key:
            st.error("Please enter your Groq API key in the sidebar to begin.")
        else:
            with st.spinner("Generating response at lightning speed..."):
                try:
                    client = Groq(api_key=groq_key)
                    
                    messages_payload = [
                        {
                            "role": "system", 
                            "content": f"You are an expert, friendly college study tutor. Explain concepts simply and use bullet points.\n\nContext Material: {context_text if context_text else 'None provided.'}"
                        },
                        {
                            "role": "user", 
                            "content": final_query
                        }
                    ]
                    
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",  # Verified stable production model
                        messages=messages_payload,
                        temperature=0.7
                    )
                    
                    ai_response = response.choices[0].message.content
                    st.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    
                except Exception as err:
                    st.error(f"Error: {str(err)}. Please verify your Groq API key.")

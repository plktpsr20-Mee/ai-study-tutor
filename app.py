import streamlit as st
import pypdf
from google import genai
from openai import OpenAI

# Page Layout
st.set_page_config(page_title="AI Study Tutor", page_icon="📚", layout="wide")
st.title("📚 Dual-Model AI Study Tutor")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Settings & Setup")
    model_choice = st.radio("Select AI Model", ["Gemini (Flash)", "GPT-4o-mini"])
    
    st.markdown("---")
    st.subheader("🔑 Enter API Keys")
    gemini_key = st.text_input("Gemini API Key", type="password", help="Get free from Google AI Studio")
    openai_key = st.text_input("OpenAI API Key", type="password", help="Get from OpenAI Platform")
    
    st.markdown("---")
    uploaded_file = st.file_uploader("📄 Upload Study Material (PDF)", type=["pdf"])

# --- PDF Text Processing ---
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
    st.success(f"Loaded context from: {uploaded_file.name}")

# --- Chat Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- User Input & AI Execution ---
user_input = st.chat_input("Ask a question, request an explanation, or type 'Quiz me'...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Master prompt telling the model to act strictly as a tutor
    system_prompt = f"""
    You are an expert interactive college tutor. 
    Use the provided study materials to explain concepts simply, quiz the user, evaluate their answers, 
    and explicitly correct them when they give wrong or incomplete answers.
    
    Provided Study Material:
    {context_text if context_text else 'No document uploaded yet. Advise user to upload a PDF if needed.'}
    """

    full_payload = f"{system_prompt}\n\nUser Question/Response: {user_input}"
    ai_response = ""

    with st.chat_message("assistant"):
        try:
            if "Gemini" in model_choice:
                if not gemini_key:
                    st.error("Please enter your Gemini API key in the sidebar.")
                else:
                    client = genai.Client(api_key=gemini_key)
                    res = client.models.generate_content(
                        model='gemini-2.5-flash',
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

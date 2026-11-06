import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
from io import BytesIO

import streamlit as st
from groq import Groq
from pypdf import PdfReader

# ==================================================
# 1. CONFIGURATION
# ==================================================
MODEL = "openai/gpt-oss-20b"
DB_PATH = "chat_history.db"

st.set_page_config(
    page_title="AI Study Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================================================
# 2. DATABASE: PERSISTENT CHAT HISTORY
# ==================================================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        # Safe migration for databases created by the previous version.
        columns = [row[1] for row in conn.execute("PRAGMA table_info(chats)").fetchall()]
        if "folder_id" not in columns:
            conn.execute("ALTER TABLE chats ADD COLUMN folder_id INTEGER")


def create_chat(title="New chat", folder_id=None):
    chat_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chats (id, title, created_at, updated_at, folder_id) VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, now, now, folder_id),
        )
    return chat_id


def list_chats():
    with get_db() as conn:
        return conn.execute(
            "SELECT id, title, updated_at FROM chats ORDER BY updated_at DESC"
        ).fetchall()


def list_folders():
    with get_db() as conn:
        return conn.execute("SELECT id, name FROM folders ORDER BY name COLLATE NOCASE").fetchall()


def create_folder(name):
    clean = " ".join(name.strip().split())[:32]
    if not clean:
        return False
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO folders (name, created_at) VALUES (?, ?)",
                (clean, datetime.now().isoformat(timespec="seconds")),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def rename_folder(folder_id, name):
    clean = " ".join(name.strip().split())[:32]
    if not clean:
        return False
    try:
        with get_db() as conn:
            conn.execute("UPDATE folders SET name = ? WHERE id = ?", (clean, folder_id))
        return True
    except sqlite3.IntegrityError:
        return False


def delete_folder(folder_id):
    # Conversations are kept and moved back to the unfiled section.
    with get_db() as conn:
        conn.execute("UPDATE chats SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
        conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))


def move_chat(chat_id, folder_id):
    with get_db() as conn:
        conn.execute("UPDATE chats SET folder_id = ? WHERE id = ?", (folder_id, chat_id))


def search_chats(term, folder_id=None):
    term = f"%{term.strip()}%"
    sql = """
        SELECT DISTINCT c.id, c.title, c.updated_at, c.folder_id
        FROM chats c LEFT JOIN messages m ON m.chat_id = c.id
        WHERE (c.title LIKE ? OR m.content LIKE ?)
    """
    params = [term, term]
    if folder_id == "unfiled":
        sql += " AND c.folder_id IS NULL"
    elif folder_id is not None:
        sql += " AND c.folder_id = ?"
        params.append(folder_id)
    sql += " ORDER BY c.updated_at DESC"
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def load_messages(chat_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_message(chat_id, role, content):
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, now),
        )
        conn.execute(
            "UPDATE chats SET updated_at = ? WHERE id = ?",
            (now, chat_id),
        )


def rename_chat(chat_id, title):
    title = title.strip()[:70]
    if title:
        with get_db() as conn:
            conn.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))


def delete_chat(chat_id):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


def set_chat_title_from_prompt(chat_id, prompt):
    title = " ".join(prompt.strip().split())[:42]
    if len(prompt.strip()) > 42:
        title += "…"
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row["total"] <= 1:
            conn.execute(
                "UPDATE chats SET title = ? WHERE id = ? AND title = 'New chat'",
                (title or "New chat", chat_id),
            )


init_db()

# ==================================================
# 3. PREMIUM GLASS DESIGN
# ==================================================
st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at 12% 8%, rgba(59,130,246,.20), transparent 30%),
        radial-gradient(circle at 88% 20%, rgba(147,51,234,.20), transparent 32%),
        radial-gradient(circle at 50% 100%, rgba(34,211,238,.10), transparent 38%),
        #080d1c;
    color: #f8fafc;
}
.block-container {
    max-width: 1120px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
h1, h2, h3 { color: #fff !important; font-weight: 750 !important; }
p, label { color: #d5dcef; }
[data-testid="stSidebar"] {
    background: rgba(9, 15, 32, .82);
    border-right: 1px solid rgba(255,255,255,.10);
}
.stButton > button {
    border: 1px solid rgba(255,255,255,.13);
    border-radius: 15px;
    min-height: 43px;
    color: white;
    background: linear-gradient(110deg, rgba(99,91,255,.88), rgba(147,51,234,.88));
    transition: .2s ease;
}
.stButton > button:hover {
    border-color: rgba(167,139,250,.8);
    transform: translateY(-1px);
    box-shadow: 0 8px 25px rgba(99,91,255,.22);
}
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.065);
    border: 1px solid rgba(255,255,255,.11);
    border-radius: 19px;
    padding: 15px;
    margin-bottom: 12px;
    backdrop-filter: blur(18px);
}
[data-testid="stChatInput"] {
    border: 1px solid rgba(139,92,246,.55);
    border-radius: 18px;
    background: rgba(255,255,255,.07);
}
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,.045);
    border: 1px dashed rgba(167,139,250,.5);
    border-radius: 15px;
    padding: 12px;
}
.intro-card {
    padding: 30px;
    border-radius: 25px;
    background: linear-gradient(120deg, rgba(36,46,89,.64), rgba(84,45,130,.48));
    border: 1px solid rgba(255,255,255,.18);
    margin-bottom: 24px;
    box-shadow: 0 18px 55px rgba(0,0,0,.20);
    backdrop-filter: blur(22px);
}
.feature-card {
    background: rgba(255,255,255,.065);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 20px;
    padding: 18px;
    min-height: 125px;
    backdrop-filter: blur(18px);
}
.sidebar-brand {
    padding: 14px 13px;
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(59,130,246,.20), rgba(147,51,234,.18));
    margin-bottom: 14px;
}
.sidebar-hint { color: #94a3b8; font-size: 11px; letter-spacing: 1.2px; }
.history-label {
    color: #a5b4fc;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin: 12px 0 8px 0;
}
hr { border-color: rgba(255,255,255,.12); }
[data-testid="stCaptionContainer"] { color: #a5b4d4; }
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ==================================================
# 4. API KEY
# ==================================================
try:
    API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
except Exception:
    API_KEY = os.environ.get("GROQ_API_KEY", "")

if not API_KEY:
    st.error("Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()


@st.cache_resource
def create_client(api_key):
    return Groq(api_key=api_key, timeout=60, max_retries=2)


client = create_client(API_KEY)

# ==================================================
# 5. SESSION STATE
# ==================================================
if "active_chat_id" not in st.session_state:
    existing = list_chats()
    st.session_state.active_chat_id = existing[0]["id"] if existing else create_chat()

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(st.session_state.active_chat_id)

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "pdf_digest" not in st.session_state:
    st.session_state.pdf_digest = ""
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "rename_value" not in st.session_state:
    st.session_state.rename_value = ""
if "history_search" not in st.session_state:
    st.session_state.history_search = ""

# ==================================================
# 6. SIDEBAR: SEARCHABLE HISTORY + FOLDERS
# ==================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div style="font-size:25px">🎓</div>
      <div style="font-size:19px;font-weight:800;color:white">AI Study Tutor</div>
      <div class="sidebar-hint">YOUR PERSONAL LEARNING SPACE</div>
    </div>
    """, unsafe_allow_html=True)

    folders = list_folders()
    folder_lookup = {f["id"]: f["name"] for f in folders}

    if st.button("＋  New chat", use_container_width=True, key="new_chat"):
        st.session_state.active_chat_id = create_chat()
        st.session_state.messages = []
        st.session_state.pending_prompt = None
        st.rerun()

    st.markdown('<div class="history-label">SEARCH CONVERSATIONS</div>', unsafe_allow_html=True)
    search_term = st.text_input(
        "Search", placeholder="Find a topic or message...", label_visibility="collapsed",
        key="history_search"
    )
    folder_options = {"All conversations": None, "Unfiled": "unfiled"}
    folder_options.update({f"📁 {f['name']}": f["id"] for f in folders})
    selected_folder_label = st.selectbox(
        "Filter by folder", list(folder_options.keys()), label_visibility="collapsed",
        key="folder_filter"
    )
    selected_folder_id = folder_options[selected_folder_label]
    chats = search_chats(search_term, selected_folder_id)

    st.markdown('<div class="history-label">YOUR CHATS</div>', unsafe_allow_html=True)
    if not chats:
        st.caption("No matching conversations yet.")
    for chat in chats:
        is_active = chat["id"] == st.session_state.active_chat_id
        label = ("●  " if is_active else "◦  ") + chat["title"]
        if st.button(label, key=f"open_{chat['id']}", use_container_width=True, type="secondary"):
            st.session_state.active_chat_id = chat["id"]
            st.session_state.messages = load_messages(chat["id"])
            st.session_state.pending_prompt = None
            st.rerun()
        if chat["folder_id"] in folder_lookup:
            st.caption(f"　📁 {folder_lookup[chat['folder_id']]}")

    st.divider()
    with st.expander("📁 Organize folders"):
        with st.form("create_folder_form", clear_on_submit=True):
            folder_name = st.text_input("New folder name", placeholder="e.g. Computer Architecture")
            create_folder_clicked = st.form_submit_button("Create folder", use_container_width=True)
        if create_folder_clicked:
            if create_folder(folder_name):
                st.success("Folder created.")
                st.rerun()
            else:
                st.warning("Enter a name or use a different folder name.")

        if folders:
            folder_manage = st.selectbox(
                "Choose folder to manage",
                options=[f["id"] for f in folders],
                format_func=lambda fid: folder_lookup.get(fid, "Folder"),
                key="folder_manage_select",
            )
            folder_new_name = st.text_input("Rename folder", key="folder_rename_text")
            if st.button("Save folder name", use_container_width=True):
                if rename_folder(folder_manage, folder_new_name):
                    st.success("Folder renamed.")
                    st.rerun()
                else:
                    st.warning("Enter a name that is not already in use.")
            if st.button("Delete folder (keep chats)", use_container_width=True, key="delete_folder"):
                delete_folder(folder_manage)
                st.rerun()
            st.caption("Deleting a folder keeps its conversations and moves them to Unfiled.")
        else:
            st.caption("Create folders to group subjects and projects.")

    current_chat = next((c for c in list_chats() if c["id"] == st.session_state.active_chat_id), None)
    with st.expander("⚙️ Current conversation"):
        current_title = current_chat["title"] if current_chat else ""
        new_title = st.text_input("Conversation name", value=current_title, key="rename_input", max_chars=70)
        if st.button("Save name", use_container_width=True):
            rename_chat(st.session_state.active_chat_id, new_title)
            st.rerun()

        move_options = {"Unfiled": None}
        move_options.update({f["name"]: f["id"] for f in folders})
        current_folder_id = current_chat["folder_id"] if current_chat else None
        current_folder_label = next((name for name, fid in move_options.items() if fid == current_folder_id), "Unfiled")
        chosen_folder = st.selectbox(
            "Move conversation to", list(move_options.keys()),
            index=list(move_options.keys()).index(current_folder_label), key="move_chat_folder"
        )
        if st.button("Move conversation", use_container_width=True):
            move_chat(st.session_state.active_chat_id, move_options[chosen_folder])
            st.rerun()

        st.divider()
        if st.button("🗑️ Delete this conversation", use_container_width=True, key="delete_current"):
            delete_chat(st.session_state.active_chat_id)
            remaining = list_chats()
            st.session_state.active_chat_id = remaining[0]["id"] if remaining else create_chat()
            st.session_state.messages = load_messages(st.session_state.active_chat_id)
            st.rerun()

    st.divider()
    st.markdown("### 📚 Study Resources")
    uploaded_file = st.file_uploader(
        "Upload your study notes", type=["pdf"],
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
                    extracted_text += (page.extract_text() or "") + "\n"
                st.session_state.pdf_text = extracted_text[:10000]
                st.session_state.pdf_digest = digest
                if st.session_state.pdf_text.strip():
                    st.success("PDF uploaded successfully!")
                else:
                    st.warning("No readable text found. This PDF may contain scanned images.")
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
    st.caption("History: SQLite")

# ==================================================
# 7. INTRODUCTION
# ==================================================
st.markdown("""
<div class="intro-card">
  <div style="color:#c4b5fd;font-size:12px;font-weight:800;letter-spacing:2px;">
    YOUR PERSONAL LEARNING SPACE
  </div>
  <h1 style="font-size:clamp(30px,5vw,42px);margin:13px 0;color:white;">
    🎓 AI Study Tutor
  </h1>
  <p style="font-size:17px;color:#e0e7ff;line-height:1.7;margin-bottom:16px;">
    Learn smarter. Understand deeper. Prepare better for your exams.
  </p>
  <span style="display:inline-block;padding:8px 15px;border-radius:30px;
  background:rgba(255,255,255,.12);color:#ddd6fe;font-size:13px;">
    ✨ Your AI-powered study companion
  </span>
</div>
""", unsafe_allow_html=True)

# ==================================================
# 8. FEATURE CARDS + QUICK ACTIONS
# ==================================================
st.markdown("### What would you like to do today?")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="feature-card"><h3>📖 Learn</h3><p>Understand difficult concepts with simple explanations.</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="feature-card"><h3>📝 Revise</h3><p>Summarize your notes and prepare for examinations.</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="feature-card"><h3>🧠 Practice</h3><p>Test your knowledge with interactive quizzes.</p></div>', unsafe_allow_html=True)

st.write("")
st.divider()
st.markdown("### ⚡ Quick Study Actions")
col1, col2 = st.columns(2)

with col1:
    if st.button("📝 Summarize My Notes", use_container_width=True):
        st.session_state.pending_prompt = (
            "Summarize my uploaded notes. Explain all important concepts in simple English. "
            "Include important exam definitions and points."
            if st.session_state.pdf_text
            else "Help me summarize a topic. First ask me which subject and topic I want to study."
        )
        st.rerun()

with col2:
    if st.button("❓ Start a Quiz", use_container_width=True):
        st.session_state.pending_prompt = (
            "Create a 5-question quiz based on my uploaded notes. Ask one question at a time "
            "and wait for my answer before continuing."
            if st.session_state.pdf_text
            else "Start a study quiz. First ask me which subject and topic I want to practice."
        )
        st.rerun()

# ==================================================
# 9. CHAT DISPLAY
# ==================================================
st.divider()
st.markdown("### 💬 Chat with Your AI Tutor")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.messages:
    export_lines = [f"# {current_chat['title'] if current_chat else 'Study conversation'}", ""]
    for item in st.session_state.messages:
        speaker = "You" if item["role"] == "user" else "AI Study Tutor"
        export_lines.extend([f"## {speaker}", item["content"], ""])
    st.download_button(
        "⬇️ Export this chat as Markdown", "\n".join(export_lines),
        file_name="study_conversation.md", mime="text/markdown"
    )

# ==================================================
# 10. CHAT INPUT + QUICK ACTION PROMPTS
# ==================================================
prompt = st.chat_input("Ask anything about your studies...")
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

# ==================================================
# 11. AI RESPONSE + SAVE TO DATABASE
# ==================================================
if prompt:
    save_message(st.session_state.active_chat_id, "user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    set_chat_title_from_prompt(st.session_state.active_chat_id, prompt)

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
        system_prompt += (
            "\nThe student has uploaded study notes. Use these notes as the main reference "
            "when answering questions related to them.\n\nUPLOADED NOTES:\n"
            + st.session_state.pdf_text
        )

    api_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages[-8:]

    with st.chat_message("assistant"):
        with st.spinner("✨ Your AI tutor is thinking..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                )
                answer = response.choices[0].message.content or (
                    "I couldn't generate a response. Please try again."
                )
                st.markdown(answer)
                save_message(st.session_state.active_chat_id, "assistant", answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as error:
                status = getattr(error, "status_code", None)
                if status == 401:
                    st.error("Invalid API key. Check your Groq API key in Streamlit Secrets.")
                elif status == 404:
                    st.error("Model not found. Check the Groq model ID.")
                elif status == 429:
                    st.error("Groq usage limit reached. Please wait and try again.")
                elif status and status >= 500:
                    st.error("Groq service is temporarily unavailable. Please try again later.")
                else:
                    st.error(f"Something went wrong: {error}")
                st.info("Your question is saved in this conversation. You can try sending it again.")

# ==================================================
# 12. FOOTER
# ==================================================
st.divider()
st.markdown("""
<div style="text-align:center;padding:15px;color:#94a3b8;font-size:13px;">
  Built with ❤️ for smarter learning<br><br>
  AI Study Tutor · Powered by Groq · Searchable history
</div>
""", unsafe_allow_html=True)

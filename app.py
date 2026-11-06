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

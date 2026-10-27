import streamlit as st
from github_agent.main import ask_github_mcp_agent


st.set_page_config(
    page_title="GitHub MCP Agent",
    page_icon="🐙",
)


st.title("🐙 GitHub MCP Agent")
st.caption("Paste a GitHub repository once, then chat with it.")

# -------------------------------------------------------
# Session State
# -------------------------------------------------------

if "history" not in st.session_state:
    st.session_state.history = []

if "repo" not in st.session_state:
    st.session_state.repo = ""

if "logs" not in st.session_state:
    st.session_state.logs = []






@st.dialog("🪵 State Logs", width="large")
def show_logs_dialog():
    st.code("\n\n".join(st.session_state.logs), language="text")

# -------------------------------------------------------
# Sidebar
# -------------------------------------------------------

with st.sidebar:

    st.subheader("Repository")

    repo_input = st.text_input(
        "GitHub Repository",
        value=st.session_state.repo,
        placeholder="github/github-mcp-server",
        help="Example: github/github-mcp-server",
    )

    if st.button("Load Repository"):
        st.session_state.repo = repo_input.strip()
        st.success(f"Loaded: {st.session_state.repo}")

    st.divider()

    if st.button("Start New Conversation"):
        st.session_state.history = []
        st.session_state.logs = []
        st.rerun()

    st.divider()

    with st.expander("🪵 State Logs"):
        if st.session_state.logs:
            if st.button("Expand Logs", use_container_width=True):
                show_logs_dialog()
        else:
            st.caption("No logs yet. Ask a question to see state logs here.")

# -------------------------------------------------------
# Display Chat History (Visual UI Bubbles)
# -------------------------------------------------------

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -------------------------------------------------------
# Chat Input & Execution (Stateless backend call)
# -------------------------------------------------------

user_prompt = st.chat_input("Ask a question about the repository...")

if user_prompt:

    if not st.session_state.repo:
        st.warning("Please load a GitHub repository first.")
        st.stop()

    # Append user input to UI history for display bubbles
    st.session_state.history.append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )

    with st.chat_message("user"):
        st.write(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Stateless call: No past history is sent to the backend graph
            answer, logs = ask_github_mcp_agent(
                repo=st.session_state.repo,
                question=user_prompt,
            )

        # Save logs for the debugging dialog
        st.session_state.logs.append(logs)
        st.write(answer)

    # Append assistant response to UI history for display bubbles
    st.session_state.history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    st.rerun()



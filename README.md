# 🐙 GitHub MCP Agent

**Chat with your GitHub repositories using natural language.**

GitHub MCP Agent is a Streamlit application that lets you ask questions about a GitHub repository and receive AI-generated answers. It uses **ChatOpenAI** for language-model integration, **LangGraph** to orchestrate the workflow, and GitHub's official remote **Model Context Protocol (MCP)** server to access repository information.

Ask questions such as:

- "Explain this repository."
- "What does the README say?"
- "Which files are responsible for the main functionality?"
- "How does this feature work?"

---

## 🏗️ Architecture & Workflow

The following diagram illustrates how the Streamlit interface, LangGraph workflow, ChatOpenAI, and GitHub MCP server work together.

![GitHub MCP Agent Architecture](/assets/architecture-flow.png)

For a detailed explanation of the architecture, see [`architecture.md`](./architecture.md).

---

## ✨ Features

- 💬 **Natural-language repository Q&A** — ask questions about GitHub repositories.
- 🔐 **Public and private repositories** — access repositories available to your configured GitHub token.
- 🧠 **ChatOpenAI integration** — generate answers using OpenAI chat models.
- 🔄 **LangGraph orchestration** — manage the assistant workflow and tool-calling loop.
- 🐙 **GitHub MCP integration** — access repository information through GitHub's official remote MCP server.
- 🛠️ **Controlled tool access** — restrict which MCP tools are available to the assistant.
- 🐞 **Debugging support** — inspect state logs and tool calls where implemented.
- 🔎 **MCP tool discovery** — inspect available GitHub MCP tools through the MCP client, where supported by the configuration.

---

## 🧰 Tech Stack

| Technology               | Purpose                                  |
| ------------------------ | ---------------------------------------- |
| Python                   | Core application language                |
| Streamlit                | Interactive chat interface               |
| ChatOpenAI               | Language-model integration               |
| LangChain OpenAI         | OpenAI integration for LangChain         |
| LangGraph                | Workflow orchestration                   |
| LangChain MCP Adapters   | Connect LangGraph workflows to MCP tools |
| GitHub Remote MCP Server | Repository access through MCP            |
| python-dotenv            | Environment variable management          |

---

## ✅ Requirements

Before getting started, ensure you have:

- Python 3.10 or newer
- An OpenAI API key
- A GitHub Personal Access Token with access to the repositories you want to query
- Internet connectivity

> 🔒 **Security:** Never commit your `.env` file, API keys, or access tokens to GitHub.

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd github-mcp-agent
```

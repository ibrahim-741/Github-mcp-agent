# GitHub MCP Agent — Architecture

A Streamlit chat app where a user loads a GitHub repo once, then asks
questions about it. Each question is answered by a **stateless**
LangGraph agent that calls GitHub's official remote MCP server
(filtered down to one tool) through an LLM on Groq.

---

## 0. What is MCP? (in plain terms)

Think of a restaurant. **You** don't walk into the kitchen and cook —
you tell a **waiter** what you want, the waiter carries that request to
the **kitchen**, and brings the food back. You never need to know how
the kitchen works.

**MCP (Model Context Protocol)** is that waiter — a shared, standard
way for an AI app to ask an external system ("get me this file") without
needing to know how that system is built internally.


### The Adapter

The waiter only speaks "kitchen." Your AI agent only understands
"LangChain tools." Someone has to translate between the two — that's
the **adapter** (`langchain-mcp-adapters` in this project). It takes
whatever the MCP server hands back and reshapes it into a format
LangChain/LangGraph already knows how to call.


---

## 1. File Map

```
app.py            Streamlit UI — repo input, chat, logs viewer
main.py           LangGraph build + execution (the agent's brain)
mcp_client.py     Connects to GitHub's MCP server, filters tools
groq_client.py    LLM provider (Groq)
prompt.py         System message
state.py          Shared graph state schema
```

---

## 2. Full Startup → Request Flow (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                              STARTUP                                 │
│                                                                       │
│   streamlit run app.py                                               │
│         │                                                            │
│         ▼                                                            │
│   app.py loads --> imports main.ask_github_mcp_agent                 │
│         │                                                            │
│         ▼                                                            │
│   Sidebar renders (repo box, buttons, logs expander)                 │
│         │                                                            │
│         ▼                                                            │
│   _graph = None   <-- nothing built yet (lazy)                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    USER LOADS A REPO (sidebar)                       │
│                                                                       │
│   type "owner/repo" --> click "Load Repository"                      │
│         │                                                            │
│         ▼                                                            │
│   st.session_state.repo = "owner/repo"                               │
│   (nothing sent to the backend yet -- just stored client-side)       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                 USER ASKS A QUESTION (chat box)                      │
│                                                                       │
│   "explain this repo" --> Enter                                      │
│         │                                                            │
│         ▼                                                            │
│   ask_github_mcp_agent(repo, question)          [main.py]            │
│         │                                                            │
│         ▼                                                            │
│   _graph is None?                                                    │
│      │                                                                │
│      ├── yes ──► _build_graph()  (see section 3, runs ONCE)          │
│      │                                                                │
│      └── no  ──► reuse cached graph                                  │
│         │                                                            │
│         ▼                                                            │
│   graph.ainvoke({ messages: [HumanMessage(question)], repo })        │
│         │                                                            │
│         ▼                                                            │
│   (see section 4 -- the assistant/tools loop)                        │
│         │                                                            │
│         ▼                                                            │
│   get_state_logs(result)  -->  logs string                           │
│   last AIMessage with content  -->  answer string                    │
│         │                                                            │
│         ▼                                                            │
│   app.py displays answer as a chat bubble, stores logs for sidebar   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. `_build_graph()` — runs exactly once per app process

```
_build_graph()
     │
     ├─► get_mcp_tools()                              [mcp_client.py]
     │        │
     │        ▼
     │   MultiServerMCPClient({ "github": {...} })
     │        │
     │        ▼
     │   client.get_tools()
     │        │
     │        ▼
     │   ── GitHub remote MCP server ──
     │   https://api.githubcopilot.com/mcp/
     │        │
     │        ▼
     │   40+ tools returned
     │        │
     │        ▼
     │   filtered by GITHUB_TOOLS_ALLOWLIST
     │        │
     │        ▼
     │   ["get_file_contents"]   <-- only this survives
     │
     ├─► get_llm().bind_tools(tools)                  [groq_client.py]
     │        │
     │        ▼
     │   ChatGroq(model="qwen/qwen3.6-27b") + tool schemas attached
     │
     └─► StateGraph(State) built and compiled          (section 4)
```

---

## 4. The Graph — assistant ⇄ tools loop

```
                    START
                      │
                      ▼
              ┌───────────────┐
       ┌─────►│   assistant    │
       │      └───────────────┘
       │              │
       │      tool_calls present?
       │              │
       │        ┌─────┴─────┐
       │        │           │
       │       yes          no
       │        │           │
       │        ▼           ▼
       │  ┌───────────┐    END
       │  │   tools    │
       │  │ (ToolNode) │
       │  └───────────┘
       │        │
       └────────┘
     (result appended as
      ToolMessage, loop
      back to assistant)
```

**Inside the `assistant` node, every pass:**

```
messages = state["messages"]
     │
     ▼
repo set AND last message is HumanMessage?
     │
     yes
     ▼
rewrite last message:
   "Repository:\n{repo}\n\nQuestion:\n{original_question}"
     │
     ▼
truncate any ToolMessage over 6000 chars
   (_truncate_if_tool_message, protects Groq TPM limit)
     │
     ▼
llm_with_tools.ainvoke([SYSTEM_MESSAGE] + messages)
     │
     ▼
response (AIMessage, maybe with tool_calls)
     │
     ▼
return {"messages": [response]}
```

---

## 5. State Shape

```
State
 ├── messages : list[BaseMessage]   (accumulated via add_messages)
 └── repo     : str | None          ("owner/repo", set per request)
```

Each call to `ask_github_mcp_agent()` builds a **fresh** `messages` list
containing only the current question — no checkpointer, no memory
across turns. `repo` comes from `st.session_state.repo` on every call.

```
Turn 1: messages = [HumanMessage("explain this repo")]
Turn 2: messages = [HumanMessage("what license does it use?")]
                     ▲
                     Turn 1 is NOT included here — fully stateless
```

---

## 6. Full Per-Request Sequence

```
app.py                  main.py                mcp tool (GitHub)
  │                         │                          │
  │──ask_github_mcp_agent──►│                          │
  │                         │                          │
  │                         │──inject repo into prompt │
  │                         │──truncate old tool msgs  │
  │                         │──llm.ainvoke(messages)───┤
  │                         │                          │
  │                         │◄─tool_call: get_file_contents
  │                         │                          │
  │                         │──ToolNode.invoke────────►│
  │                         │                          │──fetch file from GitHub
  │                         │◄─────────────────────────│
  │                         │                          │
  │                         │──llm.ainvoke(messages)───┤
  │                         │◄─final AIMessage (no tool_calls)
  │                         │                          │
  │◄──answer, logs──────────│                          │
  │                         │                          │
  │──render chat bubble     │                          │
  │──save logs to sidebar   │                          │
```

---

## 7. Token-Budget Guardrails

```
GITHUB_TOOLS_ALLOWLIST = {"get_file_contents"}
        │
        └─► keeps tool-schema tokens to a minimum
            (GitHub's server exposes 40+ tools --
             loading all of them can alone exceed
             hosted providers' rate limits)

MAX_TOOL_MESSAGE_CHARS = 6000
        │
        └─► _truncate_if_tool_message() caps any single
            tool result before it's resent to the LLM
```

---

## 8. Debugging Standalone

`mcp_client.py` can be run directly, without Streamlit or LangGraph,
to sanity-check the MCP connection and see every available tool's
name + description:

```
python mcp_client.py
```

```
total count of tools 43
Available tools from all servers:
- get_file_contents: Get the contents of a file...
- search_repositories: ...
...

Tools actually loaded:
- get_file_contents: Get the contents of a file...
```

---

## 9. Swappable Pieces

```
groq_client.py -> get_llm()
        Only this function needs to change to switch LLM providers.
        Everything downstream (main.py, mcp_client.py, state.py)
        is provider-agnostic.
```
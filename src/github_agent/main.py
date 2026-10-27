import asyncio
import io
import contextlib
import os
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from github_agent.openai_client import get_llm
from github_agent.mcp_client import get_mcp_tools
from github_agent.prompt import SYSTEM_MESSAGE
from github_agent.state import State

load_dotenv()

# -------------------------------------------------------
# LLM & Tools Setup
# -------------------------------------------------------

_graph = None
MAX_TOOL_MESSAGE_CHARS = 6000

#---------------------------------------------------------
#To control Token
#--------------------------------------------------------

def _truncate_if_tool_message(msg):
    """Cap oversized tool outputs to protect GPT TPM limits."""
    if not isinstance(msg, ToolMessage):  #if not tool message => nothing to be done
        return msg
    content = str(msg.content) #convert message into string => for counting length
    if len(content) <= MAX_TOOL_MESSAGE_CHARS:     #pass same tool message
        return msg
    truncated = content[:MAX_TOOL_MESSAGE_CHARS] + f"\n...(truncated, {len(content)} chars total)"
    return ToolMessage(content=truncated, tool_call_id=msg.tool_call_id, name=msg.name)  #convert back into and handover to langgraph


# -------------------------------------------------------
# Build Graph Function
# -------------------------------------------------------
async def _build_graph():
    tools = await get_mcp_tools()   
    print(f"\nLoaded tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool.name}")

    llm_with_tools = get_llm().bind_tools(tools) #adding tools to llm  => making it agent

    # 1. Assistant Node 
    async def assistant(state: State):
        repo = state.get("repo")
        messages = list(state["messages"])

        # Inject repository context into the latest human prompt if available
        if repo and isinstance(messages[-1], HumanMessage):
            original_question = messages[-1].content
            messages[-1] = HumanMessage(
                content=f"Repository:\n{repo}\n\nQuestion:\n{original_question}" #modifying the prompt
            )

        # Truncate tool responses to save tokens
        messages = [_truncate_if_tool_message(msg) for msg in messages]

        response = await llm_with_tools.ainvoke([SYSTEM_MESSAGE] + messages) #here i will route to my agent
        
        print("\nLLM Tool Calls:")
        print(response.tool_calls)

        return {"messages": [response]}

    # 2. Routing Logic
    def route_assistant(state: State):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return "end"

    # 3. Compile Graph
    builder = StateGraph(State)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        route_assistant,
        {"tools": "tools", "end": END},
    )
    builder.add_edge("tools", "assistant")

    return builder.compile()

# -------------------------------------------------------
# Logs & Execution Interface
# -------------------------------------------------------
def get_state_logs(result):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        print("\n===== STATE LOGS =====")
        if result.get("repo"):
            print(f"Repository: {result['repo']}")
        for i, msg in enumerate(result["messages"]):
            content = getattr(msg, "content", "No content")
            print(f"[{i}] {msg.__class__.__name__}: {content}")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"    Tool Calls: {msg.tool_calls}")
        print("======================\n")
    return output.getvalue()



def ask_github_mcp_agent(repo: str, question: str):
    async def _run():
        global _graph
        if _graph is None:
            _graph = await _build_graph()

        # STRICTLY STATELESS: Only pass the repo and the current question. 
        # Do not accumulate or accept chat_history lists.
        result = await _graph.ainvoke(
            {
                "messages": [HumanMessage(content=question)],
                "repo": repo,
            }
        )

        logs = get_state_logs(result)

        answer = "No answer generated."
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                answer = msg.content
                break

        return answer, logs

    return asyncio.run(_run())




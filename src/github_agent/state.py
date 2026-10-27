from typing import Annotated, Optional, TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict):
    """
    State shared across the LangGraph workflow.

    messages:
        Conversation messages managed by LangGraph.
        add_messages appends new messages instead of replacing the list,
        which is what lets the assistant <-> tools loop accumulate
        AIMessage / ToolMessage turns.

    repo:
        The currently selected GitHub repository for this request.
        Example: "github/github-mcp-server".
        Set per invocation, not persisted across turns.
    """

    messages: Annotated[list, add_messages]
    repo: Optional[str]



import asyncio
import logging
import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

logger = logging.getLogger(__name__)

# Each GitHub tool schema is token-heavy and Groq's hosted tiers have a
# tokens-per-minute ceiling, so only a small allowlist is loaded per run.
# Add only the tools you actually need. Names must match GitHub's catalog exactly.
DEFAULT_ALLOWLIST = {
    "get_file_contents",
    "search_code",
    "list_commits",
}


def get_allowlist() -> set[str]:
    """Read the tool allowlist from GITHUB_TOOLS_ALLOWLIST, falling back to the default."""
    raw = os.getenv("GITHUB_TOOLS_ALLOWLIST", "")
    names = {name.strip() for name in raw.split(",") if name.strip()}
    return names or DEFAULT_ALLOWLIST


def get_mcp_client() -> MultiServerMCPClient:
    github_pat = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_pat:
        raise ValueError(
            "GITHUB_PERSONAL_ACCESS_TOKEN not found. Set it in your .env file."
        )

    return MultiServerMCPClient(
        {
            # You can register more MCP servers here later, e.g. "slack", "postgres".
            "github": {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {github_pat}",
                },
            },
        }
    )


async def get_mcp_tools(retries: int = 2):
    """Connect to the GitHub MCP server and return the filtered tool list."""
    all_tools = None
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            client = get_mcp_client()
            all_tools = await client.get_tools()
            break
        except Exception as exc:  # network, auth, transport, etc.
            last_error = exc
            logger.warning(
                "MCP get_tools failed (attempt %s/%s): %s", attempt, retries, exc
            )
            if attempt < retries:
                await asyncio.sleep(1.5 * attempt)

    if all_tools is None:
        raise RuntimeError(
            f"Could not load GitHub MCP tools: {last_error}"
        ) from last_error

    logger.info("Total tools exposed by GitHub MCP server: %s", len(all_tools))
    for tool in all_tools:
        logger.info("  available: %s — %s", tool.name, tool.description)

    # ---- FILTER: only the tools you chose make it into the agent ----
    allowlist = get_allowlist()
    filtered = [tool for tool in all_tools if tool.name in allowlist] #remove this if we want all tools

    logger.info(
        "Tools loaded into the agent (%s of %s):", len(filtered), len(all_tools)
    )
    for tool in filtered:
        logger.info("  loaded: %s — %s", tool.name, tool.description)

    if not filtered:
        logger.warning(
            "Allowlist %s matched no tools. The agent will have no tools available.",
            sorted(allowlist),
        )

    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(get_mcp_tools())


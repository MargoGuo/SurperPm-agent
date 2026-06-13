"""Direct query service for dev/test — runs query() to completion and returns result."""
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock


async def chat_query_sync(
    prompt: str,
    plugin: str,
    plugin_repo_path: str,
    target_repo_path: str,
) -> dict:
    plugin_path = plugin_repo_path.replace("SuperPmAgent-core", plugin) if plugin != "SuperPmAgent-core" else plugin_repo_path
    options = ClaudeAgentOptions(
        plugins=[{"type": "local", "path": plugin_path}],
        allowed_tools=["Read", "Edit", "Write", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",
        cwd=target_repo_path,
        max_turns=10,
    )

    texts: list[str] = []
    cost = 0.0
    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        texts.append(block.text)
            elif isinstance(msg, ResultMessage):
                cost = getattr(msg, "total_cost_usd", 0.0)
        return {"response": "\n".join(texts), "cost_usd": cost, "error": None}
    except Exception as e:
        return {"response": "\n".join(texts), "cost_usd": cost, "error": str(e)}

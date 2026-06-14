"""Shared AI chat reply logic for discussions (goal-scoped + standalone)."""

import logging

import anthropic

from app.services.event_bus import DISCUSSION_CREATED, DISCUSSION_DELTA, bus
from app.services.knowledge_store import get_store

_logger = logging.getLogger(__name__)

_MAX_CONTEXT_MESSAGES = 20
_EVOLVE_EVERY_N = 10  # analyze profile evolution every N messages


async def generate_ai_reply(
    workspace_id: str,
    user_content: str,
    *,
    goal_id: int | None = None,
    image_data_uri: str | None = None,
    topic_id: int | None = None,
    username: str | None = None,
) -> None:
    from app.routes.discussions_standalone import _build_system_prompt
    from app.services.ai_key_resolver import (
        resolve_ai_base_url,
        resolve_ai_key,
        resolve_ai_model,
    )

    store = get_store()
    api_key = await resolve_ai_key()

    disc_id: int | None = None
    try:
        if not api_key:
            err_disc = await store.create_discussion({
                "workspace_id": workspace_id,
                "goal_id": goal_id,
                "content": "⚠️ AI API 未配置，请在 Settings → AI Model 中设置。",
                "role": "agent",
                "topic_id": topic_id,
            })
            await bus.emit(DISCUSSION_CREATED, {
                "id": err_disc["id"],
                "workspace_id": workspace_id,
                "goal_id": goal_id,
                "role": "agent",
                "content": err_disc["content"],
                "topic_id": topic_id,
                "created_at": err_disc["created_at"],
            })
            await bus.emit(DISCUSSION_DELTA, {
                "workspace_id": workspace_id,
                "goal_id": goal_id,
                "discussion_id": err_disc["id"],
                "delta": "",
                "done": True,
            })
            return

        agent_disc = await store.create_discussion({
            "workspace_id": workspace_id,
            "goal_id": goal_id,
            "content": "",
            "role": "agent",
            "topic_id": topic_id,
        })
        disc_id = agent_disc["id"]

        await bus.emit(DISCUSSION_CREATED, {
            "id": disc_id,
            "workspace_id": workspace_id,
            "goal_id": goal_id,
            "role": "agent",
            "content": "",
            "topic_id": topic_id,
            "created_at": agent_disc["created_at"],
        })

        recent = store.list_discussions(topic_id=topic_id)
        recent = [
            r for r in recent if r.get("workspace_id") == workspace_id
        ]
        if goal_id is None:
            recent = [r for r in recent if r.get("goal_id") is None]
        recent.sort(key=lambda r: r.get("created_at", ""))
        recent = recent[-_MAX_CONTEXT_MESSAGES:]

        messages: list[dict] = []
        for msg in recent:
            if msg.get("id") == disc_id:
                continue
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append(
                {"role": role, "content": msg.get("content", "")},
            )

        if image_data_uri and messages and messages[-1]["role"] == "user":
            media_type = "image/png"
            b64_data = image_data_uri
            if image_data_uri.startswith("data:"):
                header, b64_data = image_data_uri.split(",", 1)
                if "image/jpeg" in header:
                    media_type = "image/jpeg"
            messages[-1]["content"] = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {"type": "text", "text": messages[-1]["content"]},
            ]

        base_url = await resolve_ai_base_url()
        model = await resolve_ai_model()
        client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url or None,
        )
        full_text = ""

        async with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=_build_system_prompt(username=username),
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
                await bus.emit(DISCUSSION_DELTA, {
                    "workspace_id": workspace_id,
                    "goal_id": goal_id,
                    "discussion_id": disc_id,
                    "delta": text,
                })

        cache_key = store._disc_cache_key(topic_id)
        cached = store._cache.get(cache_key, [])
        for row in cached:
            if row.get("id") == disc_id:
                row["content"] = full_text
                break
        store._flush_jsonl(store._discussion_path(topic_id), cached)

        await bus.emit(DISCUSSION_DELTA, {
            "workspace_id": workspace_id,
            "goal_id": goal_id,
            "discussion_id": disc_id,
            "delta": "",
            "done": True,
        })

        if username and disc_id and disc_id % _EVOLVE_EVERY_N == 0:
            import asyncio
            asyncio.create_task(_maybe_evolve_profile(username, messages, store))

    except Exception as e:
        _logger.warning("AI reply failed: %s", e)
        if disc_id is not None:
            error_text = f"⚠️ AI 回复出错: {e}"
            cache_key = store._disc_cache_key(topic_id)
            cached = store._cache.get(cache_key, [])
            for row in cached:
                if row.get("id") == disc_id:
                    row["content"] = error_text
                    break
            store._flush_jsonl(
                store._discussion_path(topic_id), cached,
            )
            await bus.emit(DISCUSSION_DELTA, {
                "workspace_id": workspace_id,
                "goal_id": goal_id,
                "discussion_id": disc_id,
                "delta": error_text,
                "done": True,
            })


async def _maybe_evolve_profile(
    username: str, messages: list[dict], store,
) -> None:
    """Analyze recent conversation to auto-update user profile preferences."""
    try:
        from app.services.ai_key_resolver import resolve_ai_key, resolve_ai_base_url, resolve_ai_model

        root = store._root.parent
        user_md_path = root / "profiles" / "users" / f"{username}.md"
        if not user_md_path.is_file():
            return

        current_profile = user_md_path.read_text(encoding="utf-8")
        recent_msgs = messages[-10:]
        conversation = "\n".join(
            f"[{m['role']}] {m['content'][:200]}" for m in recent_msgs
        )

        api_key = await resolve_ai_key()
        if not api_key:
            return

        client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=await resolve_ai_base_url() or None,
        )

        resp = await client.messages.create(
            model=await resolve_ai_model(),
            max_tokens=400,
            system=(
                "You are a profile evolution engine. Given a user's current profile and recent conversation, "
                "determine if the profile should be updated. Output ONLY the updated markdown profile if changes are needed, "
                "or output exactly 'NO_CHANGE' if no update is warranted. "
                "Only update fields where the conversation provides clear evidence of a preference change. "
                "Preserve the existing frontmatter and structure."
            ),
            messages=[{
                "role": "user",
                "content": f"## Current Profile\n{current_profile}\n\n## Recent Conversation\n{conversation}",
            }],
        )

        result = resp.content[0].text.strip()
        if result != "NO_CHANGE" and len(result) > 50:
            user_md_path.write_text(result, encoding="utf-8")
            _logger.info("profile evolved for user %s", username)

    except Exception:
        _logger.debug("profile evolution skipped for %s", username, exc_info=True)

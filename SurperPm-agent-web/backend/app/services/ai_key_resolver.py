"""Resolve AI API key / base_url / model from multiple sources."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import settings

_logger = logging.getLogger(__name__)

_AI_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "ai_config.json"


def _read_ai_config_file() -> dict:
    if _AI_CONFIG_FILE.is_file():
        try:
            return json.loads(_AI_CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


async def resolve_ai_key() -> str | None:
    """Return the first non-empty API key from: GlobalConfig → ai_config.json → env."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig
    from app.services.crypto import decrypt

    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if cfg and cfg.ai_api_key_enc:
            try:
                key = decrypt(cfg.ai_api_key_enc)
                if key:
                    return key
            except Exception:
                _logger.debug("ai_key_resolver: failed to decrypt GlobalConfig key")

    file_cfg = _read_ai_config_file()
    if file_cfg.get("api_key"):
        return file_cfg["api_key"]

    if settings.anthropic_api_key:
        return settings.anthropic_api_key

    return None


async def resolve_ai_base_url() -> str | None:
    """Return the first non-empty base_url from: KnowledgeStore settings → ai_config.json → env."""
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    if store_settings.get("ai_base_url"):
        return store_settings["ai_base_url"]

    file_cfg = _read_ai_config_file()
    if file_cfg.get("base_url"):
        return file_cfg["base_url"]

    if settings.anthropic_base_url:
        return settings.anthropic_base_url

    return None


async def resolve_ai_model() -> str:
    """Return the configured model, defaulting to claude-sonnet-4-20260614."""
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    if store_settings.get("ai_model"):
        return store_settings["ai_model"]

    file_cfg = _read_ai_config_file()
    if file_cfg.get("model"):
        return file_cfg["model"]

    if settings.agent_model:
        return settings.agent_model

    return "claude-sonnet-4-20260614"

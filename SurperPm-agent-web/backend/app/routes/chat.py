"""Dev/test endpoint for direct plugin queries."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.services.chat_query import chat_query_sync

router = APIRouter()


class ChatQueryRequest(BaseModel):
    prompt: str
    plugin: str = "SuperPmAgent-core"


@router.post("/query")
async def query_plugin(req: ChatQueryRequest) -> dict:
    return await chat_query_sync(
        prompt=req.prompt,
        plugin=req.plugin,
        plugin_repo_path=settings.plugin_repo_path,
        target_repo_path=settings.target_repo_path,
    )

"""Legacy Pydantic request/response models (non-table)."""
from pydantic import BaseModel


class GoalSubmit(BaseModel):
    session_id: str | None = None
    text: str
    max_iterations: int = 50
    token_budget: int = 500_000
    max_duration_min: int = 60
    sandbox: str = "lap"  # "lap" | "local"


class GoalRun(BaseModel):
    id: str
    status: str  # running | paused | waiting_human | done | failed
    iter: int
    tokens_used: int
    pr_url: str | None = None
    distill_pr_urls: list[str] = []


class SessionFolder(BaseModel):
    name: str
    path: str
    last_modified: str


class KnowledgeNode(BaseModel):
    path: str
    is_dir: bool
    children: list["KnowledgeNode"] = []

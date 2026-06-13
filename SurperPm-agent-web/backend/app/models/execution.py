"""Execution table model."""

import secrets
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Execution(SQLModel, table=True):
    __tablename__ = "execution"

    id: str = Field(default_factory=lambda: secrets.token_hex(8), primary_key=True)
    goal_id: int = Field(foreign_key="goal.id", nullable=False)
    workspace_id: str = Field(foreign_key="workspace.id", nullable=False)
    status: str = Field(default="pending")  # pending | running | success | failed | timeout
    branch: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None)
    log_path: str | None = Field(default=None)
    pr_url: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

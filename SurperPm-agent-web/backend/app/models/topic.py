"""Topic table model — Slack-style discussion channels."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Topic(SQLModel, table=True):
    __tablename__ = "topic"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = Field(foreign_key="workspace.id", nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    goal_id: int | None = Field(default=None, foreign_key="goal.id")
    session_name: str | None = Field(default=None)
    repo_url: str | None = Field(default=None)
    pinned: bool = Field(default=False)
    archived: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

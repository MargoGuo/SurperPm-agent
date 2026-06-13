"""Goal table model."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Goal(SQLModel, table=True):
    __tablename__ = "goal"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = Field(foreign_key="workspace.id", nullable=False)
    title: str = Field(nullable=False)
    description: str | None = Field(default=None)
    status: str = Field(default="todo")  # todo | doing | done | failed
    priority: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

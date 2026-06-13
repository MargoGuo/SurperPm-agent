"""Discussion table model."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Discussion(SQLModel, table=True):
    __tablename__ = "discussion"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: str = Field(foreign_key="workspace.id", nullable=False)
    goal_id: int | None = Field(default=None, foreign_key="goal.id")
    role: str = Field(nullable=False)  # user | agent | system
    content: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

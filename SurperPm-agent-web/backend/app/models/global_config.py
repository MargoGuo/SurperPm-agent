"""GlobalConfig singleton table — system-wide settings."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class GlobalConfig(SQLModel, table=True):
    __tablename__ = "global_config"

    id: int = Field(default=1, primary_key=True)
    founder_username: str | None = Field(default=None)
    knowledge_repo_url: str | None = Field(default=None)
    knowledge_repo_path: str | None = Field(default=None)
    ssh_public_key: str | None = Field(default=None)
    ssh_private_key_enc: str | None = Field(default=None)
    ai_base_url: str | None = Field(default=None)
    ai_api_key_enc: str | None = Field(default=None)
    ai_model: str | None = Field(default=None)
    github_token_enc: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

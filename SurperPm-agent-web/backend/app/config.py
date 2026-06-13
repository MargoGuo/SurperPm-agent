"""Settings loaded from env vars / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GitHub OAuth
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"

    # GitHub PAT (fallback)
    github_token: str = ""
    github_repo: str = ""  # e.g. "myteam/claude-for-SuperPmAgent-fork"

    # Session
    SuperPmAgent_secret: str = ""

    # Anthropic / 豆包
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""  # 代理地址，如 https://api.deepseek.com/anthropic
    doubao_api_key: str = ""
    doubao_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3"

    agent_model: str = ""  # 模型，如 deepseek-v4-flash、claude-sonnet-4-20260613

    # LAP
    lap_url: str = ""
    lap_token: str = ""

    # Local repo path (for dev — points at the user's local clone)
    repo_local_path: str = ""

    # Goal runner
    plugin_repo_path: str = ""  # path to claude-for-SuperPmAgent/SuperPmAgent-core
    target_repo_path: str = ""  # path to target git repo for goal execution


settings = Settings()

"""Settings loaded from env vars / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GitHub OAuth
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"

    # (GitHub token stored in session cookie / GlobalConfig.github_token_enc only)

    # Session
    SuperPmAgent_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""  # 代理地址，如 https://api.deepseek.com/anthropic

    agent_model: str = ""  # 模型，如 deepseek-v4-flash、claude-sonnet-4-20260614

    # Goal runner
    plugin_repo_path: str = ""  # path to SuperPmAgent-plugins repo clone

    # Knowledge
    knowledge_repo_path: str = ""  # path to SuperPmAgent-knowledge repo clone

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/SuperPmAgent.db"

    # Encryption key for secrets (Fernet)
    secret_key: str = ""

    # Frontend URL (for OAuth redirects)
    frontend_url: str = "http://localhost:5173"


settings = Settings()

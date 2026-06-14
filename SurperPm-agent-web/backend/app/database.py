"""Async SQLite database engine and session factory."""
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config import settings

_logger = logging.getLogger(__name__)

_db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
_db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, type_default)
    ("goal", "assigned_to", "TEXT"),
    ("goal", "suggested_assignee", "TEXT"),
    ("goal", "parent_goal_id", "INTEGER"),
    ("goal", "token_budget", "INTEGER"),
    ("execution", "token_used", "INTEGER"),
    ("execution", "token_budget", "INTEGER"),
    ("execution", "summary", "TEXT"),
    ("execution", "artifacts", "TEXT"),
    ("execution", "logs", "JSON"),
    ("discussion", "author", "TEXT"),
    ("discussion", "parent_id", "INTEGER"),
    ("discussion", "topic_id", "INTEGER"),
    ("workspace", "repos", "TEXT"),
    ("topic", "repo_url", "TEXT"),
    ("topic", "session_name", "TEXT"),
    ("goal", "slug", "TEXT"),
    ("goal", "repo_url", "TEXT"),
    ("goal", "repo_path", "TEXT"),
    ("goal", "repos", "TEXT"),
    ("global_config", "github_token_enc", "TEXT"),
    ("global_config", "founder_username", "TEXT"),
    ("goal", "reviewed_by", "TEXT"),
    ("goal", "reviewed_at", "TEXT"),
    ("goal", "group_id", "INTEGER"),
    ("goal", "deadline", "TEXT"),
    ("goal", "session_name", "TEXT"),
    ("global_config", "distill_config", "TEXT"),
]


async def _migrate_schema(conn) -> None:
    """Add any missing columns to existing tables (SQLite ADD COLUMN)."""
    for table, column, col_type in _MIGRATIONS:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result.fetchall()}
        if column not in existing:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            )
            _logger.info("Migrated: ALTER TABLE %s ADD COLUMN %s %s", table, column, col_type)


async def _seed_global_config(conn) -> None:
    """Seed global_config singleton, copying data from the first workspace."""
    result = await conn.execute(text("SELECT COUNT(*) FROM global_config"))
    if result.scalar():
        return

    ws = await conn.execute(text(
        "SELECT knowledge_repo_url, knowledge_repo_path, "
        "ssh_public_key, ssh_private_key_enc FROM workspace LIMIT 1"
    ))
    row = ws.fetchone()

    if row:
        await conn.execute(text(
            "INSERT INTO global_config (id, knowledge_repo_url, knowledge_repo_path, "
            "ssh_public_key, ssh_private_key_enc, created_at, updated_at) "
            "VALUES (1, :kru, :krp, :spk, :ske, datetime('now'), datetime('now'))"
        ), {"kru": row[0], "krp": row[1], "spk": row[2], "ske": row[3]})
    else:
        await conn.execute(text(
            "INSERT INTO global_config (id, created_at, updated_at) "
            "VALUES (1, datetime('now'), datetime('now'))"
        ))

    _logger.info("Seeded global_config singleton row")


async def _generate_goal_slugs(conn) -> None:
    """Generate slugs for existing goals that don't have one."""
    import re
    result = await conn.execute(text("SELECT id, title FROM goal WHERE slug IS NULL"))
    for row in result.fetchall():
        slug = re.sub(r"[^a-z0-9]+", "-", row[1].lower()).strip("-")[:60] or f"goal-{row[0]}"
        await conn.execute(
            text("UPDATE goal SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": row[0]},
        )
    _logger.info("Generated slugs for existing goals")


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await _migrate_schema(conn)
        await _seed_global_config(conn)
        await _generate_goal_slugs(conn)


async def get_session():
    async with async_session() as session:
        yield session

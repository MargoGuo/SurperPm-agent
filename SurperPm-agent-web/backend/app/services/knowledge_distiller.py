"""Knowledge Distiller — file-based learnings stored as Markdown in SuperPmAgent-knowledge repo.

Learnings are Markdown files with YAML-like frontmatter in knowledge/learnings/.
No database tables — the knowledge repo IS the database, Git IS the migration.
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path

from app.services.knowledge_sync import _target_path

_logger = logging.getLogger(__name__)

DECAY_LAMBDA: dict[str, float] = {
    "decision": 0.014,
    "pattern": 0.022,
    "mistake": 0.040,
    "insight": 0.040,
    "external": 0.030,
}

DEFAULT_DISTILL_CONFIG: dict = {
    "internal_sources": {
        "executions": True,
        "discussions": True,
    },
    "external_sources": [],
    "schedule": {"interval_hours": 24},
    "decay": {
        "archive_threshold": 0.3,
        "pin_bonus": 0.5,
    },
    "max_learnings_per_cycle": 10,
}


def _learnings_dir() -> Path:
    return _target_path() / "learnings"


def _access_log_path() -> Path:
    log_dir = _target_path() / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "learning_access.json"


def _load_access_counts() -> dict[str, int]:
    path = _access_log_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_access_counts(counts: dict[str, int]) -> None:
    path = _access_log_path()
    path.write_text(json.dumps(counts, indent=2))


def _parse_learning_file(path: Path) -> dict | None:
    """Parse a learning Markdown file with YAML-like frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_raw = parts[1].strip()
    body = parts[2].strip()

    meta: dict = {}
    for line in frontmatter_raw.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if val.lower() in ("true", "false"):
            meta[key] = val.lower() == "true"
        elif re.match(r"^\d+(\.\d+)?$", val):
            meta[key] = float(val) if "." in val else int(val)
        else:
            meta[key] = val

    meta["body"] = body
    meta["slug"] = path.stem
    meta["file_path"] = str(path)
    return meta


def _compute_score(meta: dict, access_count: int = 0, config: dict | None = None) -> float:
    """Memory curve: score = importance * e^(-λt) + 0.5*ln(1+access) + pin_bonus"""
    importance = meta.get("importance", 0.5)
    category = meta.get("category", "insight")
    lam = DECAY_LAMBDA.get(category, 0.030)
    pinned = meta.get("pinned", False)
    archived = meta.get("archived", False)

    if archived:
        return 0.0

    created_str = meta.get("created", "")
    try:
        created = datetime.fromisoformat(created_str)
    except (ValueError, TypeError):
        created = datetime.now(UTC)

    tz = UTC if not created.tzinfo else created.tzinfo
    days_old = (datetime.now(UTC) - created.replace(tzinfo=tz)).days
    time_decay = importance * math.exp(-lam * days_old)
    access_bonus = 0.5 * math.log(1 + access_count)

    cfg = config or DEFAULT_DISTILL_CONFIG
    pin_bonus = cfg.get("decay", {}).get("pin_bonus", 0.5) if pinned else 0.0

    return time_decay + access_bonus + pin_bonus


def list_learnings(config: dict | None = None) -> list[dict]:
    """Read all learning Markdown files from learnings/ dir, compute scores."""
    ld = _learnings_dir()
    if not ld.exists():
        return []

    access_counts = _load_access_counts()
    learnings: list[dict] = []

    for f in ld.glob("*.md"):
        meta = _parse_learning_file(f)
        if not meta:
            continue
        slug = meta["slug"]
        ac = access_counts.get(slug, 0)
        meta["access_count"] = ac
        meta["score"] = _compute_score(meta, ac, config)
        learnings.append(meta)

    learnings.sort(key=lambda x: x["score"], reverse=True)
    return learnings


def get_top_learnings(budget_tokens: int = 500, config: dict | None = None) -> str:
    """Format top learnings for injection into goal execution context."""
    all_learnings = [x for x in list_learnings(config) if not x.get("archived")]
    if not all_learnings:
        return ""

    lines: list[str] = []
    used_tokens = 0
    for item in all_learnings:
        title = item.get("title", item["slug"])
        body = item.get("body", "")[:200]
        entry = f"- [{item.get('category', 'insight')}] {title}: {body}"
        entry_tokens = len(entry) // 4
        if used_tokens + entry_tokens > budget_tokens:
            break
        lines.append(entry)
        used_tokens += entry_tokens

    return "\n".join(lines)


def record_access(slug: str) -> None:
    """Increment access count for a learning."""
    counts = _load_access_counts()
    counts[slug] = counts.get(slug, 0) + 1
    _save_access_counts(counts)


def write_learning(
    title: str,
    content: str,
    category: str = "insight",
    source_type: str = "internal",
    importance: float = 0.5,
    tags: list[str] | None = None,
) -> Path:
    """Write a new learning as a Markdown file with frontmatter."""
    ld = _learnings_dir()
    ld.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:60].strip("-")
    slug = f"{now.strftime('%Y%m%d')}-{slug}"

    file_path = ld / f"{slug}.md"
    counter = 1
    while file_path.exists():
        file_path = ld / f"{slug}-{counter}.md"
        counter += 1

    tags_str = ", ".join(tags) if tags else ""
    frontmatter = (
        f"---\n"
        f"title: {title}\n"
        f"category: {category}\n"
        f"source_type: {source_type}\n"
        f"importance: {importance}\n"
        f"confidence: 0.8\n"
        f"created: {now.isoformat()}\n"
        f"pinned: false\n"
        f"archived: false\n"
        f"tags: {tags_str}\n"
        f"---\n\n"
    )
    file_path.write_text(frontmatter + content, encoding="utf-8")
    return file_path


def apply_decay(config: dict | None = None) -> list[str]:
    """Archive learnings below threshold. Returns list of archived slugs."""
    cfg = config or DEFAULT_DISTILL_CONFIG
    threshold = cfg.get("decay", {}).get("archive_threshold", 0.3)
    archived: list[str] = []

    ld = _learnings_dir()
    if not ld.exists():
        return []

    access_counts = _load_access_counts()

    for f in ld.glob("*.md"):
        meta = _parse_learning_file(f)
        if not meta or meta.get("archived") or meta.get("pinned"):
            continue

        score = _compute_score(meta, access_counts.get(meta["slug"], 0), cfg)
        if score < threshold:
            text = f.read_text(encoding="utf-8")
            text = text.replace("archived: false", "archived: true", 1)
            f.write_text(text, encoding="utf-8")
            archived.append(meta["slug"])

    return archived


async def _ai_distill(raw_items: list[dict], config: dict | None = None) -> list[dict]:
    """Use AI to distill raw items into structured learnings."""
    from app.services.ai_key_resolver import resolve_ai_base_url, resolve_ai_key, resolve_ai_model

    api_key = await resolve_ai_key()
    if not api_key:
        return _fallback_distill(raw_items)

    try:
        import httpx

        base_url = await resolve_ai_base_url() or "https://api.openai.com/v1"
        model = await resolve_ai_model()

        items_text = "\n".join(
            f"- [{it.get('type', 'unknown')}] "
            f"{it.get('title', '')}: {it.get('content', '')[:300]}"
            for it in raw_items[:20]
        )

        prompt = (
            "You are a knowledge distiller. "
            "From the following raw items, extract key learnings.\n"
            "For each learning, output JSON with: title, "
            "content (1-3 sentences), category "
            "(one of: decision, pattern, mistake, insight, external), "
            "importance (0.0-1.0), tags (list).\n"
            "Output a JSON array. Only include genuinely useful "
            "knowledge.\n\n"
            f"Raw items:\n{items_text}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
            if resp.status_code != 200:
                _logger.warning("AI distill failed: %d", resp.status_code)
                return _fallback_distill(raw_items)

            text = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception:
        _logger.warning("AI distill error", exc_info=True)

    return _fallback_distill(raw_items)


def _fallback_distill(raw_items: list[dict]) -> list[dict]:
    """Pass-through when AI is unavailable."""
    results = []
    for item in raw_items[:5]:
        results.append({
            "title": item.get("title", "Untitled")[:120],
            "content": item.get("content", "")[:500],
            "category": (
                "external"
                if item.get("type", "").startswith(("github", "rss", "web"))
                else "insight"
            ),
            "importance": 0.4,
            "tags": [item.get("type", "unknown")],
        })
    return results


async def _collect_from_executions() -> list[dict]:
    """Collect raw items from recent goal executions."""
    from app.services.knowledge_store import get_store

    store = get_store()
    exes = store.list("executions")
    exes = [
        e for e in exes
        if e.get("status") == "success" and e.get("summary")
    ]
    exes.sort(key=lambda e: e.get("finished_at", ""), reverse=True)
    items: list[dict] = []
    for ex in exes[:20]:
        items.append({
            "type": "execution",
            "title": f"Goal execution #{ex.get('id')}",
            "content": ex.get("summary", ""),
            "date": ex.get("finished_at", ""),
        })
    return items


async def _collect_from_discussions() -> list[dict]:
    """Collect raw items from recent AI discussions."""
    from app.services.knowledge_store import get_store

    store = get_store()
    all_discs = store.list_all_discussions()
    agent_msgs = [
        d for d in all_discs
        if d.get("role") == "agent" and len(d.get("content", "")) > 100
    ]
    agent_msgs.sort(
        key=lambda d: d.get("created_at", ""), reverse=True,
    )
    items: list[dict] = []
    for d in agent_msgs[:20]:
        content = d.get("content", "")
        items.append({
            "type": "discussion",
            "title": content[:80],
            "content": content[:1000],
            "date": d.get("created_at", ""),
        })
    return items


async def _fetch_external_sources(config: dict) -> list[dict]:
    """Fetch from configured external sources."""
    from app.database import async_session
    from app.models.global_config import GlobalConfig
    from app.services.crypto import decrypt
    from app.services.source_fetcher import fetch_github, fetch_rss, fetch_webpage

    sources = config.get("external_sources", [])
    items: list[dict] = []

    github_token: str | None = None
    async with async_session() as session:
        cfg = await session.get(GlobalConfig, 1)
        if cfg and cfg.github_token_enc:
            try:
                github_token = decrypt(cfg.github_token_enc)
            except Exception:
                pass

    for src in sources:
        src_type = src.get("type", "")
        url = src.get("url", "")
        if not url:
            continue
        try:
            if src_type == "github":
                items.extend(await fetch_github(url, token=github_token))
            elif src_type == "rss":
                items.extend(await fetch_rss(url))
            elif src_type == "webpage":
                items.extend(await fetch_webpage(url))
        except Exception:
            _logger.warning("Failed to fetch source: %s %s", src_type, url, exc_info=True)

    return items


async def _git_commit_learnings(message: str = "auto-distill: update learnings") -> bool:
    """Git add + commit + push learnings directory."""
    import subprocess as _sp

    from app.services.platform import run_cmd

    repo_path = _target_path()
    if not (repo_path / ".git").is_dir():
        return False

    try:
        await run_cmd("git", "-C", str(repo_path), "add", "learnings/", ".logs/", timeout=10)

        # diff --cached --quiet exits 0 when nothing to commit, 1 when there are changes.
        # raw subprocess is needed here because we care about the specific exit code.
        diff = _sp.run(
            ["git", "-C", str(repo_path), "diff", "--cached", "--quiet"],
            capture_output=True, timeout=5,
        )
        if diff.returncode == 0:
            return True  # no changes to commit

        await run_cmd(
            "git", "-C", str(repo_path),
            "-c", "user.name=SuperPmAgent", "-c", "user.email=SuperPmAgent@local",
            "commit", "-m", message,
            timeout=10,
        )

        await run_cmd("git", "-C", str(repo_path), "push", timeout=30)
        return True
    except RuntimeError:
        _logger.warning("git commit learnings failed", exc_info=True)
        return False


async def run_distill_cycle(config: dict | None = None) -> dict:
    """Full distill pipeline: collect → AI distill → write → decay → git commit."""
    cfg = config or DEFAULT_DISTILL_CONFIG
    _logger.info("knowledge_distiller: starting distill cycle")

    raw_items: list[dict] = []

    internal = cfg.get("internal_sources", {})
    if internal.get("executions"):
        raw_items.extend(await _collect_from_executions())
    if internal.get("discussions"):
        raw_items.extend(await _collect_from_discussions())

    raw_items.extend(await _fetch_external_sources(cfg))

    if not raw_items:
        _logger.info("knowledge_distiller: no raw items to distill")
        return {"distilled": 0, "archived": []}

    max_per_cycle = cfg.get("max_learnings_per_cycle", 10)
    distilled = await _ai_distill(raw_items[:max_per_cycle * 2], cfg)

    written = 0
    for item in distilled[:max_per_cycle]:
        write_learning(
            title=item.get("title", "Untitled"),
            content=item.get("content", ""),
            category=item.get("category", "insight"),
            source_type=item.get("source_type", "auto"),
            importance=item.get("importance", 0.5),
            tags=item.get("tags"),
        )
        written += 1

    archived = apply_decay(cfg)
    await _git_commit_learnings()

    _logger.info(
        "knowledge_distiller: cycle done — %d written, %d archived",
        written, len(archived),
    )
    return {"distilled": written, "archived": archived}

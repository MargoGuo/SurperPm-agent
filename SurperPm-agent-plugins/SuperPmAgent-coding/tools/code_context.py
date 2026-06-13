#!/usr/bin/env python3
"""Lightweight local code-context CLI (no MCP).

Replaces analyzeProject / exploreCodeContext for JS/TS/Python repos.
Usage:
  python code_context.py analyze --project PATH --keywords "A,B,C" [--focus SUBDIR]
  python code_context.py explore --project PATH --mode expand|search|trace --query QUERY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from pathlib import Path
from typing import Iterable

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "target",
}

CODE_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".rs", ".java", ".vue", ".svelte"}


def _iter_files(root: Path, focus: str | None = None) -> Iterable[Path]:
    base = root / focus if focus else root
    if not base.exists():
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in CODE_EXTS:
                yield p


def _read_lines(path: Path, max_lines: int = 400) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    return lines[:max_lines]


def _manifest_summary(root: Path) -> dict:
    info: dict = {"root": str(root)}
    for name in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml"):
        p = root / name
        if p.exists():
            info["manifest"] = name
            if name == "package.json":
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    info["name"] = data.get("name")
                    info["scripts"] = list((data.get("scripts") or {}).keys())[:12]
                except (json.JSONDecodeError, OSError):
                    pass
            break
    return info


def cmd_analyze(project: Path, keywords: list[str], focus: str | None) -> dict:
    hits: list[dict] = []
    kw_lower = [k.lower() for k in keywords if k.strip()]
    for fp in _iter_files(project, focus):
        rel = fp.relative_to(project).as_posix()
        lines = _read_lines(fp)
        matched: list[dict] = []
        for i, line in enumerate(lines, start=1):
            low = line.lower()
            for kw in kw_lower:
                if kw in low:
                    matched.append({"line": i, "text": line.strip()[:200], "keyword": kw})
                    break
        if matched:
            hits.append(
                {
                    "path": rel,
                    "matches": matched[:8],
                    "preview": "\n".join(lines[:15])[:800],
                }
            )
    hits.sort(key=lambda h: len(h["matches"]), reverse=True)
    return {
        "command": "analyze",
        "project": str(project),
        "focus": focus,
        "keywords": keywords,
        "manifest": _manifest_summary(project),
        "candidates": hits[:25],
    }


def _parse_expand_query(query: str) -> tuple[str, int | None, int | None]:
    # path or path:start-end
    m = re.match(r"^([^:|]+)(?::(\d+)(?:-(\d+))?)?$", query.strip())
    if not m:
        return query.strip(), None, None
    path, start, end = m.group(1), m.group(2), m.group(3)
    if start and end:
        return path, int(start), int(end)
    if start:
        s = int(start)
        return path, max(1, s - 20), s + 80
    return path, None, None


def cmd_explore(
    project: Path,
    mode: str,
    query: str,
    direction: str = "both",
    max_depth: int = 3,
) -> dict:
    if mode == "expand":
        rel, start, end = _parse_expand_query(query)
        fp = project / rel
        lines = _read_lines(fp, max_lines=2000)
        if start is not None and end is not None:
            chunk = lines[start - 1 : end]
            text = "\n".join(f"{start + i}:{ln}" for i, ln in enumerate(chunk))
        else:
            text = "\n".join(f"{i+1}:{ln}" for i, ln in enumerate(lines[:120]))
        return {"command": "explore", "mode": "expand", "path": rel, "content": text[:12000]}

    if mode == "search":
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        results: list[dict] = []
        for fp in _iter_files(project):
            rel = fp.relative_to(project).as_posix()
            for i, line in enumerate(_read_lines(fp), start=1):
                if pattern.search(line):
                    results.append({"path": rel, "line": i, "text": line.strip()[:200]})
                    if len(results) >= 40:
                        break
            if len(results) >= 40:
                break
        return {"command": "explore", "mode": "search", "query": query, "results": results}

    if mode == "trace":
        symbol = query.strip()
        import_re = re.compile(
            rf"(?:import\s+.*\b{re.escape(symbol)}\b|from\s+['\"][^'\"]+['\"]|require\(['\"][^'\"]+['\"]\))"
        )
        def_re = re.compile(rf"(?:function|const|class|def|async\s+function)\s+{re.escape(symbol)}\b")
        refs: list[dict] = []
        definitions: list[dict] = []
        for fp in _iter_files(project):
            rel = fp.relative_to(project).as_posix()
            for i, line in enumerate(_read_lines(fp), start=1):
                if def_re.search(line):
                    definitions.append({"path": rel, "line": i, "text": line.strip()[:200]})
                elif symbol in line:
                    refs.append({"path": rel, "line": i, "text": line.strip()[:200]})
        # shallow import graph from definition files
        graph: list[dict] = []
        seen = set()
        q: deque[tuple[str, int]] = deque((d["path"], 0) for d in definitions[:3])
        while q and len(graph) < 30:
            rel, depth = q.popleft()
            if depth > max_depth or rel in seen:
                continue
            seen.add(rel)
            fp = project / rel
            for i, line in enumerate(_read_lines(fp, 200), start=1):
                if "import " in line or "require(" in line:
                    graph.append({"path": rel, "line": i, "import": line.strip()[:200]})
        return {
            "command": "explore",
            "mode": "trace",
            "symbol": symbol,
            "definitions": definitions[:10],
            "references": refs[:20],
            "imports": graph,
            "direction": direction,
            "max_depth": max_depth,
        }

    raise SystemExit(f"Unknown explore mode: {mode}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SuperPmAgent code-context CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Keyword scan + manifest summary")
    p_an.add_argument("--project", required=True)
    p_an.add_argument("--keywords", required=True, help="Comma-separated keywords")
    p_an.add_argument("--focus", default=None, help="Optional subdirectory")

    p_ex = sub.add_parser("explore", help="expand | search | trace")
    p_ex.add_argument("--project", required=True)
    p_ex.add_argument("--mode", required=True, choices=["expand", "search", "trace"])
    p_ex.add_argument("--query", required=True)
    p_ex.add_argument("--direction", default="both", choices=["in", "out", "both"])
    p_ex.add_argument("--max-depth", type=int, default=3)

    args = parser.parse_args()
    project = Path(args.project).resolve()
    if not project.is_dir():
        print(json.dumps({"error": f"Not a directory: {project}"}), file=sys.stderr)
        sys.exit(1)

    if args.cmd == "analyze":
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        out = cmd_analyze(project, kws, args.focus)
    else:
        out = cmd_explore(project, args.mode, args.query, args.direction, args.max_depth)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

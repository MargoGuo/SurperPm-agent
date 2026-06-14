"""MCP Server management — reads/writes knowledge/mcp/servers.json."""

import asyncio
import json as _json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth

router = APIRouter()
_logger = logging.getLogger(__name__)


def _mcp_root() -> Path:
    from app.services.knowledge_store import get_store

    store = get_store()
    root = store._root.parent / "mcp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _servers_file() -> Path:
    return _mcp_root() / "servers.json"


def _read_servers() -> dict:
    f = _servers_file()
    if not f.is_file():
        return {}
    try:
        data = _json.loads(f.read_text(encoding="utf-8"))
        return data.get("servers", {}) if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _write_servers(servers: dict) -> None:
    f = _servers_file()
    f.write_text(
        _json.dumps({"servers": servers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _plugin_root() -> Path | None:
    from app.services.knowledge_store import get_store

    store = get_store()
    knowledge_plugins = store._root.parent / "plugins"
    if knowledge_plugins.is_dir():
        return knowledge_plugins
    from app.config import settings

    if settings.plugin_repo_path:
        p = Path(settings.plugin_repo_path)
        if p.is_dir():
            return p
    return None


def _discover_from_plugins() -> list[dict]:
    root = _plugin_root()
    if not root:
        return []

    discovered: list[dict] = []
    for plugin_dir in sorted(root.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        mcp_json = plugin_dir / ".mcp.json"
        if not mcp_json.is_file():
            continue
        try:
            data = _json.loads(mcp_json.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        raw = data.get("mcpServers", {}) if isinstance(data, dict) else {}
        for name, cfg in raw.items():
            if not isinstance(cfg, dict):
                continue
            discovered.append({
                "name": name,
                "transport": cfg.get("type", "stdio"),
                "command": cfg.get("command"),
                "args": cfg.get("args", []),
                "env": cfg.get("env", {}),
                "url": cfg.get("url"),
                "headers": cfg.get("headers", {}),
                "plugin_source": plugin_dir.name,
            })
    return discovered


class MCPServerCreate(BaseModel):
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] | None = None
    env: dict | None = None
    url: str | None = None
    headers: dict | None = None


class MCPImportBody(BaseModel):
    json_text: str


@router.get("/servers")
async def list_servers(
    workspace_id: str,
    _user: dict = Depends(require_auth),
):
    manual = _read_servers()
    discovered = _discover_from_plugins()
    result = []

    for name, cfg in manual.items():
        result.append({
            "name": name,
            "enabled": cfg.get("enabled", True),
            **{k: v for k, v in cfg.items() if k != "enabled"},
            "source": "manual",
        })

    manual_names = set(manual.keys())
    for d in discovered:
        if d["name"] not in manual_names:
            result.append({**d, "enabled": False, "source": "plugin"})

    return result


@router.post("/servers", status_code=201)
async def create_server(
    workspace_id: str,
    body: MCPServerCreate,
    _user: dict = Depends(require_auth),
):
    servers = _read_servers()
    if body.name in servers:
        raise HTTPException(
            status_code=409,
            detail=f"Server '{body.name}' already exists",
        )
    servers[body.name] = {
        "transport": body.transport,
        "command": body.command,
        "args": body.args or [],
        "env": body.env or {},
        "url": body.url,
        "headers": body.headers or {},
        "enabled": True,
    }
    _write_servers(servers)
    return {"ok": True, "name": body.name}


@router.patch("/servers/{name}")
async def update_server(
    workspace_id: str,
    name: str,
    body: dict,
    _user: dict = Depends(require_auth),
):
    servers = _read_servers()
    if name not in servers:
        servers[name] = {"transport": "stdio", "enabled": True}
    servers[name].update(body)
    _write_servers(servers)
    return {"ok": True, "name": name, **servers[name]}


@router.delete("/servers/{name}", status_code=204)
async def delete_server(
    workspace_id: str,
    name: str,
    _user: dict = Depends(require_auth),
):
    servers = _read_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail="Server not found")
    del servers[name]
    _write_servers(servers)


@router.post("/import", status_code=201)
async def import_from_json(
    workspace_id: str,
    body: MCPImportBody,
    _user: dict = Depends(require_auth),
):
    try:
        raw = _json.loads(body.json_text)
    except _json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON: {e}",
        ) from None

    mcp_servers = {}
    if isinstance(raw, dict):
        mcp_servers = raw.get("mcpServers", raw)

    if not isinstance(mcp_servers, dict) or not mcp_servers:
        raise HTTPException(
            status_code=400,
            detail="No mcpServers found in JSON",
        )

    servers = _read_servers()
    imported = []
    for name, cfg in mcp_servers.items():
        if not isinstance(cfg, dict):
            continue
        servers[name] = {
            "transport": cfg.get("type", "stdio"),
            "command": cfg.get("command"),
            "args": cfg.get("args", []),
            "env": cfg.get("env", {}),
            "url": cfg.get("url"),
            "headers": cfg.get("headers", {}),
            "enabled": True,
        }
        imported.append(name)
    _write_servers(servers)
    return {"ok": True, "imported": imported, "count": len(imported)}


@router.post("/discover")
async def discover_servers(
    workspace_id: str,
    _user: dict = Depends(require_auth),
):
    discovered = _discover_from_plugins()
    if not discovered:
        return {"ok": True, "discovered": 0, "servers": []}

    servers = _read_servers()
    new_names = []
    for d in discovered:
        name = d["name"]
        if name not in servers:
            servers[name] = {
                "transport": d["transport"],
                "command": d.get("command"),
                "args": d.get("args", []),
                "env": d.get("env", {}),
                "url": d.get("url"),
                "headers": d.get("headers", {}),
                "enabled": True,
                "plugin_source": d.get("plugin_source"),
            }
            new_names.append(name)
    _write_servers(servers)
    return {
        "ok": True,
        "discovered": len(new_names),
        "servers": new_names,
    }


@router.post("/servers/{name}/test")
async def test_server(
    workspace_id: str,
    name: str,
    _user: dict = Depends(require_auth),
):
    servers = _read_servers()
    srv = servers.get(name)
    if not srv:
        discovered = _discover_from_plugins()
        for d in discovered:
            if d["name"] == name:
                srv = d
                break
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    transport = srv.get("transport", "stdio")
    if transport == "stdio":
        return await _test_stdio(srv)
    return await _test_http(srv)


async def _test_stdio(srv: dict) -> dict:
    cmd = srv.get("command")
    if not cmd:
        return {"ok": False, "error": "No command configured"}
    args = srv.get("args", [])
    if isinstance(args, str):
        args = _json.loads(args)
    env_extra = srv.get("env", {})
    if isinstance(env_extra, str):
        env_extra = _json.loads(env_extra)

    import os

    env = {**os.environ, **env_extra}
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(
                proc.communicate(b""), timeout=5,
            )
        except TimeoutError:
            proc.kill()
            return {
                "ok": True,
                "message": "Process started (killed after 5s)",
            }
        if proc.returncode == 0:
            return {"ok": True, "message": "Process exited cleanly"}
        return {
            "ok": False,
            "error": f"Exit {proc.returncode}: {stderr.decode()[:200]}",
        }
    except FileNotFoundError:
        return {"ok": False, "error": f"Command not found: {cmd}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _test_http(srv: dict) -> dict:
    import httpx

    url = srv.get("url", "")
    if not url:
        return {"ok": False, "error": "No URL configured"}
    hdrs = srv.get("headers", {})
    if isinstance(hdrs, str):
        hdrs = _json.loads(hdrs)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, headers=hdrs)
            return {
                "ok": r.status_code < 400,
                "status": r.status_code,
                "message": f"HTTP {r.status_code}",
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}

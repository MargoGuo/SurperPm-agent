"""Asyncio locks — serialises goal executions per key (workspace or goal)."""
import asyncio

_locks: dict[str, asyncio.Lock] = {}


def get_lock(key: str) -> asyncio.Lock:
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]

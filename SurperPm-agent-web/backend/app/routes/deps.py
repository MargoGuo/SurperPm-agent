"""Shared route dependencies — auth, session, etc."""

from typing import Annotated

from fastapi import Cookie, HTTPException

from app.services import session as session_svc


async def require_auth(
    SuperPmAgent_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    if not SuperPmAgent_session:
        raise HTTPException(status_code=401, detail="not_logged_in")
    data = session_svc.decode(SuperPmAgent_session)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_session")
    return data

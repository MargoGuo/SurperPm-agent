"""Session cookie helpers — itsdangerous-signed payloads."""
import logging
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

_SECRET = settings.SuperPmAgent_secret or "SuperPmAgent-dev-secret-change-in-prod"
if not settings.SuperPmAgent_secret:
    logging.warning("SuperPmAgent_SECRET not set — using dev secret. Set it in .env for production.")

_serializer = URLSafeSerializer(_SECRET, salt="SuperPmAgent.session")


def encode(payload: dict) -> str:
    return _serializer.dumps(payload)


def decode(token: str) -> dict:
    try:
        result = _serializer.loads(token)
    except BadSignature:
        return {}
    if not isinstance(result, dict):
        return {}
    return result

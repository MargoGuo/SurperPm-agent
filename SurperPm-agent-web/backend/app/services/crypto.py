"""Fernet encryption helper for secret storage."""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_DEV_KEY = "SuperPmAgent-dev-key-do-not-use-in-production"


def _get_fernet() -> Fernet:
    """Build a Fernet instance from settings.secret_key.

    Derives a 32-byte key via SHA-256 hash, then base64-encodes it for Fernet.
    If secret_key is empty, falls back to a default dev key with a warning.
    """
    raw_key = settings.secret_key
    if not raw_key:
        logger.warning(
            "secret_key is empty — using default dev key. "
            "Set SECRET_KEY env var for production!"
        )
        raw_key = _DEFAULT_DEV_KEY

    # Derive 32 bytes via SHA-256
    key_bytes = hashlib.sha256(raw_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a string."""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode())
    return token.decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string and return the plaintext."""
    f = _get_fernet()
    plaintext = f.decrypt(ciphertext.encode())
    return plaintext.decode()

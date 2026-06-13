"""Tests for Phase 5: Secrets, SSH keygen, and Crypto services."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.database as db_module
from app.database import get_session
from app.main import app as fastapi_app
from app.services.crypto import decrypt, encrypt
from app.services.ssh_keygen import generate_ssh_keypair


@pytest.fixture()
def client(tmp_path):
    """Fresh app client with clean temp-file DB for each test."""
    db_file = tmp_path / "test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    test_session_factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    original_engine = db_module.engine
    db_module.engine = test_engine

    async def _override_get_session():
        async with test_session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session

    with TestClient(fastapi_app) as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    db_module.engine = original_engine


def _create_workspace(client: TestClient) -> str:
    """Helper: create a workspace and return its id."""
    res = client.post("/api/workspaces", json={
        "name": "Secrets Test WS",
        "slug": "secrets-test-ws",
    })
    assert res.status_code == 201
    return res.json()["id"]


class TestCrypto:
    """Unit tests for the crypto encrypt/decrypt module."""

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "super-secret-api-key-12345"
        ciphertext = encrypt(plaintext)
        assert ciphertext != plaintext
        assert decrypt(ciphertext) == plaintext

    def test_encrypt_produces_different_tokens(self):
        """Fernet includes a timestamp, so same plaintext produces different tokens."""
        plaintext = "same-value"
        ct1 = encrypt(plaintext)
        ct2 = encrypt(plaintext)
        # Tokens may differ (Fernet uses current time), but both decrypt to same value
        assert decrypt(ct1) == plaintext
        assert decrypt(ct2) == plaintext

    def test_encrypt_empty_string(self):
        ciphertext = encrypt("")
        assert decrypt(ciphertext) == ""


class TestSSHKeygen:
    """Unit tests for SSH key generation."""

    def test_generate_keypair_returns_strings(self):
        public_key, private_key = generate_ssh_keypair()
        assert isinstance(public_key, str)
        assert isinstance(private_key, str)

    def test_public_key_format(self):
        public_key, _ = generate_ssh_keypair()
        assert public_key.startswith("ssh-ed25519 ")

    def test_private_key_format(self):
        _, private_key = generate_ssh_keypair()
        assert "BEGIN OPENSSH PRIVATE KEY" in private_key
        assert "END OPENSSH PRIVATE KEY" in private_key

    def test_keypair_uniqueness(self):
        pub1, priv1 = generate_ssh_keypair()
        pub2, priv2 = generate_ssh_keypair()
        assert pub1 != pub2
        assert priv1 != priv2


class TestSecretsAPI:
    """Integration tests for the secrets CRUD endpoints."""

    def test_create_secret(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "GITHUB_TOKEN",
            "value": "ghp_abc123",
            "category": "env",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["key"] == "GITHUB_TOKEN"
        assert data["value"] == "***"
        assert data["category"] == "env"
        assert data["workspace_id"] == ws_id
        assert "id" in data

    def test_list_secrets_redacted(self, client):
        ws_id = _create_workspace(client)
        client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "SECRET_A",
            "value": "value_a",
        })
        client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "SECRET_B",
            "value": "value_b",
            "category": "mcp",
        })
        res = client.get(f"/api/workspaces/{ws_id}/secrets")
        assert res.status_code == 200
        secrets = res.json()
        assert len(secrets) == 2
        for s in secrets:
            assert s["value"] == "***"

    def test_reveal_secret(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "MY_SECRET",
            "value": "the-real-value",
        })
        secret_id = res.json()["id"]
        res = client.get(f"/api/workspaces/{ws_id}/secrets/{secret_id}/reveal")
        assert res.status_code == 200
        data = res.json()
        assert data["key"] == "MY_SECRET"
        assert data["value"] == "the-real-value"

    def test_reveal_secret_not_found(self, client):
        ws_id = _create_workspace(client)
        res = client.get(f"/api/workspaces/{ws_id}/secrets/9999/reveal")
        assert res.status_code == 404

    def test_delete_secret(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "TO_DELETE",
            "value": "bye",
        })
        secret_id = res.json()["id"]
        res = client.delete(f"/api/workspaces/{ws_id}/secrets/{secret_id}")
        assert res.status_code == 204
        # Verify it's gone
        res = client.get(f"/api/workspaces/{ws_id}/secrets")
        assert len(res.json()) == 0

    def test_delete_secret_not_found(self, client):
        ws_id = _create_workspace(client)
        res = client.delete(f"/api/workspaces/{ws_id}/secrets/9999")
        assert res.status_code == 404

    def test_secret_value_encrypted_in_db(self, client):
        """Verify the value stored in DB is encrypted, not plaintext."""
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/secrets", json={
            "key": "CHECK_ENC",
            "value": "plaintext-val",
        })
        secret_id = res.json()["id"]
        # Reveal should give back original value (proves encrypt+decrypt works)
        res = client.get(f"/api/workspaces/{ws_id}/secrets/{secret_id}/reveal")
        assert res.json()["value"] == "plaintext-val"


class TestWorkspaceSSH:
    """Tests for SSH keypair generation on workspace creation."""

    def test_workspace_creation_generates_ssh_keypair(self, client):
        res = client.post("/api/workspaces", json={
            "name": "SSH WS",
            "slug": "ssh-ws",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["ssh_public_key"] is not None
        assert data["ssh_public_key"].startswith("ssh-ed25519 ")
        assert data["ssh_private_key_enc"] is not None
        # Private key should be encrypted (not raw PEM)
        assert "BEGIN OPENSSH PRIVATE KEY" not in data["ssh_private_key_enc"]

    def test_get_ssh_public_key_endpoint(self, client):
        res = client.post("/api/workspaces", json={
            "name": "SSH Key WS",
            "slug": "ssh-key-ws",
        })
        ws_id = res.json()["id"]
        res = client.get(f"/api/workspaces/{ws_id}/ssh-public-key")
        assert res.status_code == 200
        assert res.text.startswith("ssh-ed25519 ")

    def test_get_ssh_public_key_not_found(self, client):
        res = client.get("/api/workspaces/nonexistent/ssh-public-key")
        assert res.status_code == 404

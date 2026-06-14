"""SSH key pair generation using Ed25519 via system ssh-keygen."""

import subprocess
import tempfile
from pathlib import Path

from app.services.platform import find_ssh_keygen


def generate_ssh_keypair() -> tuple[str, str]:
    """Generate an Ed25519 SSH key pair using system ssh-keygen.

    Returns:
        (public_key, private_key) as OpenSSH-formatted strings.
    """
    ssh_keygen = find_ssh_keygen()
    tmp = Path(tempfile.mkdtemp())
    keyfile = tmp / "id_ed25519"

    try:
        result = subprocess.run(
            [ssh_keygen, "-t", "ed25519", "-f", str(keyfile), "-N", "", "-C", "SuperPmAgent"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed: {result.stderr.strip()}")

        private_key = keyfile.read_text()
        public_key = (tmp / "id_ed25519.pub").read_text().strip()

        return public_key, private_key
    finally:
        for f in tmp.glob("id_ed25519*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass

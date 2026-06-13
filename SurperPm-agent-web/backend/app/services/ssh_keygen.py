"""SSH key pair generation using Ed25519."""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_ssh_keypair() -> tuple[str, str]:
    """Generate an Ed25519 SSH key pair.

    Returns:
        (public_key, private_key) as OpenSSH-formatted strings.
    """
    private_key = Ed25519PrivateKey.generate()

    # Serialize private key in OpenSSH format (no passphrase)
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key in OpenSSH format
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    return public_key_bytes.decode(), private_key_bytes.decode()

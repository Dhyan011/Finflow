import hashlib
import hmac
import os


def _secret() -> str:
    return os.environ.get("HMAC_SECRET", "change-me-in-production")


def generate_signature(payload: str, timestamp: str, nonce: str) -> str:
    """Generate HMAC-SHA256 signature for payload + timestamp + nonce."""
    message = f"{payload}{timestamp}{nonce}"
    return hmac.new(
        _secret().encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

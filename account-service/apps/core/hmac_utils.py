import hashlib
import hmac
import os


def _secret() -> str:
    return os.environ.get("HMAC_SECRET", "change-me-in-production")


def generate_signature(payload: str) -> str:
    """Generate HMAC-SHA256 signature for a payload string."""
    return hmac.new(
        _secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

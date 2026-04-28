import hashlib
import hmac
import os


def _secret() -> str:
    return os.environ.get("HMAC_SECRET", "dev-secret")


def generate_signature(payload: str) -> str:
    """Generate HMAC-SHA256 signature for a payload string."""
    return hmac.new(
        _secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: str, signature: str) -> bool:
    """Constant-time comparison to verify HMAC signature."""
    expected = generate_signature(payload)
    return hmac.compare_digest(expected, signature)

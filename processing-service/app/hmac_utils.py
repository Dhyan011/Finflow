import hashlib
import hmac
import os
import time

_nonce_cache: dict[str, float] = {}


def _secret() -> str:
    return os.environ.get("HMAC_SECRET", "dev-secret")


def generate_signature(payload: str, timestamp: str, nonce: str) -> str:
    """Generate HMAC-SHA256 signature for payload + timestamp + nonce."""
    message = f"{payload}{timestamp}{nonce}"
    return hmac.new(
        _secret().encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: str, signature: str, timestamp: str, nonce: str) -> bool:
    """Constant-time comparison to verify HMAC signature with timestamp and nonce checks."""
    try:
        ts = float(timestamp)
    except ValueError:  # pragma: no cover
        return False
        
    now = time.time()
    
    # 1. Stale timestamp (> 5 minutes)
    if abs(now - ts) > 300:
        return False
        
    # 2. Reused nonce
    if nonce in _nonce_cache:
        return False
        
    # 3. Bad signature
    expected = generate_signature(payload, timestamp, nonce)
    if not hmac.compare_digest(expected, signature):
        return False
        
    # Valid! Store nonce
    _nonce_cache[nonce] = now
    
    # Cleanup old nonces (naive approach for a 5-day project)
    if len(_nonce_cache) > 1000:  # pragma: no cover
        stale_keys = [k for k, v in _nonce_cache.items() if now - v > 300]
        for k in stale_keys:
            _nonce_cache.pop(k, None)
            
    return True

import copy
from typing import Any

from django.db import transaction

from apps.core.models import AuditLog


def _scrub_pii(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    pii_keys = {'password', 'token', 'email', 'authorization'}
    scrubbed = copy.deepcopy(data)
    for key in list(scrubbed.keys()):
        if key in pii_keys:
            scrubbed.pop(key, None)
    return scrubbed


def log_audit(
    user,
    action: str,
    resource_type: str,
    resource_id,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request=None,
) -> None:
    ip_address = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')

    # Run outside of atomic block if possible, or append to it
    def _create_log():
        AuditLog.objects.create(
            user=user if user and getattr(user, 'is_authenticated', False) else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=_scrub_pii(before),
            after_state=_scrub_pii(after),
            ip_address=ip_address,
        )

    transaction.on_commit(_create_log)

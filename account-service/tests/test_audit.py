from apps.core.audit import _scrub_pii, log_audit
from apps.core.models import AuditLog
from tests.factories import UserFactory
import pytest

@pytest.mark.django_db(transaction=True)
def test_log_audit_creates_record(client):
    user = UserFactory()
    
    # We pass a dummy request object
    class DummyRequest:
        META = {'REMOTE_ADDR': '127.0.0.1'}
        
    request = DummyRequest()
    
    log_audit(
        user=user,
        action="CREATE",
        resource_type="TestResource",
        resource_id="00000000-0000-0000-0000-000000000000",
        before={"status": "old", "password": "secret_password"},
        after={"status": "new", "email": "test@example.com"},
        request=request
    )
    
    # Since we are using transaction=True, the transaction will be committed at the end of the atomic block,
    # but since this is not in an explicit transaction atomic block in the test,
    # it may trigger immediately, or we can just force the callback if we have to.
    # Wait, in pytest-django with transaction=True, on_commit is executed.
    
    # Actually, if we're not inside atomic block in the test, on_commit just executes immediately.
    assert AuditLog.objects.count() == 1
    
    log = AuditLog.objects.first()
    assert log.action == "CREATE"
    assert log.resource_type == "TestResource"
    assert log.ip_address == "127.0.0.1"
    
    # Verify PII scrubbing
    assert "password" not in log.before_state
    assert log.before_state["status"] == "old"
    
    assert "email" not in log.after_state
    assert log.after_state["status"] == "new"

def test_scrub_pii():
    data = {
        "normal_key": "value",
        "password": "secret",
        "token": "jwt",
        "email": "a@b.com",
        "authorization": "Bearer token"
    }
    
    scrubbed = _scrub_pii(data)
    
    assert scrubbed == {"normal_key": "value"}
    assert _scrub_pii(None) is None

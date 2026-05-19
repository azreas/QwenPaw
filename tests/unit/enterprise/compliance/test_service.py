from qwenpaw.enterprise.compliance.models import ComplianceExportFormat
from qwenpaw.enterprise.compliance.service import audit_rows_to_json, audit_rows_to_csv


class Row:
    id = "1"
    event_type = "auth.login_success"
    action = "login"
    outcome = "success"
    tenant_id = "tenant"
    actor_id = "admin"
    resource_type = "auth"
    resource_id = "login"
    request_id = "req"
    trace_id = "trace"
    payload = {"token": "secret", "safe": "ok"}
    created_at = "2026-05-10T00:00:00Z"


def test_audit_rows_to_json_redacts_payload():
    content, media_type, filename = audit_rows_to_json([Row()])

    assert media_type == "application/json"
    assert filename.endswith(".json")
    assert '"token": "***"' in content
    assert '"safe": "ok"' in content


def test_audit_rows_to_csv_contains_headers():
    content, media_type, filename = audit_rows_to_csv([Row()])

    assert media_type == "text/csv"
    assert filename.endswith(".csv")
    assert "event_type,action,outcome" in content
    assert "auth.login_success,login,success" in content


def test_audit_rows_to_json_empty():
    content, media_type, filename = audit_rows_to_json([])

    assert media_type == "application/json"
    assert content == "[]"


def test_audit_rows_to_csv_empty():
    content, media_type, filename = audit_rows_to_csv([])

    assert media_type == "text/csv"
    # CSV 有 header 但无数据行
    assert "event_type" in content

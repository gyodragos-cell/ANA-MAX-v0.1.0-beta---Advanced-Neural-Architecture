from __future__ import annotations

import json
from pathlib import Path

from os29.redaction import redact_value, sanitize_url
from os29.scope import ScopePolicy


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "lab_scope.json"


def test_redaction_masks_sensitive_keys_and_bearer_text():
    value = {
        "Authorization": "Bearer very-secret-token-value",
        "headers": {"X-API-Key": "key-123", "Content-Type": "application/json"},
        "message": "request failed with access_token=secret123",
        "count": 3,
    }
    cleaned, count = redact_value(value)
    encoded = json.dumps(cleaned)
    assert count >= 3
    assert "very-secret-token-value" not in encoded
    assert "key-123" not in encoded
    assert "secret123" not in encoded
    assert cleaned["count"] == 3
    assert cleaned["headers"]["Content-Type"] == "application/json"


def test_url_removes_userinfo_and_redacts_sensitive_query():
    cleaned, count = sanitize_url("https://user:pass@example.test/v1?api_key=abc123&region=eu")
    assert count >= 1
    assert "user" not in cleaned and "pass" not in cleaned and "abc123" not in cleaned
    assert "example.test" in cleaned
    assert "region=eu" in cleaned


def test_scope_allows_only_explicit_loopback_host_and_port():
    policy = ScopePolicy(SCOPE)
    assert policy.check_target("http://127.0.0.1:8766/health")["allowed"] is True
    assert policy.check_target("http://localhost:8771/health")["allowed"] is True
    assert policy.check_target("http://127.0.0.1:8080/")["reason"] == "port_not_in_scope"
    assert policy.check_target("https://example.com/")["reason"] == "host_not_in_scope"
    assert policy.check_target("http://user:pass@127.0.0.1:8766/")["reason"] == "embedded_credentials_forbidden"


def test_frida_device_and_process_are_denied_until_explicitly_approved(tmp_path: Path):
    policy = ScopePolicy(SCOPE)
    device_result = policy.check_device("device-42")
    assert device_result["allowed"] is False
    assert device_result["reason"] == "device_not_explicitly_approved"

    process_result = policy.check_process("some-app.exe")
    assert process_result["allowed"] is False
    assert process_result["reason"] == "process_not_explicitly_approved"

    data = json.loads(SCOPE.read_text(encoding="utf-8"))
    data["approved_device_ids"] = ["device-42"]
    data["approved_process_names"] = ["sampleapp"]
    expanded = tmp_path / "approved-scope.json"
    expanded.write_text(json.dumps(data), encoding="utf-8")
    approved = ScopePolicy(expanded)
    assert approved.check_device("device-42")["allowed"] is True
    assert approved.check_device("device-43")["allowed"] is False
    assert approved.check_process("SampleApp")["allowed"] is True
    assert approved.check_process("otherapp")["allowed"] is False
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from os29 import frida_bridge


ROOT = Path(__file__).resolve().parents[1]


def test_frida_bridge_refuses_device_not_in_scope_before_enumeration(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "frida_bridge.py",
            "--device-id", "unapproved-device",
            "--pid", "1234",
            "--class-name", "example.app.ApiClient",
            "--method-name", "fetch",
            "--trace-id", "trace-test",
            "--scope", str(ROOT / "config" / "lab_scope.json"),
            "--db", str(ROOT / "data" / "must-not-be-created.db"),
        ],
    )
    with pytest.raises(SystemExit, match="device_not_explicitly_approved"):
        frida_bridge.main()
    assert not (ROOT / "data" / "must-not-be-created.db").exists()
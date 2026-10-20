from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

from os29 import cli


def test_experience_validation_requires_an_interactive_terminal(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(cli.sys, "stdout", SimpleNamespace(isatty=lambda: False))
    args = Namespace(
        db=str(tmp_path / "must-not-be-created.db"),
        lesson_id="candidate-1",
        verification_event_id="verification-1",
        confidence=0.8,
    )
    with pytest.raises(ValueError, match="interactive local terminal"):
        cli.cmd_experience_validate(args)
    assert not (tmp_path / "must-not-be-created.db").exists()
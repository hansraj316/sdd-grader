"""Mocked tests for the optional --api judge backend (issue #13). No live key needed."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from sddgrade import config as config_mod
from sddgrade.adapters.base import parse_sections
from sddgrade.engine.judge import JudgeUnavailable
from sddgrade.integrations.api import DEFAULT_MODEL, ApiJudge
from sddgrade.model import Artifact, ArtifactType


def _artifacts() -> list[Artifact]:
    text = "# Feature Specification: X\n\n- FR-001: The system shall do a thing.\n"
    return [Artifact(path="spec.md", type=ArtifactType.SPEC, feature_id="x",
                     raw=text, sections=parse_sections(text))]


def _fake_anthropic(response_text: str) -> types.ModuleType:
    """A stand-in `anthropic` module whose client returns `response_text`."""
    mod = types.ModuleType("anthropic")

    class _Block:
        type = "text"
        def __init__(self, t: str) -> None:
            self.text = t

    class _Msg:
        def __init__(self, t: str) -> None:
            self.content = [_Block(t)]

    class _Stream:
        def __init__(self, t: str) -> None:
            self._t = t
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get_final_message(self):
            return _Msg(self._t)

    class _Messages:
        def __init__(self, t: str) -> None:
            self._t = t
        def stream(self, **kwargs):
            return _Stream(self._t)

    class Anthropic:
        def __init__(self, *a, **k) -> None:
            self.messages = _Messages(response_text)

    mod.Anthropic = Anthropic
    return mod


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(JudgeUnavailable, match="ANTHROPIC_API_KEY"):
        ApiJudge(config_mod.Config()).judge(_artifacts(), Path("."))


def test_missing_sdk_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(sys.modules, "anthropic", None)  # import anthropic -> ImportError
    with pytest.raises(JudgeUnavailable, match="anthropic SDK not installed"):
        ApiJudge(config_mod.Config()).judge(_artifacts(), Path("."))


def test_invalid_json_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic("not json at all"))
    with pytest.raises(JudgeUnavailable, match="non-JSON"):
        ApiJudge(config_mod.Config()).judge(_artifacts(), Path("."))


def test_successful_mocked_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    payload = json.dumps({"findings": [{
        "artifact": "spec.md", "dimension": "clarity", "severity": "medium",
        "message": "ambiguous", "suggestion": "clarify", "pitfall_id": None,
    }]})
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic(payload))
    findings = ApiJudge(config_mod.Config()).judge(_artifacts(), Path("."))
    assert len(findings) == 1
    assert findings[0]["dimension"] == "clarity"


def test_model_default_and_override(monkeypatch):
    monkeypatch.delenv("SDDREVIEW_MODEL", raising=False)
    assert ApiJudge(config_mod.Config()).model == DEFAULT_MODEL
    monkeypatch.setenv("SDDREVIEW_MODEL", "claude-sonnet-4-6")
    assert ApiJudge(config_mod.Config()).model == "claude-sonnet-4-6"

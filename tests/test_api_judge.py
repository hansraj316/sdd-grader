"""Mocked tests for the optional --api judge backend (issue #13). No live key needed.

Also covers issue #41: an explicitly requested --api judge that fails must exit
non-zero with the failure reason, never silently degrade to a lint-only score.
"""

from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path

import pytest
from rich.console import Console

from sddgrade import config as config_mod
from sddgrade.adapters.base import parse_sections
from sddgrade.engine.judge import JudgeUnavailable
from sddgrade.integrations.api import DEFAULT_MODEL, ApiJudge
from sddgrade.model import Artifact, ArtifactType
from sddgrade.runner import EXIT_JUDGE_REQUIRED, run_review


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


def _raising_anthropic(exc: Exception) -> types.ModuleType:
    """A stand-in `anthropic` module whose client raises `exc` on the API call."""
    mod = types.ModuleType("anthropic")

    class _Messages:
        def stream(self, **kwargs):
            raise exc

    class Anthropic:
        def __init__(self, *a, **k) -> None:
            self.messages = _Messages()

    mod.Anthropic = Anthropic
    return mod


def test_api_error_surfaces_class_and_status(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    class FakeAuthError(Exception):
        status_code = 401

    monkeypatch.setitem(
        sys.modules, "anthropic", _raising_anthropic(FakeAuthError("invalid x-api-key"))
    )
    with pytest.raises(JudgeUnavailable) as excinfo:
        ApiJudge(config_mod.Config()).judge(_artifacts(), Path("."))
    msg = str(excinfo.value)
    assert "FakeAuthError" in msg
    assert "HTTP 401" in msg
    assert "invalid x-api-key" in msg


def test_model_default_and_override(monkeypatch):
    monkeypatch.delenv("SDDREVIEW_MODEL", raising=False)
    assert ApiJudge(config_mod.Config()).model == DEFAULT_MODEL
    monkeypatch.setenv("SDDREVIEW_MODEL", "claude-sonnet-4-6")
    assert ApiJudge(config_mod.Config()).model == "claude-sonnet-4-6"


# ------------------------------------------------- --api never silently degrades (#41)

def test_api_backend_missing_key_fails_run(monkeypatch, good_repo: Path):
    # `--api` without a key must NOT pass on a lint-only score: exit 3, clear message.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    buf = io.StringIO()
    code = run_review(
        good_repo, backend="api", fail_under=70, console=Console(file=buf)
    )
    assert code == EXIT_JUDGE_REQUIRED
    out = buf.getvalue()
    assert "ERROR" in out
    assert "ANTHROPIC_API_KEY" in out  # what failed
    assert "--api" in out  # what was requested
    assert "lint-only" in out  # what we refused to emit


def test_api_backend_api_error_fails_run_with_reason(monkeypatch, good_repo: Path):
    # A failing API call (auth, network, rate limit) surfaces class + status, exit 3.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-expired")

    class FakeAuthError(Exception):
        status_code = 401

    monkeypatch.setitem(
        sys.modules, "anthropic", _raising_anthropic(FakeAuthError("invalid x-api-key"))
    )
    buf = io.StringIO()
    code = run_review(
        good_repo, backend="api", fail_under=70, console=Console(file=buf)
    )
    assert code == EXIT_JUDGE_REQUIRED
    out = buf.getvalue()
    assert "FakeAuthError" in out and "HTTP 401" in out  # reason not swallowed


def test_api_backend_failure_json_is_labeled_lint_only(monkeypatch, good_repo: Path, capsys):
    # Even the JSON emitted alongside the failure never claims lint+semantic coverage.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code = run_review(
        good_repo, backend="api", json_out=True, fail_under=70,
        console=Console(file=io.StringIO()),
    )
    assert code == EXIT_JUDGE_REQUIRED
    captured = capsys.readouterr()
    data = json.loads(captured.out)  # stdout stays pure, parseable JSON
    assert data["engine"] == "rules"
    assert data["coverage"] == "lint-only"
    assert data["judge_used"] is False
    assert "ANTHROPIC_API_KEY" in captured.err  # reason on stderr, not swallowed


def test_api_backend_success_passes_with_semantic_coverage(monkeypatch, good_repo: Path, capsys):
    # When the API judge runs, --api behaves as before: exit 0, lint+semantic coverage.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(
        sys.modules, "anthropic", _fake_anthropic(json.dumps({"findings": []}))
    )
    code = run_review(
        good_repo, backend="api", json_out=True, fail_under=70,
        console=Console(file=io.StringIO()),
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["engine"] == "api"
    assert data["coverage"] == "lint+semantic"


def test_agent_backend_still_degrades_quietly(good_repo: Path):
    # The forgiving default is unchanged: agent backend without judge.json degrades
    # to rules with a yellow notice (no --require-judge, no --api → no hard failure).
    buf = io.StringIO()
    code = run_review(good_repo, backend="agent", fail_under=70, console=Console(file=buf))
    assert code == 0
    assert "Judge unavailable" in buf.getvalue()

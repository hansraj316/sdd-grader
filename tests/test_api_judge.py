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
from sddgrade.discovery import discover_artifacts
from sddgrade.engine.judge import JudgeUnavailable
from sddgrade.integrations.api import (
    DEFAULT_MODEL,
    INPUT_BUDGET_CHARS,
    ApiJudge,
    truncate_to_budget,
)
from sddgrade.model import Artifact, ArtifactType
from sddgrade.runner import EXIT_JUDGE_REQUIRED, run_review


def _artifacts() -> list[Artifact]:
    text = "# Feature Specification: X\n\n- FR-001: The system shall do a thing.\n"
    return [Artifact(path="spec.md", type=ArtifactType.SPEC, feature_id="x",
                     raw=text, sections=parse_sections(text))]


def _fake_anthropic(response_text: str) -> types.ModuleType:
    """A stand-in `anthropic` module whose client returns `response_text`.

    Every `messages.stream(**kwargs)` call is recorded in `mod.calls` so tests can
    inspect the exact prompt the judge sent (e.g. for truncation markers).
    """
    mod = types.ModuleType("anthropic")
    mod.calls = []

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
            mod.calls.append(kwargs)
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
    # No injected console: err_console defaults to real stderr, json goes to stdout.
    code = run_review(good_repo, backend="api", json_out=True, fail_under=70)
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


# ------------------------------------------------- input budget & cost control (#52)

def _artifact(path: str, raw: str) -> Artifact:
    return Artifact(path=path, type=ArtifactType.SPEC, feature_id="x",
                    raw=raw, sections=parse_sections(raw))


def test_truncate_noop_under_budget():
    arts = [_artifact("specs/a/spec.md", "line one\nline two\n")]
    out, truncated = truncate_to_budget(arts, budget=1_000)
    assert truncated == []
    assert out[0].raw == arts[0].raw


def test_truncate_largest_first_with_marker():
    small = _artifact("specs/a/spec.md", "small artifact\n" * 3)
    big = _artifact("specs/b/spec.md", ("x" * 9 + "\n") * 100)  # 1000 chars, 100 lines
    out, truncated = truncate_to_budget([small, big], budget=300)
    assert out[0].raw == small.raw  # smaller artifact untouched
    assert len(truncated) == 1
    t = truncated[0]
    assert t.label == "specs/b/spec.md"
    assert t.total_lines == 100
    assert 0 < t.shown_lines < 100
    assert f"[truncated: showing first {t.shown_lines} of 100 lines]" in out[1].raw
    assert len(out[1].raw) < len(big.raw)


def test_truncate_multiple_large_share_cut_equally():
    # Water-filling: the two big artifacts absorb the whole cut, the tiny one is
    # untouched, and both big ones end up at the same cap.
    a = _artifact("specs/a/spec.md", ("a" * 9 + "\n") * 40)  # 400 chars
    b = _artifact("specs/b/spec.md", ("b" * 9 + "\n") * 40)  # 400 chars
    c = _artifact("specs/c/spec.md", "tiny\n")
    out, truncated = truncate_to_budget([a, b, c], budget=205)
    assert {t.label for t in truncated} == {"specs/a/spec.md", "specs/b/spec.md"}
    assert out[2].raw == "tiny\n"
    assert truncated[0].shown_lines == truncated[1].shown_lines


def test_api_judge_under_budget_sends_untruncated(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake = _fake_anthropic(json.dumps({"findings": []}))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    arts = _artifacts()
    judge = ApiJudge(config_mod.Config())
    judge.judge(arts, Path("."))
    prompt = fake.calls[0]["messages"][0]["content"]
    assert arts[0].raw in prompt          # full artifact text, verbatim
    assert "[truncated" not in prompt
    assert judge.notes == []
    err = capsys.readouterr().err
    assert "--api input:" in err          # size diagnostic always printed
    assert "notice:" not in err


def test_api_judge_over_budget_truncates_with_marker_and_notice(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake = _fake_anthropic(json.dumps({"findings": []}))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    big_raw = "This spec line is plain filler for the budget test.\n" * 4_000  # ~208k chars
    small_raw = "# Feature Specification: small\n\n- FR-001: The system logs events.\n"
    assert len(big_raw) + len(small_raw) > INPUT_BUDGET_CHARS
    arts = [_artifact("specs/big/spec.md", big_raw), _artifact("specs/small/spec.md", small_raw)]
    judge = ApiJudge(config_mod.Config())
    judge.judge(arts, Path("."))
    prompt = fake.calls[0]["messages"][0]["content"]
    assert "[truncated: showing first" in prompt   # marker visible to the judge
    assert small_raw in prompt                     # small artifact untouched
    assert len(prompt) < len(big_raw)              # input actually shrank
    # Partial coverage is recorded, never silent.
    assert judge.notes and "truncated" in judge.notes[0]
    assert "specs/big/spec.md" in judge.notes[0]
    err = capsys.readouterr().err
    assert "--api input:" in err
    assert "notice:" in err
    assert "specs/big/spec.md" in err                  # what was truncated
    assert "sddgrade review specs/<feature>" in err    # how to narrow the review


def test_run_review_reflects_partial_coverage(monkeypatch, good_repo: Path, capsys):
    # Over-budget corpus through the full pipeline: JSON report carries the note.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(
        sys.modules, "anthropic", _fake_anthropic(json.dumps({"findings": []}))
    )
    spec = good_repo / "specs" / "001-task-export" / "spec.md"
    spec.write_text(
        spec.read_text() + "Filler content line for the input budget test.\n" * 4_000
    )
    code = run_review(good_repo, backend="api", json_out=True)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["coverage"] == "lint+semantic"
    assert data["notes"] and "truncated" in data["notes"][0]
    assert "spec.md" in data["notes"][0]
    assert "truncated" in data["coverage_note"]  # partial coverage in the caveat too
    assert "notice:" in captured.err


def test_single_feature_dir_is_reviewable(good_repo: Path):
    # The truncation notice tells users to run `sddgrade review specs/<feature>`;
    # discovery must actually support a feature dir as the review root.
    feature = good_repo / "specs" / "001-task-export"
    arts = discover_artifacts(feature, "auto")
    names = {Path(a.path).name for a in arts}
    assert "spec.md" in names and "plan.md" in names
    assert all(a.feature_id == "001-task-export" for a in arts)


def test_agent_backend_still_degrades_quietly(good_repo: Path):
    # The forgiving default is unchanged: agent backend without judge.json degrades
    # to rules with a yellow notice (no --require-judge, no --api → no hard failure).
    buf = io.StringIO()
    code = run_review(good_repo, backend="agent", fail_under=70, console=Console(file=buf))
    assert code == 0
    assert "Judge unavailable" in buf.getvalue()

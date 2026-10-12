"""Mocked tests for the optional --jev (TypeSafe Jev) judge backend. No live key needed."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from sddgrade.adapters.base import parse_sections
from sddgrade.engine.judge import JudgeUnavailable
from sddgrade.integrations import jev as jev_mod
from sddgrade.integrations.jev import (
    DEFAULT_MODEL,
    JevJudge,
    extract_requirements,
)
from sddgrade.model import Artifact, ArtifactType, Dimension, Severity, Source
from sddgrade.runner import EXIT_JUDGE_REQUIRED, run_review

SPEC = """# Feature Specification: Search

## Requirements

- FR-001: The system shall return results quickly and rank them appropriately.
- FR-002: The system shall return at most 20 results per page.
- Users must be able to clear the query.

```
- FR-999: inside a fence, never a requirement
```
"""


def _art(text: str = SPEC, kind: ArtifactType = ArtifactType.SPEC, path: str = "spec.md"):
    return Artifact(path=path, type=kind, feature_id="x", raw=text,
                    sections=parse_sections(text))


def _fake_post(answers_for):
    """A _post stand-in: ``answers_for(payload)`` → {qid: noul}. Records payloads."""
    calls: list[dict] = []

    def _post(self, payload):
        calls.append(payload)
        probs = answers_for(payload)
        return {
            "model": "jev-1.13.0",
            "answers": {q: {"type": "noul", "noul": probs.get(q, 0.05)}
                        for q in payload["questions"]},
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }

    return _post, calls


def test_extract_requirements_ids_bullets_and_fences():
    reqs = extract_requirements([_art()])
    assert [r.rid for r in reqs] == ["FR-001", "FR-002", "line 7"]
    assert reqs[0].line == 5
    assert reqs[2].text == "Users must be able to clear the query."


def test_extract_requirements_skips_non_spec():
    assert extract_requirements([_art(kind=ArtifactType.PLAN, path="plan.md")]) == []


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(JudgeUnavailable, match="TYPESAFE_API_KEY"):
        JevJudge().judge([_art()], Path("."))


def test_model_default_and_override(monkeypatch):
    monkeypatch.delenv("SDDGRADE_JEV_MODEL", raising=False)
    assert JevJudge().model == DEFAULT_MODEL
    monkeypatch.setenv("SDDGRADE_JEV_MODEL", "jev-1.13.0")
    assert JevJudge().model == "jev-1.13.0"


def test_confident_yes_becomes_line_anchored_finding(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")

    def answers(payload):
        req = payload["state"].get("requirement", "")
        if "quickly" in req:
            return {"ambiguous": 0.97, "compound": 0.85, "unverifiable": 0.6}
        return {}

    post, calls = _fake_post(answers)
    monkeypatch.setattr(JevJudge, "_post", post)
    findings = JevJudge().judge([_art()], Path("."))

    # 3 requirement requests + 1 injection request, all with the configured model.
    assert len(calls) == 4
    assert all(c["model"] == DEFAULT_MODEL for c in calls)
    assert all(q["type"] == "noul" for c in calls for q in c["questions"].values())

    by_key = {(f.dimension, f.severity) for f in findings}
    assert by_key == {(Dimension.CLARITY, Severity.MEDIUM), (Dimension.CLARITY, Severity.LOW)}
    assert all(f.source is Source.JUDGE for f in findings)
    assert all(f.line == 5 and f.pitfall_id == "JUDGE-29148-PERREQ" for f in findings)
    # 0.6 is below the threshold: Jev split ≠ defect.
    assert not any("verifiable" in f.message for f in findings)


def test_injection_and_overengineering(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")

    def answers(payload):
        if "injection" in payload["questions"]:
            return {"injection": 0.99}
        if "over" in payload["questions"]:
            return {"over": 0.92}
        return {}

    post, _ = _fake_post(answers)
    monkeypatch.setattr(JevJudge, "_post", post)
    plan = _art("# Plan\n\nAdd a service mesh.\n", ArtifactType.PLAN, "plan.md")
    findings = JevJudge().judge([_art(), plan], Path("."))
    ids = sorted((f.pitfall_id, f.artifact_path) for f in findings)
    assert ids == [
        ("PLAN-OVER-ENGINEERING", "plan.md"),
        ("SPEC-PROMPT-INJECTION-SUSPECT", "plan.md"),
        ("SPEC-PROMPT-INJECTION-SUSPECT", "spec.md"),
    ]


def test_missing_answer_raises(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setattr(JevJudge, "_post", lambda self, p: {"answers": {}})
    with pytest.raises(JudgeUnavailable, match="missing a noul answer"):
        JevJudge().judge([_art()], Path("."))


def test_requirement_cap_adds_note(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setattr(jev_mod, "MAX_REQUIREMENTS", 1)
    post, calls = _fake_post(lambda p: {})
    monkeypatch.setattr(JevJudge, "_post", post)
    judge = JevJudge()
    judge.judge([_art()], Path("."))
    assert len(calls) == 2  # 1 requirement + 1 injection
    assert judge.notes and "first 1 of 3" in judge.notes[0]


def test_http_error_surfaces_status(monkeypatch):
    import urllib.error

    monkeypatch.setenv("TYPESAFE_API_KEY", "bad")

    def boom(req, timeout):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"bad key"}')
        )

    monkeypatch.setattr(jev_mod.urllib.request, "urlopen", boom)
    with pytest.raises(JudgeUnavailable, match="HTTP 401"):
        JevJudge().judge([_art()], Path("."))


def test_jev_backend_missing_key_fails_run(monkeypatch, good_repo: Path):
    # --jev without a key must NOT pass on a lint-only score: exit 3, clear message.
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    buf = io.StringIO()
    code = run_review(good_repo, backend="jev", fail_under=70, console=Console(file=buf))
    assert code == EXIT_JUDGE_REQUIRED
    out = buf.getvalue()
    assert "--jev" in out and "TYPESAFE_API_KEY" in out and "lint-only" in out


def test_jev_backend_end_to_end_json(monkeypatch, good_repo: Path, capsys):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    post, _ = _fake_post(lambda p: {})
    monkeypatch.setattr(JevJudge, "_post", post)
    code = run_review(good_repo, backend="jev", json_out=True)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["engine"] == "jev"
    assert data["coverage"] == "lint+semantic"
    assert data["judge_model"] == DEFAULT_MODEL

"""Semantic judge — the LLM half of the hybrid engine.

The judge does NOT bake in a provider. It defers to a JudgeBackend that mirrors
Spec-Kit's `--integration` model:

* **agent** (default): the user's own agent (Claude Code, Copilot, …) runs a scaffolded
  slash command on their existing subscription and writes structured JSON; this module
  reads it. No API key.
* **api**: optional key-based call for headless CI.

Either way the judge yields additional :class:`Finding` objects (semantic pitfalls the
deterministic lint can't catch), which the scorer folds in alongside lint findings.
"""

from __future__ import annotations

from pathlib import Path

from ..catalog import load_catalog
from ..model import Artifact, Dimension, Finding, Severity, Source

# JSON schema the agent / API judge must return.
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "artifact": {"type": "string"},
                    "dimension": {
                        "type": "string",
                        "enum": [d.value for d in Dimension],
                    },
                    "severity": {
                        "type": "string",
                        "enum": [s.value for s in Severity],
                    },
                    "message": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "pitfall_id": {"type": ["string", "null"]},
                },
                "required": ["artifact", "dimension", "severity", "message", "suggestion"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


class JudgeUnavailable(Exception):
    """Raised when the chosen backend can't run (degrade to rules-only)."""


def judge_guidance() -> str:
    """Catalog text handed to the judge: the semantic pitfalls it owns."""
    cat = load_catalog()
    lines = ["Evaluate each artifact for these semantic pitfalls (and any others you see):"]
    for p in cat.values():
        if not p.judge_detectable:
            continue
        lines.append(
            f"- {p.id} ({p.dimension.value}, {p.severity.value}): {p.name} — "
            f"{p.why} Detect: {p.detect} Fix: {p.fix}"
        )
    return "\n".join(lines)


def build_prompt(artifacts: list[Artifact]) -> str:
    """The instruction an agent runs to judge the artifact set."""
    parts = [
        "You are an expert reviewer of Spec-Driven Development artifacts.",
        "Score the artifacts below by reporting findings — concrete quality defects, "
        "each with a one-line fix suggestion. Focus on judgment the lint layer can't do: "
        "true ambiguity, hidden contradictions across artifacts, over-engineering, "
        "INVEST quality, and missing rationale.",
        "",
        judge_guidance(),
        "",
        "Return ONLY JSON matching this shape: "
        '{"findings": [{"artifact": "<filename>", "dimension": "...", '
        '"severity": "low|medium|high|critical", "message": "...", '
        '"suggestion": "...", "pitfall_id": "ID or null"}]}',
        "",
        "Artifacts:",
    ]
    for a in artifacts:
        parts.append(f"\n----- {Path(a.path).name} ({a.type.value}) -----\n{a.raw}")
    return "\n".join(parts)


def to_findings(raw: list[dict], artifacts: list[Artifact]) -> list[Finding]:
    """Validate and map judge output dicts onto Finding objects."""
    by_name = {Path(a.path).name: a.path for a in artifacts}
    out: list[Finding] = []
    for item in raw:
        try:
            dim = Dimension(item["dimension"])
            sev = Severity(item["severity"])
        except (KeyError, ValueError):
            continue
        artifact_name = Path(str(item.get("artifact", ""))).name
        path = by_name.get(artifact_name) or item.get("artifact")
        out.append(
            Finding(
                dimension=dim,
                severity=sev,
                message=str(item.get("message", "")).strip(),
                suggestion=str(item.get("suggestion", "")).strip(),
                source=Source.JUDGE,
                pitfall_id=item.get("pitfall_id") or None,
                artifact_path=path,
            )
        )
    return out


def judge(artifacts, backend, root: Path, cfg, console=None) -> list[Finding]:
    """Dispatch to the configured backend and return semantic findings."""
    if backend == "agent":
        from ..integrations.agent import AgentJudge

        raw = AgentJudge().read_judgment(root)
    elif backend == "api":
        from ..integrations.api import ApiJudge

        raw = ApiJudge(cfg).judge(artifacts, root)
    else:
        return []
    return to_findings(raw, artifacts)

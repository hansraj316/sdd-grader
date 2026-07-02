"""Agent integration — the default judge backend, using the user's own AI agent.

Mirrors Spec-Kit's `--integration`: `sddgrade init --integration <agent>` installs a
slash command into the agent's command directory. The user runs it; their agent (on
their existing subscription, no API key) judges the artifacts and writes
`.sddgrade/judge.json`, which `sddgrade review` reads back.
"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

from ..engine.judge import JudgeUnavailable, artifact_label, judge_guidance

# Agent → relative path where its slash/prompt command file lives.
# Best-effort conventions; the file is plain Markdown every agent can read.
_AGENT_PATHS: dict[str, str] = {
    "claude": ".claude/commands/sddgrade.md",
    "copilot": ".github/prompts/sddgrade.prompt.md",
    "cursor": ".cursor/commands/sddgrade.md",
    "gemini": ".gemini/commands/sddgrade.md",
    "windsurf": ".windsurf/workflows/sddgrade.md",
    "codex": ".codex/prompts/sddgrade.md",
    "generic": ".sddgrade/commands/sddgrade.md",
}

JUDGMENT_FILE = ".sddgrade/judge.json"


def supported_agents() -> list[str]:
    return sorted(_AGENT_PATHS)


def _command_text() -> str:
    template = (
        resources.files("sddgrade.integrations.commands") / "judge-command.md"
    ).read_text(encoding="utf-8")
    return template.replace("{{GUIDANCE}}", judge_guidance())


def _default_config(integration: str) -> str:
    return (
        "# sddgrade configuration\n"
        "[sddgrade]\n"
        'tool = "speckit"\n'
        f'integration = "{integration}"\n'
        "fail_under = 70\n"
    )


def scaffold(root: Path, integration: str) -> list[Path]:
    """Write the agent command file and a starter `.sddgrade.toml`. Returns paths."""
    root = Path(root).resolve()
    rel = _AGENT_PATHS.get(integration, _AGENT_PATHS["generic"])

    written: list[Path] = []

    command_path = root / rel
    command_path.parent.mkdir(parents=True, exist_ok=True)
    command_path.write_text(_command_text(), encoding="utf-8")
    written.append(command_path)

    config_path = root / ".sddgrade.toml"
    if not config_path.exists():
        config_path.write_text(_default_config(integration), encoding="utf-8")
        written.append(config_path)

    return written


def artifact_manifest(artifacts, root: Path) -> dict[str, str]:
    """Relative artifact path → sha256 of its current on-disk content.

    This is the freshness manifest the judge command writes into judge.json;
    ``read_judgment`` compares it against the artifacts being reviewed so a stale
    judgment never silently grades edited specs.
    """
    out: dict[str, str] = {}
    for a in artifacts:
        try:
            digest = hashlib.sha256(Path(a.path).read_bytes()).hexdigest()
        except OSError:
            digest = ""
        out[artifact_label(a.path, root)] = digest
    return out


class AgentJudge:
    """Reads the judgment JSON the user's agent produced."""

    def read_judgment(self, root: Path, artifacts: list | None = None) -> list[dict]:
        path = Path(root) / JUDGMENT_FILE
        if not path.is_file():
            raise JudgeUnavailable(
                "no .sddgrade/judge.json found — run the sddgrade judge command in "
                "your agent first (or use --rules / --api)"
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise JudgeUnavailable(f"judge.json is not valid JSON: {exc}") from exc
        findings = data.get("findings", data if isinstance(data, list) else [])
        if not isinstance(findings, list):
            raise JudgeUnavailable("judge.json has no 'findings' array")
        if artifacts is not None:
            self._check_freshness(data, artifacts, Path(root))
        return findings

    @staticmethod
    def _check_freshness(data, artifacts, root: Path) -> None:
        """Reject a judgment whose hash manifest doesn't match the current artifacts."""
        manifest = data.get("artifacts") if isinstance(data, dict) else None
        if not isinstance(manifest, dict) or not manifest:
            raise JudgeUnavailable(
                "judge.json is stale — it has no artifact hash manifest "
                "(old format); re-run the sddgrade judge command"
            )
        recorded = {str(k).removeprefix("./"): str(v) for k, v in manifest.items()}
        for rel, digest in artifact_manifest(artifacts, root).items():
            if recorded.get(rel) != digest:
                why = "changed since it was judged" if rel in recorded else "was not judged"
                raise JudgeUnavailable(
                    f"judge.json is stale — {rel} {why}; re-run the sddgrade judge command"
                )

"""Agent integration — the default judge backend, using the user's own AI agent.

Mirrors Spec-Kit's `--integration`: `sddreview init --integration <agent>` installs a
slash command into the agent's command directory. The user runs it; their agent (on
their existing subscription, no API key) judges the artifacts and writes
`.sddreview/judge.json`, which `sddreview review` reads back.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from ..engine.judge import JudgeUnavailable, judge_guidance

# Agent → relative path where its slash/prompt command file lives.
# Best-effort conventions; the file is plain Markdown every agent can read.
_AGENT_PATHS: dict[str, str] = {
    "claude": ".claude/commands/sddreview.md",
    "copilot": ".github/prompts/sddreview.prompt.md",
    "cursor": ".cursor/commands/sddreview.md",
    "gemini": ".gemini/commands/sddreview.md",
    "windsurf": ".windsurf/workflows/sddreview.md",
    "codex": ".codex/prompts/sddreview.md",
    "generic": ".sddreview/commands/sddreview.md",
}

JUDGMENT_FILE = ".sddreview/judge.json"


def supported_agents() -> list[str]:
    return sorted(_AGENT_PATHS)


def _command_text() -> str:
    template = (
        resources.files("sddreview.integrations.commands") / "judge-command.md"
    ).read_text(encoding="utf-8")
    return template.replace("{{GUIDANCE}}", judge_guidance())


def _default_config(integration: str) -> str:
    return (
        "# sddreview configuration\n"
        "[sddreview]\n"
        'tool = "speckit"\n'
        f'integration = "{integration}"\n'
        "fail_under = 70\n"
    )


def scaffold(root: Path, integration: str) -> list[Path]:
    """Write the agent command file and a starter `.sddreview.toml`. Returns paths."""
    root = Path(root).resolve()
    rel = _AGENT_PATHS.get(integration, _AGENT_PATHS["generic"])

    written: list[Path] = []

    command_path = root / rel
    command_path.parent.mkdir(parents=True, exist_ok=True)
    command_path.write_text(_command_text(), encoding="utf-8")
    written.append(command_path)

    config_path = root / ".sddreview.toml"
    if not config_path.exists():
        config_path.write_text(_default_config(integration), encoding="utf-8")
        written.append(config_path)

    return written


class AgentJudge:
    """Reads the judgment JSON the user's agent produced."""

    def read_judgment(self, root: Path) -> list[dict]:
        path = Path(root) / JUDGMENT_FILE
        if not path.is_file():
            raise JudgeUnavailable(
                "no .sddreview/judge.json found — run the sddreview judge command in "
                "your agent first (or use --rules / --api)"
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise JudgeUnavailable(f"judge.json is not valid JSON: {exc}") from exc
        if isinstance(data, list):
            findings = data
        elif isinstance(data, dict):
            findings = data.get("findings", [])
            if not isinstance(findings, list):
                raise JudgeUnavailable("judge.json 'findings' value is not an array")
        else:
            raise JudgeUnavailable(
                "judge.json must be a JSON object or array at the top level"
            )
        return findings

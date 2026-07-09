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
    """The scaffolded command: a thin shim that defers to `sddgrade judge-prompt`.

    Guidance is deliberately NOT baked in at init time (#50) — the shim tells the
    agent to run `sddgrade judge-prompt`, which prints the current instructions for
    the currently detected toolchain, so catalog updates reach every scaffolded
    command without re-running init.
    """
    return (
        resources.files("sddgrade.integrations.commands") / "judge-command.md"
    ).read_text(encoding="utf-8")


# Toolchain → the artifact-discovery step of the judge instructions (#50: an
# OpenSpec repo must not be told to review Spec-Kit paths).
_DISCOVERY_STEPS: dict[str, str] = {
    "speckit": (
        "Find the artifacts: every file under `specs/<feature>/` (`spec.md`, `plan.md`,\n"
        "   `tasks.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/*`) and the\n"
        "   constitution at `.specify/memory/constitution.md`."
    ),
    "openspec": (
        "Find the artifacts: `openspec/project.md`, every source-of-truth spec\n"
        "   `openspec/specs/<capability>/spec.md`, and for each change under\n"
        "   `openspec/changes/<change-id>/` (skip `changes/archive/`): `proposal.md`,\n"
        "   `tasks.md`, `design.md`, and the delta specs `specs/<capability>/spec.md`."
    ),
}


def judge_instructions(root: Path, tool: str = "auto") -> str:
    """The full, current judge instructions for the repo's (detected) toolchain.

    Printed by `sddgrade judge-prompt` and consumed by the scaffolded shim command,
    so both the pitfall catalog and the artifact paths are always live — never
    frozen at init time (#50).
    """
    from ..discovery import resolve_adapter

    adapter = resolve_adapter(Path(root).resolve(), tool)
    name = getattr(adapter, "name", "speckit")
    template = (
        resources.files("sddgrade.integrations.commands") / "judge-instructions.md"
    ).read_text(encoding="utf-8")
    return template.replace(
        "{{DISCOVERY}}", _DISCOVERY_STEPS.get(name, _DISCOVERY_STEPS["speckit"])
    ).replace("{{GUIDANCE}}", judge_guidance())


def _default_config() -> str:
    # Every key written here must be honored by `sddgrade review` (#46): a scaffolded
    # key that does nothing is a lie. Currently honored: tool, fail_under, weights.
    return (
        "# sddgrade configuration — every key here is honored by `sddgrade review`.\n"
        "[sddgrade]\n"
        '# Toolchain adapter: "auto" detects the layout; set "speckit" or "openspec"\n'
        "# to force one. An explicit `--tool` flag overrides this.\n"
        'tool = "auto"\n'
        "# CI gate: exit non-zero when the overall score is below this threshold.\n"
        "# Delete the line (or omit --fail-under) to disable gating.\n"
        "fail_under = 70\n"
        "\n"
        "# Optional per-dimension penalty multipliers (default 1.0). Example:\n"
        "# [sddgrade.weights]\n"
        '# clarity = 1.5\n'
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
        config_path.write_text(_default_config(), encoding="utf-8")
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

    def __init__(self) -> None:
        # The model the agent recorded in judge.json ("model" key), for report
        # provenance. None until read_judgment sees one.
        self.model: str | None = None

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
        if isinstance(data, dict):
            findings = data.get("findings", [])
            if not isinstance(findings, list):
                raise JudgeUnavailable("judge.json 'findings' value is not an array")
            raw_model = data.get("model")
            self.model = str(raw_model).strip() or None if raw_model else None
        elif isinstance(data, list):
            # Legacy bare-array format: carries no hash manifest, so with artifacts
            # to verify it fails the freshness check below rather than crashing.
            findings = data
        else:
            raise JudgeUnavailable(
                "judge.json must be a JSON object at the top level"
            )
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

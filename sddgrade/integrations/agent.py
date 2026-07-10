"""Agent integration — the default judge backend, using the user's own AI agent.

Mirrors Spec-Kit's `--integration`: `sddgrade init --integration <agent>` installs a
Spec-Kit-style *family* of slash commands (`/sddgrade.judge`, `/sddgrade.review`,
`/sddgrade.fix`, `/sddgrade.advise`) into the agent's command directory, following
each agent's own convention (Markdown for most, TOML for Gemini, plus a skill for
Claude Code). The user runs them; their agent (on their existing subscription, no
API key) judges the artifacts and writes `.sddgrade/judge.json`, which
`sddgrade review` reads back.
"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

from ..engine.judge import JudgeUnavailable, artifact_label, judge_guidance

# The command family: name → template file. `/sddgrade.<name>` in every agent.
COMMANDS: dict[str, str] = {
    "judge": "judge-command.md",
    "review": "review-command.md",
    "fix": "fix-command.md",
    "advise": "advise-command.md",
}

# Agent → (command directory, filename pattern, format). Mirrors Spec-Kit's
# per-agent conventions: Markdown with YAML frontmatter for most agents
# (`speckit.<name>.md` → `sddgrade.<name>.md`), Copilot's `.prompt.md` files
# under `.github/prompts/`, and Gemini's TOML (`description` + `prompt` keys,
# `{{args}}` argument placeholder instead of `$ARGUMENTS`).
_AGENT_SPECS: dict[str, tuple[str, str, str]] = {
    "claude": (".claude/commands", "sddgrade.{name}.md", "markdown"),
    "copilot": (".github/prompts", "sddgrade.{name}.prompt.md", "markdown"),
    "cursor": (".cursor/commands", "sddgrade.{name}.md", "markdown"),
    "gemini": (".gemini/commands", "sddgrade.{name}.toml", "toml"),
    "windsurf": (".windsurf/workflows", "sddgrade.{name}.md", "markdown"),
    "codex": (".codex/prompts", "sddgrade.{name}.md", "markdown"),
    "generic": (".sddgrade/commands", "sddgrade.{name}.md", "markdown"),
}

# Claude Code additionally gets a skill that teaches the whole judge → review →
# fix workflow and triggers on grade/review/score-my-specs requests.
CLAUDE_SKILL_PATH = ".claude/skills/sddgrade/SKILL.md"

JUDGMENT_FILE = ".sddgrade/judge.json"


def supported_agents() -> list[str]:
    return sorted(_AGENT_SPECS)


def _template_text(filename: str) -> str:
    return (
        resources.files("sddgrade.integrations.commands") / filename
    ).read_text(encoding="utf-8")


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split ``content`` into (frontmatter text, body); ("", content) if none."""
    if content.startswith("---\n"):
        end = content.find("\n---", 4)
        if end != -1:
            return content[4:end].strip(), content[end + 4 :].lstrip("\n")
    return "", content


def _frontmatter_description(content: str) -> str:
    fm, _ = _split_frontmatter(content)
    for line in fm.splitlines():
        if line.startswith("description:"):
            return line.removeprefix("description:").strip()
    return ""


def _render_toml(content: str) -> str:
    """Render a Markdown command template as a Gemini TOML command file.

    Gemini custom commands are TOML with a ``description`` string and a
    ``prompt`` multiline string, and use ``{{args}}`` instead of ``$ARGUMENTS``
    (same conversion Spec-Kit's TomlIntegration performs).
    """
    description = _frontmatter_description(content)
    _, body = _split_frontmatter(content)
    body = body.replace("$ARGUMENTS", "{{args}}").rstrip("\n")
    escaped = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    lines = []
    if description:
        d = description.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'description = "{d}"')
        lines.append("")
    lines.append(f'prompt = """\n{escaped}\n"""')
    return "\n".join(lines) + "\n"


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
    """Write the agent's command family and a starter `.sddgrade.toml`.

    Idempotent: command files are re-rendered from the installed templates on
    every run (so re-running init after an upgrade refreshes them), the config
    is only written when absent. Returns every path written, in order.
    """
    root = Path(root).resolve()
    cmd_dir, pattern, fmt = _AGENT_SPECS.get(integration, _AGENT_SPECS["generic"])

    written: list[Path] = []

    for name, template in COMMANDS.items():
        content = _template_text(template)
        if fmt == "toml":
            content = _render_toml(content)
        command_path = root / cmd_dir / pattern.format(name=name)
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text(content, encoding="utf-8")
        written.append(command_path)

    if integration == "claude":
        skill_path = root / CLAUDE_SKILL_PATH
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(_template_text("skill.md"), encoding="utf-8")
        written.append(skill_path)

    config_path = root / ".sddgrade.toml"
    if not config_path.exists():
        config_path.write_text(_default_config(), encoding="utf-8")
        written.append(config_path)

    return written


def scaffold_summary(written: list[Path], integration: str) -> str:
    """The next-steps message `init` (and the guided wizard) prints after scaffolding."""
    lines = [f"Initialized sddgrade ({integration}). Wrote:"]
    lines += [f"  {p}" for p in written]
    lines += [
        "",
        "Slash commands installed: /sddgrade.judge  /sddgrade.review  "
        "/sddgrade.fix  /sddgrade.advise",
        "Next: open your agent and run /sddgrade.review "
        "(or run `sddgrade review --rules` for the offline lint).",
    ]
    return "\n".join(lines)


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

"""Scaffolding of the Spec-Kit-style /sddgrade.* command family per agent.

`sddgrade init --integration <agent>` must install /sddgrade.judge, .review, .fix
and .advise following each agent's own convention (Markdown frontmatter files for
most, TOML for Gemini, plus a SKILL.md for Claude Code), idempotently, with no
leftover template placeholders.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from sddgrade.integrations.agent import (
    CLAUDE_SKILL_PATH,
    COMMANDS,
    judge_instructions,
    scaffold,
    scaffold_summary,
    supported_agents,
)

# Uppercase mustache tokens are render-time placeholders ({{DISCOVERY}}, …);
# {{args}} is Gemini's *runtime* argument placeholder and is expected output.
_PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")

# Expected on-disk layout per agent, mirroring Spec-Kit's conventions.
_EXPECTED = {
    "claude": [".claude/commands/sddgrade.{name}.md"],
    "copilot": [".github/prompts/sddgrade.{name}.prompt.md"],
    "cursor": [".cursor/commands/sddgrade.{name}.md"],
    "gemini": [".gemini/commands/sddgrade.{name}.toml"],
    "windsurf": [".windsurf/workflows/sddgrade.{name}.md"],
    "codex": [".codex/prompts/sddgrade.{name}.md"],
    "generic": [".sddgrade/commands/sddgrade.{name}.md"],
}


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n"), "command file must start with YAML frontmatter"
    return text[4 : text.index("\n---", 4)]


def test_expected_layout_covers_every_supported_agent():
    assert set(_EXPECTED) == set(supported_agents())


@pytest.mark.parametrize("agent", sorted(_EXPECTED))
def test_scaffold_writes_full_command_family(tmp_path: Path, agent: str):
    written = scaffold(tmp_path, agent)
    for pattern in _EXPECTED[agent]:
        for name in COMMANDS:
            path = tmp_path / pattern.format(name=name)
            assert path.is_file(), f"{agent}: missing {path}"
            assert path in written
    # And every written text file renders with no leftover template placeholder.
    for p in written:
        assert not _PLACEHOLDER.search(p.read_text(encoding="utf-8")), f"placeholder left in {p}"


@pytest.mark.parametrize("agent", sorted(set(_EXPECTED) - {"gemini"}))
def test_markdown_commands_have_description_frontmatter(tmp_path: Path, agent: str):
    scaffold(tmp_path, agent)
    for pattern in _EXPECTED[agent]:
        for name in COMMANDS:
            text = (tmp_path / pattern.format(name=name)).read_text(encoding="utf-8")
            assert "description:" in _frontmatter(text), f"{agent}/{name}"


def test_gemini_commands_are_valid_toml_with_description_and_prompt(tmp_path: Path):
    scaffold(tmp_path, "gemini")
    for name in COMMANDS:
        path = tmp_path / f".gemini/commands/sddgrade.{name}.toml"
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert set(data) == {"description", "prompt"}
        assert "sddgrade" in data["prompt"]
        # Gemini uses {{args}}, never Markdown-agent $ARGUMENTS.
        assert "$ARGUMENTS" not in data["prompt"]


def test_claude_scaffold_includes_wellformed_skill(tmp_path: Path):
    written = scaffold(tmp_path, "claude")
    skill = tmp_path / CLAUDE_SKILL_PATH
    assert skill.is_file() and skill in written
    text = skill.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: sddgrade" in fm
    assert "description:" in fm
    # Trigger conditions and the workflow the skill teaches.
    for needle in ("grade", "review", "spec.md", "plan.md", "OpenSpec", "Spec-Kit"):
        assert needle in fm, f"skill description must mention {needle!r}"
    for cmd in ("/sddgrade.judge", "/sddgrade.review", "/sddgrade.fix", "/sddgrade.advise"):
        assert cmd in text
    assert len(text.splitlines()) < 100, "skill must stay concise (<100 lines)"


def test_non_claude_agents_do_not_get_the_claude_skill(tmp_path: Path):
    scaffold(tmp_path, "copilot")
    assert not (tmp_path / ".claude").exists()


def test_judge_command_still_instructs_manifest_and_model(tmp_path: Path):
    scaffold(tmp_path, "claude")
    shim = (tmp_path / ".claude/commands/sddgrade.judge.md").read_text(encoding="utf-8")
    # The shim defers to the live prompt but must still name the contract:
    assert "sddgrade judge-prompt" in shim
    assert ".sddgrade/judge.json" in shim
    assert "hash manifest" in shim
    assert "`model`" in shim
    # And the live instructions carry the full contract the shim points at.
    live = judge_instructions(tmp_path)
    assert "sha256" in live
    assert '"model"' in live
    assert '"artifacts"' in live


def test_scaffold_is_idempotent(tmp_path: Path):
    first = scaffold(tmp_path, "claude")
    second = scaffold(tmp_path, "claude")
    # Config is only written once; command files are refreshed in place.
    assert set(second) == set(first) - {tmp_path / ".sddgrade.toml"}
    assert len(second) == len(set(second))
    assert (tmp_path / ".sddgrade.toml").is_file()


def test_scaffold_summary_lists_paths_and_next_steps(tmp_path: Path):
    written = scaffold(tmp_path, "cursor")
    summary = scaffold_summary(written, "cursor")
    assert summary.startswith("Initialized sddgrade (cursor). Wrote:")
    for p in written:
        assert str(p) in summary
    assert "/sddgrade.review" in summary

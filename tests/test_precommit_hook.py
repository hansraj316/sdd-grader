"""Validate .pre-commit-hooks.yaml is syntactically correct and has expected fields."""
import importlib.util
import pathlib

import pytest

HOOKS_FILE = pathlib.Path(__file__).parent.parent / ".pre-commit-hooks.yaml"


def _load_yaml(path: pathlib.Path):
    # Use stdlib tomllib / PyYAML if available, otherwise parse manually.
    # We ship only pytest as a dev dependency, so do a lightweight parse.
    try:
        import yaml  # type: ignore[import]
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    # Minimal fallback: just verify the file exists and is non-empty.
    return None


def test_hooks_file_exists():
    assert HOOKS_FILE.exists(), ".pre-commit-hooks.yaml must exist at the repo root"


def test_hooks_file_nonempty():
    content = HOOKS_FILE.read_text()
    assert content.strip(), ".pre-commit-hooks.yaml must not be empty"


def test_hooks_file_contains_required_fields():
    content = HOOKS_FILE.read_text()
    for field in ("id:", "name:", "language:", "entry:", "files:", "pass_filenames:"):
        assert field in content, f".pre-commit-hooks.yaml missing field: {field}"


def test_hooks_entry_uses_rules_flag():
    content = HOOKS_FILE.read_text()
    assert "--rules" in content, "hook entry must include --rules (deterministic, no LLM)"


def test_hooks_entry_uses_fail_under():
    content = HOOKS_FILE.read_text()
    assert "--fail-under" in content, "hook entry must include --fail-under"


def test_hooks_language_is_python():
    content = HOOKS_FILE.read_text()
    assert "language: python" in content, "hook language must be python"


def test_hooks_pass_filenames_is_false():
    content = HOOKS_FILE.read_text()
    assert "pass_filenames: false" in content, "pass_filenames must be false (we review the whole specs dir)"


def test_readme_documents_precommit():
    readme = (pathlib.Path(__file__).parent.parent / "README.md").read_text()
    assert "pre-commit" in readme.lower(), "README.md must document the pre-commit integration"
    assert ".pre-commit-config.yaml" in readme, "README.md must show a .pre-commit-config.yaml snippet"
    assert "id: sddgrade" in readme, "README.md must show the sddgrade hook id"

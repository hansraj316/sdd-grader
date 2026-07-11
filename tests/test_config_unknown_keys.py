"""Tests for unknown-key warnings in config.load() (#80)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sddgrade import config as config_mod


def _write_config(tmp_path: Path, text: str) -> Path:
    cfg = tmp_path / ".sddgrade.toml"
    cfg.write_text(text, encoding="utf-8")
    return tmp_path


def test_clean_config_no_warnings(tmp_path, capsys):
    """Valid config keys emit no warnings."""
    _write_config(tmp_path, '[sddgrade]\ntool = "speckit"\nfail_under = 70\n')
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert captured.err == ""


def test_typo_key_emits_warning(tmp_path, capsys):
    """A misspelled top-level key produces a warning on stderr."""
    _write_config(tmp_path, '[sddgrade]\nthreashold = 80\n')
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert "unknown config key 'threashold'" in captured.err
    assert ".sddgrade.toml" in captured.err


def test_unknown_nested_weight_key_emits_warning(tmp_path, capsys):
    """An unknown dimension name inside [sddgrade.weights] produces a warning."""
    _write_config(tmp_path, '[sddgrade.weights]\ncompleteness = 2.0\ntypo_dim = 1.5\n')
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert "unknown config key 'weights.typo_dim'" in captured.err


def test_multiple_unknown_keys_each_warned(tmp_path, capsys):
    """Each unknown key gets its own warning line."""
    _write_config(tmp_path, '[sddgrade]\nfoo = 1\nbar = 2\n')
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert "unknown config key 'foo'" in captured.err
    assert "unknown config key 'bar'" in captured.err


def test_no_config_file_no_warnings(tmp_path, capsys):
    """When no .sddgrade.toml exists, nothing is written to stderr."""
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert captured.err == ""


def test_valid_weights_no_warnings(tmp_path, capsys):
    """All valid dimension names in [weights] produce no warnings."""
    _write_config(
        tmp_path,
        '[sddgrade.weights]\ncompleteness = 1.5\nclarity = 1.2\ntestability = 1.0\n',
    )
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert captured.err == ""


def test_toplevel_unknown_key_without_sddgrade_section(tmp_path, capsys):
    """Unknown key at top level (no [sddgrade] wrapper) is also warned."""
    _write_config(tmp_path, 'tool = "auto"\nunknown_option = true\n')
    config_mod.load(tmp_path)
    captured = capsys.readouterr()
    assert "unknown config key 'unknown_option'" in captured.err

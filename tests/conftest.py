"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def good_repo(tmp_path: Path) -> Path:
    """A throwaway copy of the well-formed Spec-Kit fixture."""
    dst = tmp_path / "good"
    shutil.copytree(FIXTURES / "speckit_good", dst)
    return dst


@pytest.fixture
def bad_repo(tmp_path: Path) -> Path:
    """A throwaway copy of the defect-laden Spec-Kit fixture."""
    dst = tmp_path / "bad"
    shutil.copytree(FIXTURES / "speckit_bad", dst)
    return dst

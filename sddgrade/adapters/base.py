"""Adapter protocol + shared Markdown parsing.

An adapter knows how a particular SDD toolchain lays out its artifacts on disk and
how to normalize them into :class:`~sddgrade.model.Artifact` objects. The engine and
reports depend only on this protocol, so adding OpenSpec later is a new adapter, not a
change to the core.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..model import Artifact, ArtifactType, Finding, Section


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def parse_sections(text: str) -> list[Section]:
    """Split Markdown into sections by ATX heading, ignoring headings inside code fences.

    Each section's ``body`` is the text from just after its heading up to the next
    heading (of any level). This is intentionally simple and dependency-free — it is
    enough for required-section and content checks without a full Markdown AST.
    """
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []  # (line_index, level, title)
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))

    sections: list[Section] = []
    for idx, (line_i, level, title) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = "\n".join(lines[line_i + 1 : end]).strip()
        sections.append(Section(title=title, level=level, body=body, line=line_i + 1))
    return sections


# Template authoring machinery, not content (#69): headings the Spec-Kit templates
# carry for the generating agent's benefit. Never required of authored artifacts
# (the judge guidance treats keeping them as boilerplate to remove).
_SCAFFOLDING_TITLES: frozenset[str] = frozenset({
    "execution flow", "execution flow main",
    "quick guidelines",
    "execution status",
})


def _is_scaffolding(title: str) -> bool:
    # Normalize away emoji/punctuation ('⚡ Quick Guidelines', 'Execution Flow (main)').
    norm = " ".join(re.sub(r"[^a-z0-9 ]", " ", title.lower()).split())
    return norm in _SCAFFOLDING_TITLES


def required_sections_from_template(template_text: str, max_level: int = 2) -> list[str]:
    """Derive expected section titles from a Spec-Kit ``*-template.md`` file.

    We take headings up to ``max_level`` and strip bracketed placeholders so the
    derived requirement is the literal heading text the author is expected to keep.
    Template scaffolding sections (Execution Flow, Quick Guidelines, Execution
    Status) are excluded — they are authoring machinery, not content quality (#69).
    """
    titles: list[str] = []
    for s in parse_sections(template_text):
        if s.level > max_level:
            continue
        cleaned = re.sub(r"\[[^\]]*\]", "", s.title).strip(" :-")
        # Drop the document title (level 1) and any now-empty placeholder heading.
        if s.level == 1 or not cleaned:
            continue
        if _is_scaffolding(cleaned):
            continue
        titles.append(cleaned)
    return titles


@runtime_checkable
class ArtifactAdapter(Protocol):
    """The seam every SDD toolchain plugs into."""

    name: str
    hint: str  # short phrase for "no artifacts found" messages, e.g. "run `specify init` first"

    def detect(self, root: Path) -> bool:
        """True if this toolchain's layout is present under ``root``."""
        ...

    def discover(self, root: Path) -> list[Path]:
        """All artifact files this adapter can review under ``root``."""
        ...

    def classify(self, path: Path) -> ArtifactType:
        """Map a file path to its artifact type."""
        ...

    def parse(self, path: Path, root: Path) -> Artifact:
        """Read and normalize one artifact file."""
        ...

    def required_sections(self, artifact_type: ArtifactType, root: Path) -> list[str]:
        """Expected section titles for a type (template-derived when available)."""
        ...

    def structural_checks(self, artifact: Artifact, catalog: dict) -> list[Finding]:
        """Toolchain-specific per-artifact structural checks."""
        ...

    def cross_artifact_checks(self, artifacts: list[Artifact], catalog: dict) -> list[Finding]:
        """Toolchain-specific cross-artifact consistency checks."""
        ...

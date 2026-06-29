"""OpenSpec adapter — early support for Fission-AI OpenSpec layouts.

OpenSpec organizes work as **change proposals** plus source-of-truth **capability specs**:

    openspec/project.md                          (project conventions)
    openspec/specs/<capability>/spec.md          (source-of-truth spec)
    openspec/changes/<change-id>/proposal.md     (## Why / ## What Changes / ## Impact)
    openspec/changes/<change-id>/tasks.md        (implementation checklist)
    openspec/changes/<change-id>/design.md       (technical approach)
    openspec/changes/<change-id>/specs/<cap>/spec.md   (delta spec)

Specs use `## Requirements` → `### Requirement: <name>` (SHALL) → `#### Scenario:`
(WHEN/THEN). OpenSpec artifacts are normalized into the same Artifact model; the
universal requirement-smell checks apply, but the Spec-Kit-template-specific structural
checks do not (see engine/lint gating). This is a first-version adapter.
"""

from __future__ import annotations

from pathlib import Path

from ..model import Artifact, ArtifactType
from .base import parse_sections

# OpenSpec spec → SPEC, proposal → PLAN, tasks → TASKS, design → RESEARCH,
# project.md → CONSTITUTION (project conventions / governance).
_DEFAULT_REQUIRED: dict[ArtifactType, list[str]] = {
    ArtifactType.SPEC: ["Requirements"],
    ArtifactType.PLAN: ["Why", "What Changes", "Impact"],  # proposal.md
    ArtifactType.TASKS: [],
    ArtifactType.CONSTITUTION: [],
}


class OpenSpecAdapter:
    """ArtifactAdapter for OpenSpec."""

    name = "openspec"

    def detect(self, root: Path) -> bool:
        os_dir = root / "openspec"
        return os_dir.is_dir() and (
            (os_dir / "specs").is_dir() or (os_dir / "changes").is_dir()
        )

    def classify(self, path: Path) -> ArtifactType:
        name = path.name.lower()
        parts = [p.lower() for p in path.parts]
        if name == "proposal.md":
            return ArtifactType.PLAN
        if name == "tasks.md":
            return ArtifactType.TASKS
        if name == "design.md":
            return ArtifactType.RESEARCH
        if name == "project.md":
            return ArtifactType.CONSTITUTION
        if name == "spec.md":
            return ArtifactType.SPEC
        if "changes" in parts and name.endswith(".md"):
            return ArtifactType.UNKNOWN
        return ArtifactType.UNKNOWN

    def _feature_id(self, path: Path, root: Path) -> str | None:
        """The change-id (changes/<id>) or capability (specs/<cap>)."""
        try:
            rel = path.resolve().relative_to((root / "openspec").resolve())
        except ValueError:
            return None
        parts = rel.parts
        if len(parts) >= 2 and parts[0] in ("changes", "specs"):
            return parts[1]
        return None

    def discover(self, root: Path) -> list[Path]:
        os_dir = root / "openspec"
        found: list[Path] = []
        if not os_dir.is_dir():
            return found

        project = os_dir / "project.md"
        if project.is_file():
            found.append(project)

        specs = os_dir / "specs"
        if specs.is_dir():
            found.extend(sorted(specs.glob("*/spec.md")))

        changes = os_dir / "changes"
        if changes.is_dir():
            for change in sorted(p for p in changes.iterdir() if p.is_dir()):
                if change.name == "archive":
                    continue
                for fn in ("proposal.md", "tasks.md", "design.md"):
                    f = change / fn
                    if f.is_file():
                        found.append(f)
                # Delta specs inside the change.
                found.extend(sorted((change / "specs").glob("*/spec.md")))
        return found

    def parse(self, path: Path, root: Path) -> Artifact:
        text = path.read_text(encoding="utf-8", errors="replace")
        return Artifact(
            path=str(path),
            type=self.classify(path),
            feature_id=self._feature_id(path, root),
            raw=text,
            sections=parse_sections(text),
        )

    def required_sections(self, artifact_type: ArtifactType, root: Path) -> list[str]:
        return _DEFAULT_REQUIRED.get(artifact_type, [])

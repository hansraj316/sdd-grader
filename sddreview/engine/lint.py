"""Deterministic lint — turns Spec-Kit conventions into measurable findings.

Three layers, all free and reproducible:
1. Required-section checks (template-derived) → completeness.
2. Generic lexical pitfall checks (catalog ``patterns``) → one finding per pitfall/artifact.
3. Dedicated structural & cross-artifact checks keyed by pitfall id.

The judge handles semantic pitfalls (``method = "judge"``) the lint layer can't.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..adapters.base import ArtifactAdapter
from ..catalog import Pitfall, load_catalog
from ..model import Artifact, ArtifactType, Dimension, Finding, Section, Severity, Source

_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION", re.IGNORECASE)
_TASK_LINE_RE = re.compile(r"^\s*-?\s*\[[ xX]\]")  # a checkbox bullet
_TASK_ID_RE = re.compile(r"\bT\d{2,}\b")
_US_TAG_RE = re.compile(r"\[US\d+\]", re.IGNORECASE)
_US_HEADING_RE = re.compile(r"user stor(?:y|ies)\s*(\d+)", re.IGNORECASE)
_DIGIT_RE = re.compile(r"\d")
_FILE_PATH_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,5}\b")
_NFR_RE = re.compile(
    r"\b(latency|throughput|response time|uptime|availab|scalab|concurren|"
    r"requests per second|\brps\b|performance|load handling)\b",
    re.IGNORECASE,
)
_REQUIREMENTish_RE = re.compile(r"\b(shall|must|should|FR-\d|NFR-\d)\b", re.IGNORECASE)


def _nfr_without_threshold(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines naming an NFR quality but stating no numeric threshold."""
    p = catalog.get("SPEC-NFR-NO-THRESHOLD")
    if p is None or not p.applies_to(art.type):
        return []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        # Strip requirement IDs (FR-001, NFR-2, T012, US3) so their digits don't
        # masquerade as a measurable threshold.
        without_ids = re.sub(r"\b(?:FR|NFR|US|T)-?\d+\b", "", line, flags=re.IGNORECASE)
        if (
            _NFR_RE.search(line)
            and _REQUIREMENTish_RE.search(line)
            and not _DIGIT_RE.search(without_ids)
        ):
            return [
                _from_pitfall(
                    p, art.path,
                    "Non-functional requirement stated with no measurable threshold.",
                    line=i,
                )
            ]
    return []


_PASSIVE_VERB_RE = re.compile(
    r"\b(?:shall|must|should|will)\s+be\s+\w+ed\b"
    r"|\bto\s+be\s+\w+ed\b",
    re.IGNORECASE,
)


def _passive_voice(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines using passive voice (be + past participle, no clear actor)."""
    p = catalog.get("SPEC-PASSIVE-VOICE")
    if p is None or not p.applies_to(art.type):
        return []
    hits: list[int] = []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        if _REQUIREMENTish_RE.search(line) and _PASSIVE_VERB_RE.search(line):
            hits.append(i)
    if not hits:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"Requirement uses passive voice (no clear actor): {len(hits)} line(s).",
            line=hits[0],
        )
    ]


_NEGATIVE_REQ_RE = re.compile(
    r"\b(?:shall|must|should)\s+not\b",
    re.IGNORECASE,
)


def _negative_requirement(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines that state what the system must NOT do."""
    p = catalog.get("SPEC-NEGATIVE-REQUIREMENT")
    if p is None or not p.applies_to(art.type):
        return []
    hits: list[int] = []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        if _REQUIREMENTish_RE.search(line) and _NEGATIVE_REQ_RE.search(line):
            hits.append(i)
    if not hits:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"Negative requirement (shall/must not): {len(hits)} line(s); prefer positive bounded statements.",
            line=hits[0],
        )
    ]


def _from_pitfall(
    p: Pitfall, artifact_path: str, message: str, line: int | None = None
) -> Finding:
    return Finding(
        dimension=p.dimension,
        severity=p.severity,
        message=message,
        suggestion=p.fix,
        source=Source.LINT,
        pitfall_id=p.id,
        artifact_path=artifact_path,
        line=line,
    )


def lint(
    artifacts: list[Artifact], adapter: ArtifactAdapter, root: Path
) -> list[Finding]:
    """Run every deterministic check over a parsed artifact set."""
    catalog = load_catalog()
    findings: list[Finding] = []

    # Per-artifact checks.
    for art in artifacts:
        findings.extend(_required_sections(art, adapter, root))
        findings.extend(_lexical_pitfalls(art, catalog))
        findings.extend(_structural(art, catalog))

    # Cross-artifact checks, grouped by feature.
    findings.extend(_cross_artifact(artifacts, catalog))
    return findings


# --------------------------------------------------------------------------- layer 1

def _required_sections(
    art: Artifact, adapter: ArtifactAdapter, root: Path
) -> list[Finding]:
    required = adapter.required_sections(art.type, root)
    if not required:
        return []
    present = [s.title for s in art.sections]

    def has(title: str) -> bool:
        needle = title.lower()
        return any(needle in p.lower() for p in present)

    out: list[Finding] = []
    for title in required:
        if not has(title):
            out.append(
                Finding(
                    dimension=Dimension.COMPLETENESS,
                    severity=Severity.MEDIUM,
                    message=f"Missing required section '{title}' in {art.type.value}.",
                    suggestion=f"Add a '## {title}' section (see the Spec-Kit "
                    f"{art.type.value} template).",
                    source=Source.LINT,
                    artifact_path=art.path,
                )
            )
    return out


# --------------------------------------------------------------------------- layer 2

def _lexical_pitfalls(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """One finding per matching lexical pitfall, summarizing the matches."""
    out: list[Finding] = []
    lines = art.raw.splitlines()
    for p in catalog.values():
        if not p.compiled or not p.lint_detectable or not p.applies_to(art.type):
            continue
        hits: list[tuple[int, str]] = []
        for i, line in enumerate(lines, start=1):
            for rx in p.compiled:
                m = rx.search(line)
                if m:
                    hits.append((i, m.group(0)))
                    break
        if hits:
            examples = ", ".join(sorted({h[1] for h in hits})[:5])
            out.append(
                _from_pitfall(
                    p,
                    art.path,
                    f"{p.name}: {len(hits)} occurrence(s) (e.g. {examples}).",
                    line=hits[0][0],
                )
            )
    return out


# --------------------------------------------------------------------------- layer 3

def _structural(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []
    check = _STRUCTURAL_CHECKS.get(art.type)
    if check:
        out.extend(check(art, catalog))
    return out


def _spec_checks(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []

    # Unresolved [NEEDS CLARIFICATION] markers.
    clar = _CLARIFICATION_RE.findall(art.raw)
    if clar and (p := catalog.get("SPEC-UNRESOLVED-CLARIFICATION")):
        out.append(
            _from_pitfall(p, art.path, f"{len(clar)} unresolved [NEEDS CLARIFICATION] marker(s).")
        )

    # Edge cases present and non-trivial.
    edge = art.section("Edge Cases")
    if (not edge or len(edge.body.strip()) < 10) and (p := catalog.get("SPEC-MISSING-EDGE-CASES")):
        out.append(_from_pitfall(p, art.path, "No meaningful Edge Cases section."))

    # Measurable success criteria. The numbers may live in a "Measurable Outcomes"
    # subsection, so check the whole Success Criteria block and any Measurable section.
    success_text = ""
    for s in art.sections:
        t = s.title.lower()
        if "success criteria" in t or "measurable" in t:
            success_text += "\n" + s.body
    if success_text.strip() and not _DIGIT_RE.search(success_text) and (
        p := catalog.get("SPEC-NON-MEASURABLE-SUCCESS")
    ):
        out.append(_from_pitfall(p, art.path, "Success Criteria contain no measurable values."))

    # Each user story has real acceptance criteria (Given/When/Then or an acceptance
    # block that isn't just a TODO).
    if p := catalog.get("SPEC-MISSING-ACCEPTANCE"):
        for s in art.sections:
            if "user story" in s.title.lower():
                body = s.body.lower()
                has_gwt = "given" in body and "when" in body
                has_block = "acceptance" in body and "todo" not in body
                if not (has_gwt or has_block):
                    out.append(
                        _from_pitfall(
                            p, art.path,
                            f"User story '{s.title}' has no acceptance criteria.",
                            line=s.line,
                        )
                    )

    # Compound functional requirements (singular violation).
    if p := catalog.get("REQ-COMPOUND"):
        for i, line in enumerate(art.raw.splitlines(), start=1):
            if re.search(r"\bFR-\d|shall\b", line) and line.lower().count(" and ") >= 2:
                out.append(
                    _from_pitfall(
                        p, art.path,
                        "Requirement bundles multiple capabilities (not singular).",
                        line=i,
                    )
                )
                break

    out.extend(_nfr_without_threshold(art, catalog))
    out.extend(_passive_voice(art, catalog))
    out.extend(_negative_requirement(art, catalog))
    return out


def _plan_checks(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []

    clar = _CLARIFICATION_RE.findall(art.raw)
    if clar and (p := catalog.get("SPEC-UNRESOLVED-CLARIFICATION")):
        out.append(_from_pitfall(p, art.path, f"{len(clar)} unresolved [NEEDS CLARIFICATION] marker(s)."))

    check_section = art.section("Constitution Check")
    if p := catalog.get("PLAN-CONSTITUTION-UNCHECKED"):
        if check_section is None:
            out.append(_from_pitfall(p, art.path, "No Constitution Check section."))
        elif "pass" not in check_section.body.lower():
            out.append(_from_pitfall(p, art.path, "Constitution Check is not marked as passing."))

    if check_section and (p := catalog.get("PLAN-UNJUSTIFIED-COMPLEXITY")):
        body = check_section.body.lower()
        # A real violation: an explicit FAIL, or "violation(s)" not negated by "no".
        has_violation = bool(re.search(r"\bfail\b", body)) or (
            re.search(r"\bviolation", body) is not None
            and re.search(r"\bno\s+violation", body) is None
        )
        ct = art.section("Complexity Tracking")
        ct_body = ct.body.lower() if ct else ""
        ct_justifies = ct is not None and len(ct.body.strip()) >= 15 and "no violation" not in ct_body
        if has_violation and not ct_justifies:
            out.append(
                _from_pitfall(p, art.path, "Constitution violation is not justified in Complexity Tracking.")
            )

    out.extend(_nfr_without_threshold(art, catalog))
    out.extend(_passive_voice(art, catalog))
    out.extend(_negative_requirement(art, catalog))
    return out


def _tasks_checks(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []
    lines = art.raw.splitlines()

    # Malformed task lines: checkbox bullets without a T### id.
    if p := catalog.get("TASKS-MALFORMED"):
        bad = [
            (i, ln) for i, ln in enumerate(lines, start=1)
            if _TASK_LINE_RE.match(ln) and not _TASK_ID_RE.search(ln)
        ]
        if bad:
            out.append(
                _from_pitfall(
                    p, art.path,
                    f"{len(bad)} task line(s) missing a T### id or malformed.",
                    line=bad[0][0],
                )
            )

    # Tests-first: an "Implementation for User Story" section with no preceding
    # "Tests for User Story" section anywhere.
    if p := catalog.get("TASKS-TESTS-NOT-FIRST"):
        titles = [s.title.lower() for s in art.sections]
        has_impl = any("implementation for user story" in t for t in titles)
        has_tests = any("tests for user story" in t for t in titles)
        if has_impl and not has_tests:
            out.append(_from_pitfall(p, art.path, "Implementation tasks with no test tasks (Test-First)."))
    return out


def _constitution_checks(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    # Placeholders handled by lexical layer (CONST-PLACEHOLDER/CONST-UNVERSIONED patterns).
    return []


_STRUCTURAL_CHECKS = {
    ArtifactType.SPEC: _spec_checks,
    ArtifactType.PLAN: _plan_checks,
    ArtifactType.TASKS: _tasks_checks,
    ArtifactType.CONSTITUTION: _constitution_checks,
}


def _get(catalog: dict[str, Pitfall], key: str) -> Pitfall | None:
    return catalog.get(key)


# --------------------------------------------------------------------------- cross-artifact

def _cross_artifact(artifacts: list[Artifact], catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []
    by_feature: dict[str | None, list[Artifact]] = {}
    for a in artifacts:
        by_feature.setdefault(a.feature_id, []).append(a)

    for feature, arts in by_feature.items():
        if feature is None:
            continue
        spec = _first(arts, ArtifactType.SPEC)
        tasks = _first(arts, ArtifactType.TASKS)
        data_model = _first(arts, ArtifactType.DATA_MODEL)
        contracts = [a for a in arts if a.type == ArtifactType.CONTRACT]

        if tasks is None:
            continue
        tasks_text = tasks.raw.lower()

        # Story → task.
        if spec and (p := catalog.get("XREF-STORY-NO-TASK")):
            story_nums = {m.group(1) for m in _US_HEADING_RE.finditer(spec.raw)}
            tagged = {m.group(0).lower() for m in _US_TAG_RE.finditer(tasks.raw)}
            for n in sorted(story_nums):
                if f"[us{n}]" not in tagged:
                    out.append(_from_pitfall(p, tasks.path, f"User Story {n} has no implementing task."))

        # Entity → task.
        if data_model and (p := catalog.get("XREF-ENTITY-NO-TASK")):
            for entity in _entities(data_model):
                if entity.lower() not in tasks_text:
                    out.append(_from_pitfall(p, tasks.path, f"Entity '{entity}' is referenced by no task."))

        # Contract → contract test.
        if contracts and (p := catalog.get("XREF-CONTRACT-NO-TEST")):
            has_contract_test = "contract test" in tasks_text or "test_contract" in tasks_text
            if not has_contract_test:
                out.append(
                    _from_pitfall(p, tasks.path, f"{len(contracts)} contract(s) with no contract-test task.")
                )
    return out


def _first(arts: list[Artifact], atype: ArtifactType) -> Artifact | None:
    for a in arts:
        if a.type == atype:
            return a
    return None


def _entities(data_model: Artifact) -> list[str]:
    """Entity names = level-3 headings under the data model."""
    names: list[str] = []
    for s in data_model.sections:
        if s.level >= 3 and s.title.strip():
            names.append(s.title.strip())
    return names

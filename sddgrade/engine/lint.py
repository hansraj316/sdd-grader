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

from ..adapters.base import ArtifactAdapter, _FENCE_RE
from ..catalog import Pitfall, load_catalog
from ..model import Artifact, ArtifactType, Dimension, Finding, Section, Severity, Source

# A genuine marker has a colon and a question: [NEEDS CLARIFICATION: auth method?].
# Bare '[NEEDS CLARIFICATION]' mentions are template prose talking ABOUT markers.
_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION:", re.IGNORECASE)
_NO_CLARIF_RE = re.compile(r"no\s+\[needs\s+clarif", re.IGNORECASE)
# The template's literal demonstration placeholder ('Use [NEEDS CLARIFICATION:
# specific question] for any assumption ...' in 'For AI Generation') — template
# prose, not an author-written marker.
_CLARIF_INSTRUCTION_RE = re.compile(
    r"\[needs clarification:\s*specific question\]", re.IGNORECASE
)


def _count_real_clarification_markers(raw: str) -> int:
    """Count genuine [NEEDS CLARIFICATION: ...] markers, excluding template boilerplate.

    Template-aware (#69): skips lines inside fenced code blocks (the canonical
    Spec-Kit 'Execution Flow (main)' body is fenced), blockquote lines (template
    instructions start with '>'), checklist lines that reference the marker as the
    item being verified ('- [ ] No [NEEDS CLARIFICATION] markers remain'), and
    instruction lines that demonstrate the marker ('Use [NEEDS CLARIFICATION:
    specific question] ...'). Requires the ':' of a real marker.
    """
    lines = raw.splitlines()
    fenced = _fence_mask(lines)
    count = 0
    for line, in_fence in zip(lines, fenced):
        if in_fence:
            continue
        stripped = line.lstrip()
        if stripped.startswith(">"):
            continue
        if _NO_CLARIF_RE.search(stripped):
            continue
        if _CLARIF_INSTRUCTION_RE.search(stripped):
            continue
        if _CLARIFICATION_RE.search(line):
            count += 1
    return count
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
_SHALL_RE = re.compile(r"\bshall\b", re.IGNORECASE)
# EARS shapes: ubiquitous ("The <system> shall ...") or keyword-led (When/While/Where/If ... shall).
_EARS_UBIQUITOUS_RE = re.compile(r"\bthe\s+[\w-]+(?:\s+[\w-]+){0,5}\s+shall\b", re.IGNORECASE)
_EARS_KEYWORD_RE = re.compile(r"\b(when|while|where|if)\b.*\bshall\b", re.IGNORECASE)


def _ears_pattern(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Advisory (info): 'shall' requirements that don't match an EARS shape."""
    p = catalog.get("REQ-EARS-PATTERN")
    if p is None or not p.applies_to(art.type):
        return []
    offenders: list[int] = []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        if _SHALL_RE.search(line) and not (
            _EARS_UBIQUITOUS_RE.search(line) or _EARS_KEYWORD_RE.search(line)
        ):
            offenders.append(i)
    if offenders:
        return [
            _from_pitfall(
                p, art.path,
                f"{len(offenders)} 'shall' requirement(s) not in an EARS pattern (advisory).",
                line=offenders[0],
            )
        ]
    return []


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


# Line-leading Gherkin keywords (Given/When/Then at start of a line, allowing
# optional bullet prefix).  "And" / "But" are continuations, not primary keywords,
# so they don't trigger the triad check by themselves.
_GHERKIN_GIVEN_RE = re.compile(r"^\s*[-*+]?\s*given\b", re.IGNORECASE | re.MULTILINE)
_GHERKIN_WHEN_RE = re.compile(r"^\s*[-*+]?\s*when\b", re.IGNORECASE | re.MULTILINE)
_GHERKIN_THEN_RE = re.compile(r"^\s*[-*+]?\s*then\b", re.IGNORECASE | re.MULTILINE)


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

# Pronoun subject immediately before a modal verb ("it shall", "they must", etc.)
# Does not include "will" — that word is not in _REQUIREMENTish_RE so those lines
# are not reached by this check.
_VAGUE_SUBJECT_RE = re.compile(
    r"\b(it|they|this|that|these|those)\s+(?:shall|must|should)\b",
    re.IGNORECASE,
)
# Requirement line with no noun subject — starts (after optional bullet/FR prefix) directly
# with a modal verb: "FR-001: shall generate a report" / "- Shall display the result"
_SUBJECTLESS_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:(?:FR|NFR)-\d+\s*:\s*)?(?:shall|must|should|will)\b",
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


def _unclear_actor(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines whose grammatical subject is a vague pronoun or entirely absent."""
    p = catalog.get("SPEC-UNCLEAR-ACTOR")
    if p is None or not p.applies_to(art.type):
        return []
    hits: list[int] = []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        if not _REQUIREMENTish_RE.search(line):
            continue
        if _VAGUE_SUBJECT_RE.search(line) or _SUBJECTLESS_RE.match(line):
            hits.append(i)
    if not hits:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"Requirement has unclear actor (pronoun or missing subject): {len(hits)} line(s).",
            line=hits[0],
        )
    ]


_STORY_OPENER_RE = re.compile(
    r"^\s*(?:[-*+]?\s*)?as an?\s+\S",
    re.IGNORECASE,
)
_I_WANT_RE = re.compile(r"\bi\s+want\b", re.IGNORECASE)
_SO_THAT_RE = re.compile(r"\bso\s+that\b", re.IGNORECASE)

# Open-ended enumeration markers that make scope impossible to bound (REQ-UNBOUNDED-SCOPE).
_UNBOUNDED_SCOPE_RE = re.compile(
    r"\betc\.?\b"
    r"|\band\s+so\s+on\b"
    r"|\band\s+others\b"
    r"|\band\s+more\b"
    r"|\bincluding\s+but\s+not\s+limited\s+to\b"
    r"|\bor\s+similar\b",
    re.IGNORECASE,
)
# Broader requirement filter: includes "will" and "want" in addition to _REQUIREMENTish_RE.
_REQ_BROAD_RE = re.compile(
    r"\b(?:shall|must|should|will|want|FR-\d|NFR-\d)\b",
    re.IGNORECASE,
)

# Rollback vocabulary: any mention of a recovery/undo strategy (PLAN-MISSING-ROLLBACK).
_ROLLBACK_RE = re.compile(
    r"\brollback\b|\brevert\b|\bfallback\b|\brecovery\b|\bundo\b|\bback\s+out\b",
    re.IGNORECASE,
)
# Deployment vocabulary: signs that a plan.md covers a deployment (guard).
_DEPLOY_VOCAB_RE = re.compile(
    r"\bdeploy(?:ment|ing|ed)?\b|\brelease\b|\bship(?:ping|ped)?\b"
    r"|\bproduction\b|\bstaging\b|\bprod\b",
    re.IGNORECASE,
)
# Section-title guard: a Deployment or Release section triggers the check.
_DEPLOY_SECTION_RE = re.compile(r"\b(?:deployment|release)\b", re.IGNORECASE)

# Object pronoun following a modal verb — dangling reference (SPEC-PRONOUN-ANTECEDENT).
# Matches: "shall ... it/them/their/this/that/these/those" within one sentence (no period).
# Uses _strict_req_mask so only requirement-bearing lines are examined.
_PRONOUN_ANTECEDENT_RE = re.compile(
    r"\b(?:shall|must)\b[^.\n]{0,120}\b(it|them|their|this|that|these|those)\b",
    re.IGNORECASE,
)


def _pronoun_antecedent(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines where a modal verb is followed by a vague object pronoun (SPEC-PRONOUN-ANTECEDENT)."""
    p = catalog.get("SPEC-PRONOUN-ANTECEDENT")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _strict_req_mask(art, lines)
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        # Skip lines where the pronoun is only the subject (SPEC-UNCLEAR-ACTOR covers those).
        # A subject pronoun appears BEFORE the modal; our regex anchors at the modal, so any
        # match is necessarily post-modal (object position) — but we still skip if the entire
        # subject pronoun + modal pattern fires on the same line to avoid double-counting a
        # line that SPEC-UNCLEAR-ACTOR already surfaces.
        if _VAGUE_SUBJECT_RE.search(line):
            continue
        m = _PRONOUN_ANTECEDENT_RE.search(line)
        if not m:
            continue
        hits.append((i + 1, m.group(1).lower()))
    if not hits:
        return []
    examples = ", ".join(sorted({h[1] for h in hits})[:3])
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-PRONOUN-ANTECEDENT: {len(hits)} requirement line(s) reference ambiguous object pronoun(s) ({examples}) after a modal verb.",
            line=hits[0][0],
        )
    ]


def _plan_missing_rollback(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans that never mention a rollback/revert/fallback strategy (PLAN-MISSING-ROLLBACK)."""
    p = catalog.get("PLAN-MISSING-ROLLBACK")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the plan uses deployment vocabulary or has a Deployment/Release section.
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    # Silent when any rollback vocabulary is present anywhere in the document.
    if _ROLLBACK_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Deployment plan has no rollback/revert/fallback strategy.")]


# Requirement ID pattern: FR-NNN, NFR-NNN, AC-NNN, or US-NNN (REQ-DUPLICATE-ID).
_REQ_ID_RE = re.compile(r"\b((?:FR|NFR|AC|US)-\d+)\b", re.IGNORECASE)

# Phase/Step heading pattern: section titles that name phases or steps (PLAN-NO-TESTING-STRATEGY guard).
_PHASE_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s.*\b(?:phase|step)\b", re.IGNORECASE | re.MULTILINE)
# Testing vocabulary: any mention of testing or verification strategy.
_TESTING_VOCAB_RE = re.compile(
    r"\b(?:test(?:s|ing)?|coverage|validat(?:e|ion)|verif(?:y|ication))\b",
    re.IGNORECASE,
)


def _plan_no_testing_strategy(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Multi-phase plan with no testing vocabulary (PLAN-NO-TESTING-STRATEGY)."""
    p = catalog.get("PLAN-NO-TESTING-STRATEGY")
    if p is None or not p.applies_to(art.type):
        return []
    phase_matches = _PHASE_HEADING_RE.findall(art.raw)
    if len(phase_matches) < 2:
        return []
    if _TESTING_VOCAB_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Multi-phase plan has no testing or verification strategy.")]


# Observability vocabulary: monitoring/logging/metrics/tracing/alerting/SLO/SLA (PLAN-MISSING-OBSERVABILITY).
_OBSERVABILITY_RE = re.compile(
    r"\bmonitor(?:ing)?\b|\blogging\b|\blog\s+level\b|\bmetrics?\b"
    r"|\bobservabilit\w+\b|\btrac(?:e|ing)\b|\balert(?:ing)?\b"
    r"|\bdashboard\b|\bSLO\b|\bSLA\b",
    re.IGNORECASE,
)


def _plan_missing_observability(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans that never mention observability (PLAN-MISSING-OBSERVABILITY)."""
    p = catalog.get("PLAN-MISSING-OBSERVABILITY")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the plan uses deployment vocabulary or has a Deployment/Release section.
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    # Silent when any observability vocabulary is present.
    if _OBSERVABILITY_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Deployment plan has no observability strategy (monitoring, logging, metrics, or alerting).")]


# Security-hardening vocabulary: auth/TLS/encrypt/secrets/RBAC/IAM/firewall/token/vault (PLAN-MISSING-SECURITY).
_SECURITY_RE = re.compile(
    r"\bauth(?:entication|orization|oriz)?\b|\bTLS\b|\bSSL\b|\bencrypt\w*\b"
    r"|\bsecret(?:s)?\b|\bcredential(?:s)?\b|\bcertif(?:icate|y)?\b"
    r"|\bRBAC\b|\bIAM\b|\bfirewall\b|\baccess[\s\-]control\b"
    r"|\btoken(?:s)?\b|\bmTLS\b|\bvault\b",
    re.IGNORECASE,
)


def _plan_missing_security(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans that never mention security hardening (PLAN-MISSING-SECURITY)."""
    p = catalog.get("PLAN-MISSING-SECURITY")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the plan uses deployment vocabulary or has a Deployment/Release section.
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    # Silent when any security vocabulary is present.
    if _SECURITY_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Deployment plan has no security hardening mention (auth, TLS, encryption, secrets management, or access control).")]


# Non-normative modal verbs that weaken requirements (REQ-WEAK-DIRECTIVE).
_WEAK_MODAL_RE = re.compile(r"\b(should|may|could|might)\b", re.IGNORECASE)
# Normative modal verbs that override: if shall/must also present, it's a legitimate conditional.
_MANDATORY_MODAL_RE = re.compile(r"\b(shall|must)\b", re.IGNORECASE)
# Explicit requirement-ID label: FR-N, NFR-N, AC-N, US-N on the same line.
_STRICT_REQ_ID_LINE_RE = re.compile(r"\b(?:FR|NFR|AC|US)-\d+\b", re.IGNORECASE)


def _strict_req_mask(art: Artifact, lines: list[str]) -> list[bool]:
    """True only for lines that are explicitly in a Requirements/Acceptance/Scenario section
    OR carry an FR-/NFR-/AC-/US- label.  Stricter than _requirement_mask — does NOT mark
    arbitrary prose lines containing 'should' as requirement-bearing."""
    mask = [False] * len(lines)
    secs = art.sections
    for idx, s in enumerate(secs):
        if not _REQ_SECTION_TITLE_RE.search(s.title):
            continue
        start = s.line - 1
        end = secs[idx + 1].line - 1 if idx + 1 < len(secs) else len(lines)
        for i in range(start, min(end, len(lines))):
            mask[i] = True
    for i, line in enumerate(lines):
        if not mask[i] and _STRICT_REQ_ID_LINE_RE.search(line):
            mask[i] = True
    return mask


def _weak_directive(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines using non-normative modals instead of shall/must (REQ-WEAK-DIRECTIVE)."""
    p = catalog.get("REQ-WEAK-DIRECTIVE")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _strict_req_mask(art, lines)
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        m = _WEAK_MODAL_RE.search(line)
        if not m:
            continue
        # Skip lines where shall/must also appears — legitimate EARS conditional.
        if _MANDATORY_MODAL_RE.search(line):
            continue
        hits.append((i + 1, m.group(1).lower()))
    if not hits:
        return []
    examples = ", ".join(sorted({h[1] for h in hits})[:3])
    return [
        _from_pitfall(
            p,
            art.path,
            f"REQ-WEAK-DIRECTIVE: {len(hits)} requirement line(s) use non-normative modal(s) ({examples}) instead of 'shall'/'must'.",
            line=hits[0][0],
        )
    ]


def _req_duplicate_id(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Duplicate FR/NFR/AC/US requirement identifiers within spec.md (REQ-DUPLICATE-ID)."""
    p = catalog.get("REQ-DUPLICATE-ID")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    counts: dict[str, int] = {}
    first_line: dict[str, int] = {}
    for i, line in enumerate(lines):
        if fenced[i] or not line.strip():
            continue
        for m in _REQ_ID_RE.finditer(line):
            uid = m.group(1).upper()
            counts[uid] = counts.get(uid, 0) + 1
            if uid not in first_line:
                first_line[uid] = i + 1
    dupes = sorted(uid for uid, cnt in counts.items() if cnt > 1)
    if not dupes:
        return []
    examples = ", ".join(dupes[:3])
    suffix = f" (and {len(dupes) - 3} more)" if len(dupes) > 3 else ""
    return [
        _from_pitfall(
            p,
            art.path,
            f"Duplicate requirement ID(s): {examples}{suffix}.",
            line=first_line[dupes[0]],
        )
    ]


def _story_no_benefit(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """User stories missing the 'so that [benefit]' clause (Connextra format / INVEST Valuable)."""
    p = catalog.get("SPEC-STORY-NO-BENEFIT")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    # Guard: skip specs that use no user story format at all.
    has_stories = any(
        _STORY_OPENER_RE.match(line) and _I_WANT_RE.search(line) for line in lines
    )
    if not has_stories:
        return []
    missing: list[int] = []
    for i, line in enumerate(lines):
        if _STORY_OPENER_RE.match(line) and _I_WANT_RE.search(line):
            if _SO_THAT_RE.search(line):
                continue
            # Check next non-blank line for continuation.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and _SO_THAT_RE.search(lines[j]):
                continue
            missing.append(i + 1)  # 1-indexed
    if not missing:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"User story missing 'so that [benefit]' clause: {len(missing)} story(ies).",
            line=missing[0],
        )
    ]


def _unbounded_scope(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines with open-ended enumerations that bound scope (REQ-UNBOUNDED-SCOPE)."""
    p = catalog.get("REQ-UNBOUNDED-SCOPE")
    if p is None or not p.applies_to(art.type):
        return []
    hits: list[int] = []
    for i, line in enumerate(art.raw.splitlines(), start=1):
        if _REQ_BROAD_RE.search(line) and _UNBOUNDED_SCOPE_RE.search(line):
            hits.append(i)
    if not hits:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"Requirement contains open-ended enumeration (unbounded scope): {len(hits)} line(s).",
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

    # Per-artifact checks. Required-section + lexical pitfalls apply universally;
    # structural checks are delegated to the adapter so each toolchain's rules stay
    # behind the adapter seam and lint() itself is toolchain-agnostic.
    for art in artifacts:
        findings.extend(_required_sections(art, adapter, root))
        findings.extend(_lexical_pitfalls(art, catalog))
        findings.extend(adapter.structural_checks(art, catalog))

    # Cross-artifact checks (story→task, entity→task, contract test) are also
    # toolchain-specific — delegate to the adapter.
    findings.extend(adapter.cross_artifact_checks(artifacts, catalog))
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
                    suggestion=f"Add a '## {title}' section "
                    f"(see the {getattr(adapter, 'name', 'toolchain')} "
                    f"{art.type.value} template).",
                    source=Source.LINT,
                    artifact_path=art.path,
                )
            )
    return out


# --------------------------------------------------------------------------- layer 2

_INLINE_CODE_RE = re.compile(r"`[^`]+`")

# Requirement-smell pitfalls: their patterns describe defects *in requirements*
# (ambiguity, hedging, tech leakage, speculation), so they only match in
# requirement-bearing contexts — not user-story narrative, overview prose, or
# out-of-scope declarations, where the same words are benign.
_REQUIREMENT_SCOPED_PITFALLS = frozenset({
    "SPEC-AMBIGUOUS-WORDING",
    "SPEC-COMPARATIVE-NO-REFERENCE",
    "SPEC-ESCAPE-CLAUSE",
    "SPEC-IMPL-DETAIL-LEAK",
    "SPEC-SPECULATIVE-FEATURE",
})

# Section titles whose contents are requirement-bearing.
_REQ_SECTION_TITLE_RE = re.compile(r"requirement|acceptance|scenario", re.IGNORECASE)

# A line that itself looks like a requirement: modal verb or an FR-/NFR- id
# (multi-digit, unlike _REQUIREMENTish_RE whose FR-\d\b only matches one digit).
_REQ_LINE_RE = re.compile(r"\b(?:shall|must|should)\b|\b(?:FR|NFR)-\d+", re.IGNORECASE)

# Sections that describe the problem domain (used to suppress impl-detail hits on
# terms that ARE the domain, e.g. a spec for a Python code-review tool).
_DOMAIN_SECTION_TITLE_RE = re.compile(
    r"^(overview|summary|introduction|purpose|background|context)\b", re.IGNORECASE
)


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for lines inside (or delimiting) fenced code blocks — same fence
    tracking parse_sections uses."""
    mask: list[bool] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            mask.append(True)
        else:
            mask.append(in_fence)
    return mask


def _requirement_mask(art: Artifact, lines: list[str]) -> list[bool]:
    """True for lines in a requirement-bearing context: inside a Requirements /
    Acceptance / Scenario section, or a line that itself looks like a requirement
    (shall/must/should, FR-/NFR- id)."""
    mask = [False] * len(lines)
    secs = art.sections
    for idx, s in enumerate(secs):
        if not _REQ_SECTION_TITLE_RE.search(s.title):
            continue
        start = s.line - 1  # include the heading line itself
        end = secs[idx + 1].line - 1 if idx + 1 < len(secs) else len(lines)
        for i in range(start, min(end, len(lines))):
            mask[i] = True
    for i, line in enumerate(lines):
        if not mask[i] and _REQ_LINE_RE.search(line):
            mask[i] = True
    return mask


def _domain_text(art: Artifact) -> str:
    """Lower-cased text of the spec's title and overview-like sections — a term
    appearing here is the problem domain, not a leaked implementation choice."""
    parts: list[str] = []
    for s in art.sections:
        if s.level == 1 or _DOMAIN_SECTION_TITLE_RE.match(s.title.strip()):
            parts.append(s.title)
            parts.append(s.body)
    if not parts:  # no headings at all — fall back to the first line
        lines = art.raw.splitlines()
        if lines:
            parts.append(lines[0])
    return "\n".join(parts).lower()


def _lexical_pitfalls(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """One finding per matching lexical pitfall, summarizing the matches.

    Fenced code blocks and inline code spans are never matched. Requirement-smell
    pitfalls (see _REQUIREMENT_SCOPED_PITFALLS) match only requirement-bearing
    lines; impl-detail hits on the spec's own domain terms are suppressed.
    """
    out: list[Finding] = []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask: list[bool] | None = None  # built lazily
    domain: str | None = None
    for p in catalog.values():
        if not p.compiled or not p.lint_detectable or not p.applies_to(art.type):
            continue
        scoped = p.id in _REQUIREMENT_SCOPED_PITFALLS
        if scoped and req_mask is None:
            req_mask = _requirement_mask(art, lines)
        hits: list[tuple[int, str]] = []
        for i, line in enumerate(lines, start=1):
            if fenced[i - 1]:
                continue
            if scoped and req_mask is not None and not req_mask[i - 1]:
                continue
            text = _INLINE_CODE_RE.sub("", line)
            for rx in p.compiled:
                m = rx.search(text)
                if not m:
                    continue
                if p.id == "SPEC-IMPL-DETAIL-LEAK":
                    if domain is None:
                        domain = _domain_text(art)
                    if m.group(0).lower() in domain:
                        continue  # the term is the problem domain, not a leak
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
    clar_count = _count_real_clarification_markers(art.raw)
    if clar_count and (p := catalog.get("SPEC-UNRESOLVED-CLARIFICATION")):
        out.append(
            _from_pitfall(p, art.path, f"{clar_count} unresolved [NEEDS CLARIFICATION] marker(s).")
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
    # block that isn't just a TODO).  Also look at sibling/child sections whose title
    # suggests acceptance criteria — the canonical Spec-Kit layout puts them in a
    # separate "### Acceptance Scenarios" section after "### Primary User Story".
    if p := catalog.get("SPEC-MISSING-ACCEPTANCE"):
        for i, s in enumerate(art.sections):
            if "user story" in s.title.lower():
                combined = s.body
                for following in art.sections[i + 1:]:
                    if following.level < s.level:
                        break  # parent section: stop
                    if "user story" in following.title.lower():
                        break  # next story: these sections belong to it
                    t = following.title.lower()
                    if "acceptance" in t or "scenario" in t:
                        combined += "\n" + following.body
                body = combined.lower()
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

    # Malformed Gherkin: AC section is in "formal Gherkin mode" (≥2 distinct
    # keywords each leading their own line) but the triad is incomplete.
    # Single line-leading keywords are not checked — prose ACs written as
    # "- Given ..., when ..., then ..." have only Given line-leading and are fine.
    if p := catalog.get("SPEC-GHERKIN-MALFORMED-AC"):
        for i, s in enumerate(art.sections):
            if "user story" in s.title.lower():
                combined = s.body
                for following in art.sections[i + 1:]:
                    if following.level < s.level:
                        break
                    if "user story" in following.title.lower():
                        break
                    t = following.title.lower()
                    if "acceptance" in t or "scenario" in t:
                        combined += "\n" + following.body
                has_given = bool(_GHERKIN_GIVEN_RE.search(combined))
                has_when = bool(_GHERKIN_WHEN_RE.search(combined))
                has_then = bool(_GHERKIN_THEN_RE.search(combined))
                leading_count = sum([has_given, has_when, has_then])
                # Enter formal Gherkin mode only when ≥2 keywords each head their own line.
                if leading_count >= 2 and not (has_given and has_when and has_then):
                    missing = [kw for kw, ok in [("Given", has_given), ("When", has_when), ("Then", has_then)] if not ok]
                    out.append(
                        _from_pitfall(
                            p, art.path,
                            f"User story '{s.title}' has partial Gherkin AC (missing: {', '.join(missing)}).",
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
    out.extend(_unclear_actor(art, catalog))
    out.extend(_ears_pattern(art, catalog))
    out.extend(_story_no_benefit(art, catalog))
    out.extend(_unbounded_scope(art, catalog))
    out.extend(_req_duplicate_id(art, catalog))
    out.extend(_weak_directive(art, catalog))
    out.extend(_pronoun_antecedent(art, catalog))
    return out


def _plan_checks(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []

    clar_count = _count_real_clarification_markers(art.raw)
    if clar_count and (p := catalog.get("SPEC-UNRESOLVED-CLARIFICATION")):
        out.append(_from_pitfall(p, art.path, f"{clar_count} unresolved [NEEDS CLARIFICATION] marker(s)."))

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
    out.extend(_unclear_actor(art, catalog))
    out.extend(_unbounded_scope(art, catalog))
    out.extend(_plan_missing_rollback(art, catalog))
    out.extend(_plan_no_testing_strategy(art, catalog))
    out.extend(_plan_missing_observability(art, catalog))
    out.extend(_plan_missing_security(art, catalog))
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


# Headings in constitution.md that are structural (not principle names).
_GENERIC_CONSTITUTION_HEADINGS: frozenset[str] = frozenset({
    "governance", "overview", "core principles", "introduction",
    "summary", "preamble", "history", "amendments", "ratification",
})

# Placeholder principle names left from the constitution template.
_PRINCIPLE_PLACEHOLDER_RE = re.compile(r"\[PRINCIPLE_\d", re.IGNORECASE)


def _constitution_principles(constitution: Artifact) -> list[str]:
    """Extract authored (non-placeholder) principle names from constitution.md headings."""
    names: list[str] = []
    for s in constitution.sections:
        if s.level not in (2, 3):
            continue
        name = s.title.strip()
        if not name:
            continue
        if name.lower() in _GENERIC_CONSTITUTION_HEADINGS:
            continue
        if _PRINCIPLE_PLACEHOLDER_RE.search(name):
            continue
        names.append(name)
    return names


# --------------------------------------------------------------------------- cross-artifact

def _cross_artifact(artifacts: list[Artifact], catalog: dict[str, Pitfall]) -> list[Finding]:
    out: list[Finding] = []
    by_feature: dict[str | None, list[Artifact]] = {}
    for a in artifacts:
        by_feature.setdefault(a.feature_id, []).append(a)

    # Constitution lives at repo root (feature_id=None); gather its principles once.
    constitution_global = _first(by_feature.get(None, []), ArtifactType.CONSTITUTION)
    global_principles = _constitution_principles(constitution_global) if constitution_global else []

    for feature, arts in by_feature.items():
        if feature is None:
            continue
        spec = _first(arts, ArtifactType.SPEC)
        tasks = _first(arts, ArtifactType.TASKS)
        data_model = _first(arts, ArtifactType.DATA_MODEL)
        contracts = [a for a in arts if a.type == ArtifactType.CONTRACT]
        plan = _first(arts, ArtifactType.PLAN)

        # Constitution crosscheck: plan's Constitution Check section must reference
        # at least one actual principle name from constitution.md.
        # Runs even without tasks.md (it's a plan-only check).
        if global_principles and plan and (p := catalog.get("SPECKIT-CONSTITUTION-CROSSCHECK")):
            check_section = plan.section("Constitution Check")
            if check_section and check_section.body.strip():
                body_lower = check_section.body.lower()
                matched = any(principle.lower() in body_lower for principle in global_principles)
                if not matched:
                    out.append(
                        _from_pitfall(
                            p, plan.path,
                            "Constitution Check does not reference any principle names from constitution.md.",
                        )
                    )

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
                if not _entity_word_re(entity).search(tasks_text):
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


# Structural sub-section titles that appear inside entity blocks but are not
# entity names themselves.  Treating these as entities produces bogus findings.
_STRUCTURAL_HEADINGS: frozenset[str] = frozenset({
    "attributes", "attribute",
    "fields", "field",
    "properties", "property",
    "validation rules", "validation rule", "validation",
    "state transitions", "state transition", "states", "state",
    "migrations", "migration",
    "relationships", "relationship",
    "indexes", "index", "indices",
    "constraints", "constraint",
    "notes", "note",
    "references", "reference",
    "examples", "example",
    "overview", "summary", "description",
    "schema", "schemas",
    "types", "type",
    "enums", "enum", "enumerations", "enumeration",
})

_ENTITY_WORD_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _entity_word_re(entity: str) -> re.Pattern[str]:
    """Word-boundary pattern for *entity* (cached)."""
    key = entity.lower()
    if key not in _ENTITY_WORD_RE_CACHE:
        _ENTITY_WORD_RE_CACHE[key] = re.compile(
            r"(?<!\w)" + re.escape(key) + r"(?!\w)", re.IGNORECASE
        )
    return _ENTITY_WORD_RE_CACHE[key]


def _entities(data_model: Artifact) -> list[str]:
    """Entity names from data-model.md: level-3+ headings, skipping structural subsections."""
    names: list[str] = []
    for s in data_model.sections:
        if s.level >= 3 and s.title.strip():
            if s.title.strip().lower() not in _STRUCTURAL_HEADINGS:
                names.append(s.title.strip())
    return names

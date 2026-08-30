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
_US_TAG_NUM_RE = re.compile(r"\[US(\d+)\]", re.IGNORECASE)  # capturing variant
_US_HEADING_RE = re.compile(r"user stor(?:y|ies)\s*(\d+)", re.IGNORECASE)
_ESTIMATE_RE = re.compile(
    r"""
    \b\d+\s*sp\b              # story points: "3 sp", "3sp"
    | \bsp\s*[:=]\s*\d+       # "sp: 3"
    | \b\d+\s*pts?\b           # "3 pt", "3 pts"
    | \(\d+\s*points?\)        # "(3 points)"
    | \[(?:XS|XL|XXL)\]        # t-shirt in brackets: "[XL]", "[XXL]" (avoid [S]/[L] false pos)
    | \bsize\s*[:=]\s*(?:XS|S|M|L|XL|XXL)\b   # "size: M"
    | \bt-?shirt\s*[:=]\s*(?:XS|S|M|L|XL|XXL)\b  # "t-shirt: L"
    | \b\d+\s*(?:h\b|hr\b|hrs\b|hours?\b)    # "2h", "2 hrs", "2 hours"
    | \b\d+(?:\.\d+)?\s*days?\b               # "1 day", "2 days"
    """,
    re.IGNORECASE | re.VERBOSE,
)
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
_I_WANT_TO_RE = re.compile(r"\bi\s+want\s+to\b", re.IGNORECASE)
_SO_THAT_RE = re.compile(r"\bso\s+that\b", re.IGNORECASE)
# Compound-want detector: any 'and' as a whole word in the want-clause portion.
_COMPOUND_AND_RE = re.compile(r"\band\b", re.IGNORECASE)

# Vague outcome adverbs in Gherkin Then clauses (SPEC-AC-VAGUE-OUTCOME).
_VAGUE_OUTCOME_RE = re.compile(
    r"\b(?:correctly|properly|appropriately|as\s+expected|as\s+intended)\b",
    re.IGNORECASE,
)

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

# Future-tense phrasing in requirements — enforceability defect (SPEC-FUTURE-TENSE-REQ).
# ISO/IEC/IEEE 29148:2018 mandates present-tense normative statements; "will be" and
# similar future-tense constructions express intent rather than obligation.
_FUTURE_TENSE_RE = re.compile(
    r"\b(will\s+be|would\s+be|will\s+support|will\s+allow|will\s+provide|will\s+enable|will\s+handle)\b",
    re.IGNORECASE,
)

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


def _future_tense_req(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement lines using future-tense phrasing instead of normative shall/must (SPEC-FUTURE-TENSE-REQ)."""
    p = catalog.get("SPEC-FUTURE-TENSE-REQ")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _strict_req_mask(art, lines)
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        m = _FUTURE_TENSE_RE.search(line)
        if not m:
            continue
        # A line that also contains shall/must is a mixed normative statement — skip.
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
            f"SPEC-FUTURE-TENSE-REQ: {len(hits)} requirement line(s) use future-tense phrasing ({examples}) instead of normative 'shall'/'must'.",
            line=hits[0][0],
        )
    ]


# Requirements section with prose but no normative statements (SPEC-REQ-SECTION-PROSE-ONLY).
# IBM RQA Completeness L1 / QVscribe Identifiability / ISO 29148 §5.2.
_PROSE_REQ_SECTION_RE = re.compile(
    r"\b(?:functional\s+)?requirements?\b", re.IGNORECASE
)
_FORMAL_REQ_INDICATOR_RE = re.compile(
    r"\b(?:shall|must)\b|\b(?:FR|NFR|AC|US)-\d+\b",
    re.IGNORECASE,
)


def _req_section_prose_only(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirements section with substantial body text but no normative statements (SPEC-REQ-SECTION-PROSE-ONLY)."""
    p = catalog.get("SPEC-REQ-SECTION-PROSE-ONLY")
    if p is None or not p.applies_to(art.type):
        return []
    out: list[Finding] = []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    for s in art.sections:
        if not _PROSE_REQ_SECTION_RE.search(s.title):
            continue
        body = s.body.strip()
        if len(body) < 30:
            continue
        # Strip fenced blocks from the section body before checking for normative indicators.
        # We need to check only non-fenced lines of the section.
        section_lines = body.splitlines()
        section_fenced = _fence_mask(section_lines)
        clean_body = "\n".join(
            ln for ln, in_fence in zip(section_lines, section_fenced) if not in_fence
        )
        if not _FORMAL_REQ_INDICATOR_RE.search(clean_body):
            out.append(
                _from_pitfall(
                    p,
                    art.path,
                    f"SPEC-REQ-SECTION-PROSE-ONLY: section '{s.title}' contains prose but no normative statements (shall/must or FR-/NFR-/AC-/US- IDs).",
                    line=s.line,
                )
            )
    return out


def _req_no_id(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Normative requirement line (shall/must) in a requirements section missing a formal ID (SPEC-REQ-NO-ID)."""
    p = catalog.get("SPEC-REQ-NO-ID")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    secs = art.sections
    hits: list[tuple[int, str]] = []
    for idx, s in enumerate(secs):
        if not _REQ_SECTION_TITLE_RE.search(s.title):
            continue
        start = s.line - 1
        end = secs[idx + 1].line - 1 if idx + 1 < len(secs) else len(lines)
        # Guard: skip sections with no normative modal — SPEC-REQ-SECTION-PROSE-ONLY covers those.
        section_has_modal = any(
            not fenced[i] and not lines[i].lstrip().startswith("#") and _MANDATORY_MODAL_RE.search(lines[i])
            for i in range(start, min(end, len(lines)))
        )
        if not section_has_modal:
            continue
        for i in range(start, min(end, len(lines))):
            ln = lines[i]
            if fenced[i] or not ln.strip() or ln.lstrip().startswith("#"):
                continue
            if _MANDATORY_MODAL_RE.search(ln) and not _STRICT_REQ_ID_LINE_RE.search(ln):
                hits.append((i + 1, ln.strip()))
    if not hits:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-REQ-NO-ID: {len(hits)} normative requirement line(s) lack a formal identifier (FR-/NFR-/AC-/US-NNN); first at line {hits[0][0]}.",
            line=hits[0][0],
        )
    ]


# Spec with no Out-of-Scope / Non-Goals section despite having substantial requirements (SPEC-MISSING-OUT-OF-SCOPE).
# Amazon Kiro, Tessl, ISO 29148 §5.2.4.
_OUT_OF_SCOPE_HEADING_RE = re.compile(
    r"out[\s._-]*of[\s._-]*scope|non[\s._-]?goal|not\s+in\s+scope|exclusion|"
    r"scope[\s._-]*boundar|won.?t\s+do|will\s+not",
    re.IGNORECASE,
)
# Matches a normative indicator line: shall/must modal or formal FR-/NFR-/AC-/US- identifier.
_NORMATIVE_LINE_RE = re.compile(
    r"\b(?:shall|must)\b|\b(?:FR|NFR|AC|US)-\d+\b",
    re.IGNORECASE,
)
# US-NNN section heading title prefix (SPEC-FR-NO-STORY guard): matches section titles
# that begin with a US-NNN identifier — e.g. "US-001", "US-001: Login Feature".
# Applied to art.sections[i].title (the text after stripping leading '#' characters).
_US_NNN_TITLE_RE = re.compile(r"^US-\d+\b", re.IGNORECASE)
# FR or NFR identifier on a line (SPEC-FR-NO-STORY):
_FR_NFR_LINE_RE = re.compile(r"\b(?:FR|NFR)-\d+\b", re.IGNORECASE)
# FR-NNN only (not NFR-NNN) — used by SPEC-AC-NO-FR-LINK co-reference check.
# \bFR-\d+\b cannot match NFR-NNN because 'F' in NFR is not at a word boundary.
_FR_ID_RE = re.compile(r"\bFR-\d+\b", re.IGNORECASE)
# AC-NNN non-capturing variant for presence checks (SPEC-AC-NO-FR-LINK).
# (A capturing variant _AC_ID_RE is used by the XREF-AC-NO-TASK cross-artifact check.)
_AC_NNN_RE = re.compile(r"\bAC-\d+\b", re.IGNORECASE)


def _spec_ac_no_fr_link(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec with both FR-NNN and AC-NNN identifiers but no line co-referencing both (SPEC-AC-NO-FR-LINK).

    Guard: only fires when both FR-NNN and AC-NNN identifiers appear on non-fenced lines.
    When the guard fires: scans every non-fenced line for one that contains both an
    FR-NNN identifier and an AC-NNN identifier.  Returns one aggregate finding if no
    such co-reference line exists.

    Canon Fit Criterion / MAQA Traceability Level-2: every AC must explicitly reference
    the FR it validates so coverage completeness can be checked mechanically.
    """
    p = catalog.get("SPEC-AC-NO-FR-LINK")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    # Guard: both identifier types must appear somewhere in the spec.
    has_fr = any(not fenced[i] and _FR_ID_RE.search(ln) for i, ln in enumerate(lines))
    has_ac = any(not fenced[i] and _AC_NNN_RE.search(ln) for i, ln in enumerate(lines))
    if not (has_fr and has_ac):
        return []
    # Check: is there any non-fenced line containing both an FR-NNN and an AC-NNN?
    for i, ln in enumerate(lines):
        if fenced[i]:
            continue
        if _FR_ID_RE.search(ln) and _AC_NNN_RE.search(ln):
            return []  # co-reference found → silent
    return [
        _from_pitfall(
            p,
            art.path,
            "SPEC-AC-NO-FR-LINK: spec defines both FR-NNN and AC-NNN identifiers but no line "
            "co-references both; add explicit FR↔AC links (e.g. 'AC-001 [FR-001]: …').",
        )
    ]


def _spec_fr_no_story(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """FR-/NFR- lines in spec outside any US-NNN section with no [US#] link (SPEC-FR-NO-STORY).

    Guard: only fires when the spec has ≥1 section heading whose title begins with
    'US-NNN' (e.g. '## US-001', '### US-001: Login').  Specs that organise stories
    under 'User Story N' headings (the common Spec-Kit format) are not subject to this
    check — it targets the US-NNN-headed layout where every FR is expected to live
    inside its parent US section or carry an explicit '[US#]' cross-reference tag.
    """
    p = catalog.get("SPEC-FR-NO-STORY")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: at least one US-NNN section heading must exist.
    us_sections = [s for s in art.sections if _US_NNN_TITLE_RE.match(s.title)]
    if not us_sections:
        return []
    # Build the set of 0-indexed line numbers that are inside a US-NNN section.
    # Each US-NNN section spans from its heading line up to (but not including)
    # the line of the next heading at the same or lower depth.
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    us_lines: set[int] = set()
    for idx, s in enumerate(art.sections):
        if not _US_NNN_TITLE_RE.match(s.title):
            continue
        start = s.line - 1  # 0-indexed heading line
        # End is the next sibling/ancestor heading line, or EOF.
        end = len(lines)
        for following in art.sections[idx + 1:]:
            if following.level <= s.level:
                end = following.line - 1  # 0-indexed
                break
        for i in range(start, end):
            us_lines.add(i)
    # Collect FR-/NFR- lines that are outside all US-NNN sections and have no [US#] tag.
    orphans: list[int] = []
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        if not _FR_NFR_LINE_RE.search(line):
            continue
        if i in us_lines:
            continue
        if _US_TAG_RE.search(line):
            continue
        orphans.append(i + 1)  # 1-indexed
    if not orphans:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-FR-NO-STORY: {len(orphans)} FR-/NFR- line(s) sit outside any US-NNN section "
            f"with no [US#] link — unowned requirement(s).",
            line=orphans[0],
        )
    ]


# SPEC-MAQA-AC-CONDITIONAL: conditional or non-normative modal language in Gherkin Then clauses.
# Explicit conditionals: if, unless, depending, provided that, in the event.
_THEN_CONDITIONAL_RE = re.compile(
    r"\b(?:if|unless|depending|provided\s+that|in\s+the\s+event)\b",
    re.IGNORECASE,
)
# Non-normative modals that make the step optional rather than mandatory.
_THEN_OPTIONAL_MODAL_RE = re.compile(r"\b(?:should|may|might|could)\b", re.IGNORECASE)


def _spec_maqa_ac_conditional(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Then clause with conditional or non-normative modal language (SPEC-MAQA-AC-CONDITIONAL).

    MAQA binary-verifiability rule: every Then step must be an unconditional, binary
    assertion.  Conditional language (if/unless/depending) makes the outcome
    context-dependent; non-normative modals (should/may/might/could) make it optional.
    Both make the step impossible to evaluate as a deterministic pass/fail test.

    Guard: only fires in formal-Gherkin mode — at least one Given line-leader AND one
    When line-leader must each start their own line.  Prose ACs are not checked.
    """
    p = catalog.get("SPEC-MAQA-AC-CONDITIONAL")
    if p is None or not p.applies_to(art.type):
        return []
    raw = art.raw
    # Require formal Gherkin mode: both a Given and a When line-leader present.
    if not (_GHERKIN_GIVEN_RE.search(raw) and _GHERKIN_WHEN_RE.search(raw)):
        return []
    lines = raw.splitlines()
    fenced = _fence_mask(lines)
    hits: list[int] = []
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        if not _GHERKIN_THEN_RE.match(line):
            continue
        if _THEN_CONDITIONAL_RE.search(line) or _THEN_OPTIONAL_MODAL_RE.search(line):
            hits.append(i + 1)  # 1-indexed
    if not hits:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-MAQA-AC-CONDITIONAL: {len(hits)} Then clause(s) use conditional or non-normative "
            "modal language (if/unless/depending/should/may/might/could); replace with a binary, "
            "unconditional assertion.",
            line=hits[0],
        )
    ]


# SPEC-GHERKIN-MISSING-GIVEN: When step without a preceding Given in the same scenario block.
_SCENARIO_HEADING_RE = re.compile(r"^\s*(?:#+\s*)?scenario(?:\s+outline)?\b", re.IGNORECASE)


def _spec_gherkin_missing_given(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """When step without a preceding Given in the same scenario block (SPEC-GHERKIN-MISSING-GIVEN).

    MAQA completeness rule: every Gherkin scenario must declare its initial state (Given)
    before the action (When). A When without Given leaves the precondition undefined,
    making the test non-reproducible across environments.

    Guard: formal-Gherkin mode — at least one When line-leader AND one Then line-leader
    present in the document.  Prose ACs without a When/Then structure are skipped.
    Block boundaries are: a Scenario:/Scenario Outline: heading, or 2+ consecutive blank
    lines before another When.
    """
    p = catalog.get("SPEC-GHERKIN-MISSING-GIVEN")
    if p is None or not p.applies_to(art.type):
        return []
    raw = art.raw
    # Require formal Gherkin mode: a When line-leader AND a Then line-leader present.
    if not (_GHERKIN_WHEN_RE.search(raw) and _GHERKIN_THEN_RE.search(raw)):
        return []
    lines = raw.splitlines()
    fenced = _fence_mask(lines)

    hits: list[int] = []
    in_block_given = False  # whether a Given appeared since the last block reset
    blank_streak = 0

    for i, line in enumerate(lines):
        if fenced[i]:
            blank_streak = 0
            continue
        stripped = line.strip()

        if not stripped:
            blank_streak += 1
            if blank_streak >= 2:
                # Two or more consecutive blank lines reset the scenario block.
                in_block_given = False
            continue
        blank_streak = 0

        # Scenario:/Scenario Outline: heading resets the block.
        if _SCENARIO_HEADING_RE.match(line):
            in_block_given = False
            continue

        # Given line-leader: mark that the current block has a Given.
        if _GHERKIN_GIVEN_RE.match(line):
            in_block_given = True
            continue

        # When line-leader without a preceding Given in this block → fire.
        if _GHERKIN_WHEN_RE.match(line) and not in_block_given:
            hits.append(i + 1)  # 1-indexed

    if not hits:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-GHERKIN-MISSING-GIVEN: {len(hits)} When step(s) without a preceding Given "
            "in the same scenario block; add a Given step to declare the system's initial state.",
            line=hits[0],
        )
    ]


# SPEC-QVSCRIBE-AND-OR: "and/or" ambiguous conjunction on requirement-bearing lines.
_AND_OR_RE = re.compile(r"\band/or\b", re.IGNORECASE)


def _spec_qvscribe_and_or(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """'and/or' ambiguous conjunction on requirement-bearing lines (SPEC-QVSCRIBE-AND-OR).

    QVscribe Level-1 Clarity defect and ISO 29148 §5.2.5(a) 'unambiguous' characteristic.
    'and/or' is inherently ambiguous — readers cannot determine whether both must be
    satisfied (AND), either suffices (inclusive OR), or exactly one applies (exclusive OR).
    Check is scoped to requirement-bearing lines only via _requirement_mask() to avoid
    false positives in prose paragraphs; fenced code blocks are always excluded.
    """
    p = catalog.get("SPEC-QVSCRIBE-AND-OR")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _AND_OR_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-AND-OR: {count} requirement line(s) use ambiguous 'and/or' conjunction; "
            "replace with 'and' or 'or' depending on intent.",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-SHALL-BE-ABLE-TO: "shall be able to" dilutes mandatory obligation to a latent capability.
_SHALL_BE_ABLE_TO_RE = re.compile(r"\bshall\s+be\s+able\s+to\b", re.IGNORECASE)


def _spec_qvscribe_shall_be_able_to(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """'shall be able to' capability phrasing dilutes mandatory obligation (SPEC-QVSCRIBE-SHALL-BE-ABLE-TO).

    QVscribe's Level-1 Capability/Optionality defect: 'shall' mandates that an action
    *occurs*; 'shall be able to' only mandates that the *capability exists* — a system
    could pass acceptance if the capability is wired up but never exercised. IBM RQA
    enforceability check and ISO/IEC/IEEE 29148:2018 §5.2.5(i) 'verifiable' both require
    the requirement to state what the system *does*, not merely what it *can do*.
    Check is scoped to requirement-bearing lines via _requirement_mask(); fenced blocks
    are always excluded.
    """
    p = catalog.get("SPEC-QVSCRIBE-SHALL-BE-ABLE-TO")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _SHALL_BE_ABLE_TO_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-SHALL-BE-ABLE-TO: {count} requirement line(s) use 'shall be able to', "
            "diluting a mandatory obligation to a latent capability; "
            "replace with 'shall <verb>' to state what the system does, not what it can do.",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED: temporal universals in requirement lines.
# QVscribe Continuance defect: 'always'/'never'/'at all times'/'continuously' on a normative
# line cannot be verified by any finite test suite (ISO 29148 §5.2.5(i) verifiability).
_TEMPORAL_UNIVERSAL_RE = re.compile(
    r"""(?:
        \balways\b
        | \bnever\b
        | \bat\s+all\s+times?\b
        | \bcontinuously\b
        | \bat\s+every\b
        | \bat\s+no\s+time\b
        | \binvariably\b
        | \bperpetually\b
        | \bwithout\s+exception\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def _spec_qvscribe_temporal_unbounded(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Temporal universal in a requirement line makes it unverifiable (SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED).

    QVscribe's Continuance defect class: words like 'always', 'never', 'at all times',
    'continuously' appear on requirement-bearing lines and render the requirement
    unverifiable — no finite test suite can prove a system 'always' behaves correctly.
    ISO/IEC/IEEE 29148:2018 §5.2.5(i) 'verifiable' requires each requirement to allow
    a concrete pass/fail decision; temporal universals only permit falsification.
    The correct form is a measurable threshold (uptime %, RTO, RPO) or a scoped assertion.
    Check is scoped to requirement-bearing lines via _requirement_mask(); fenced blocks
    are always excluded.
    """
    p = catalog.get("SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _TEMPORAL_UNIVERSAL_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED: {count} requirement line(s) use a temporal universal "
            "('always', 'never', 'at all times', 'continuously', etc.) that cannot be verified by a "
            "finite test suite; replace with a measurable threshold (e.g. '99.9% uptime per month', "
            "'within 5 seconds', 'zero data loss on graceful shutdown').",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-VAGUE-QUANTIFIER: indefinite quantity words in requirement-bearing lines.
_VAGUE_QUANTIFIER_RE = re.compile(
    r"\b(?:several|many|few|some|various|numerous|a\s+number\s+of|a\s+variety\s+of)\b",
    re.IGNORECASE,
)


def _spec_qvscribe_vague_quantifier(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Indefinite quantity words in SHALL/MUST requirements (SPEC-QVSCRIBE-VAGUE-QUANTIFIER).

    QVscribe Rule QV-112 classifies indefinite quantifiers as Level-1 clarity defects.
    Words like 'several', 'many', 'few', 'some', 'various', 'numerous', 'a number of',
    and 'a variety of' leave the pass/fail criterion undefined — testers cannot determine
    when the requirement is satisfied. ISO/IEC/IEEE 29148:2018 §5.2.5 requires every
    requirement to be verifiable; an indefinite quantity provides no stopping condition.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    """
    p = catalog.get("SPEC-QVSCRIBE-VAGUE-QUANTIFIER")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _VAGUE_QUANTIFIER_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-VAGUE-QUANTIFIER: {count} requirement line(s) use an indefinite "
            "quantity word (several/many/few/some/various/numerous/a number of/a variety of); "
            "replace with a measurable threshold (e.g. 'at least 50', 'a minimum of 200').",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-WEAKENED-EXCEPT: open-ended carve-out on requirement-bearing lines.
_WEAKENED_EXCEPT_RE = re.compile(
    r"\b(?:except(?:\s+(?:when|where|as|in\s+cases?\s+where))?|unless(?:\s+otherwise)?)\b",
    re.IGNORECASE,
)

# SPEC-EARS-TRIGGER-INVERSION: 'shall' placed before EARS trigger keyword (when/while/if/where).
# EARS syntax (Mavin et al. 2009; ISO/IEC/IEEE 29148:2018) requires the trigger to open the
# sentence: "When X, the system shall Y".  Inverted ordering "shall … when" is a structural defect.
_EARS_TRIGGER_INVERSION_RE = re.compile(
    r"\bshall\b[^.;!?\n]{1,80}\b(?:when|while|if|where)\b",
    re.IGNORECASE,
)


def _spec_qvscribe_weakened_except(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement line weakened by open-ended 'except'/'unless' carve-out (SPEC-QVSCRIBE-WEAKENED-EXCEPT).

    QVscribe classifies open-ended qualifiers as a Weakness (Level-2 Completeness defect).
    Phrases like 'except when', 'except where', 'unless', 'unless otherwise' silently expand
    non-compliance scope without bounding the carve-out conditions, making the requirement
    untestable. ISO/IEC/IEEE 29148:2018 §5.2.5(b) requires every requirement to be complete.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-QVSCRIBE-WEAKENED-EXCEPT")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _WEAKENED_EXCEPT_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-WEAKENED-EXCEPT: {count} requirement line(s) contain an open-ended "
            "carve-out (except/except when/except where/unless/unless otherwise) that leaves "
            "the non-compliance boundary undefined and untestable; enumerate all exception "
            "conditions explicitly or remove the carve-out.",
            line=first_line,
        )
    ]


def _spec_ears_trigger_inversion(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement line with EARS trigger keyword placed after 'shall' (SPEC-EARS-TRIGGER-INVERSION).

    EARS (Easy Approach to Requirements Syntax, Mavin et al. 2009; ISO/IEC/IEEE 29148:2018)
    places the trigger keyword (When/While/If/Where) before the normative modal (shall):
    'When X, the system shall Y'.  A common authoring error inverts this to
    'The system shall Y, when X', placing 'shall' before the trigger.  This inversion breaks
    the EARS grammar and hampers traceability tooling that relies on trigger position as a
    structural signal.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-EARS-TRIGGER-INVERSION")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _EARS_TRIGGER_INVERSION_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-EARS-TRIGGER-INVERSION: {count} requirement line(s) place 'shall' before an "
            "EARS trigger keyword (when/while/if/where); move the trigger clause to the start of "
            "the sentence: 'When X, the system shall Y'.",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-BICONDITIONAL: 'if and only if' in normative requirement lines.
# The exact phrase is a formal logic biconditional that creates two unstated test obligations
# (A→B and B→A).  Testers routinely verify only the forward direction; the reverse constraint
# is silently skipped in acceptance test suites. QVscribe Level-1 Clarity defect;
# ISO/IEC/IEEE 29148:2018 §5.2.5(a) 'unambiguous'.
_BICONDITIONAL_RE = re.compile(
    r"\bif\s+and\s+only\s+if\b",
    re.IGNORECASE,
)


def _spec_qvscribe_biconditional(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement line containing biconditional 'if and only if' (SPEC-QVSCRIBE-BICONDITIONAL).

    A biconditional in a requirement creates two implicit test obligations: the forward
    implication (condition → outcome) and the reverse (outcome absent → condition absent).
    Natural-language readers typically verify only the forward direction, leaving the
    reverse obligation untested.  QVscribe classifies this as a Level-1 Clarity defect.
    ISO/IEC/IEEE 29148:2018 §5.2.5(a) requires every requirement to be unambiguous —
    interpretable in exactly one way.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-QVSCRIBE-BICONDITIONAL")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _BICONDITIONAL_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-BICONDITIONAL: {count} requirement line(s) use 'if and only if', "
            "creating two implicit test obligations (forward and reverse implication) that are "
            "not individually labeled; split into two explicit one-directional requirements "
            "with distinct identifiers so each direction can be traced to a test case.",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-ABSOLUTE-TERM: unprovable absolute perfection claim in normative requirement.
# Pattern A — '100 %' + quality-attribute word.
_ABSOLUTE_100PCT_RE = re.compile(
    r"""
    \b100\s*%\s*
    (?:uptime|availability|reliability|accuracy|consistency|coverage|fault[\s-]?free|error[\s-]?free|complian)
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Pattern B — 'zero' + failure-mode word.
_ABSOLUTE_ZERO_RE = re.compile(
    r"""
    \bzero\s+
    (?:downtime|errors?|defects?|failures?|data\s+loss|latency)
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Pattern C — absolute adverb + quality term.
_ABSOLUTE_ADVERB_RE = re.compile(
    r"""
    \b(?:fully|completely|perfectly)\s+
    (?:operational|compliant|functional|consistent|reliable|available|accurate)
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _spec_qvscribe_absolute_term(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Requirement line asserting absolute perfection (100%/zero/fully) (SPEC-QVSCRIBE-ABSOLUTE-TERM).

    Three distinct patterns fire this check:
      A) '100 %' adjacent to a quality-attribute word (uptime, availability, …)
      B) 'zero' adjacent to a failure-mode word (errors, defects, data loss, …)
      C) adverbs 'fully'/'completely'/'perfectly' modifying a system quality term.

    Each pattern imposes a standard no finite test suite can confirm.  QVscribe classifies
    this as a Verifiability defect.  ISO/IEC/IEEE 29148:2018 §5.2.5(i) requires requirements
    to be verifiable by finite means.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-QVSCRIBE-ABSOLUTE-TERM")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if (
            _ABSOLUTE_100PCT_RE.search(line)
            or _ABSOLUTE_ZERO_RE.search(line)
            or _ABSOLUTE_ADVERB_RE.search(line)
        ):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-ABSOLUTE-TERM: {count} requirement line(s) claim absolute perfection "
            "('100%', 'zero failures', 'fully compliant', etc.) — no finite test suite can "
            "confirm such a standard; replace with a bounded, measurable threshold "
            "(e.g. '99.95% uptime per month', 'RPO=0 for committed transactions').",
            line=first_line,
        )
    ]


# SPEC-QVSCRIBE-TIMEBOX-VAGUE: vague timing constraint in normative requirement.
# Matches qualitative timing phrases that give no numeric bound.
_TIMEBOX_VAGUE_RE = re.compile(
    r"""
    \b(?:
        as\s+soon\s+as\s+possible
        | ASAP
        | promptly
        | in\s+a\s+timely\s+manner
        | without\s+(?:undue\s+)?delay
        | at\s+the\s+earliest\s+(?:opportunity|convenience)
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Silence when a numeric time unit appears on the same line (concrete bound present).
_TIMEBOX_NUMERIC_UNIT_RE = re.compile(
    r"""
    \d+\s*
    (?:ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?)\b
    | per\s+(?:second|minute|hour|day)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _spec_qvscribe_timebox_vague(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Vague timing constraint on a requirement-bearing line (SPEC-QVSCRIBE-TIMEBOX-VAGUE).

    QVscribe 'Imprecise Timebox' defect class — fires when a requirement line
    substitutes a qualitative timing phrase ('as soon as possible', 'ASAP',
    'promptly', 'in a timely manner', 'without delay') for a numeric bound.
    ISO/IEC/IEEE 29148:2018 §5.2.5(i) requires every requirement to be verifiable
    by finite means; 'promptly' supplies no stopping condition for acceptance
    testing.

    Distinct from SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED (temporal universals like
    'always'/'never') and SPEC-NFR-NO-THRESHOLD (missing numeric value entirely).
    This fires on any requirement-bearing line using a vague time adverb.

    Scoped to non-fenced requirement-bearing lines via _requirement_mask().
    Silenced when the same line also contains a numeric time unit (the concrete
    bound makes the requirement verifiable despite the qualifier).
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-QVSCRIBE-TIMEBOX-VAGUE")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        if _TIMEBOX_VAGUE_RE.search(line) and not _TIMEBOX_NUMERIC_UNIT_RE.search(line):
            count += 1
            if first_line is None:
                first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-QVSCRIBE-TIMEBOX-VAGUE: {count} requirement line(s) use a vague timing "
            "phrase ('as soon as possible', 'promptly', 'without delay', etc.) with no "
            "numeric bound — no finite acceptance test can determine when the requirement "
            "is satisfied; replace with a measurable threshold "
            "(e.g. 'within 2 seconds', 'within 500 ms at ≤200 req/s').",
            line=first_line,
        )
    ]


# SPEC-MAQA-MISSING-PRIORITY: spec with ≥3 FR- lines but no priority annotation.
_PRIORITY_MARKER_RE = re.compile(
    r"""(?:
        \b(?:must\s+have|should\s+have|could\s+have|won.?t\s+have)\b
        | \bMoSCoW\b
        | \bP[123]\b
        | \bpriority\s*[:=]\s*(?:high|medium|low|critical)\b
        | \bHigh\s+Priority\b
        | \bMedium\s+Priority\b
        | \bLow\s+Priority\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def _spec_maqa_missing_priority(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec with ≥3 FR- requirement lines but no priority annotation (SPEC-MAQA-MISSING-PRIORITY).

    MAQA 'Modifiability' attribute and INVEST 'Negotiable' principle require requirements
    to carry relative priority so teams can triage scope cuts without full re-analysis.
    Guard: ≥3 non-fenced lines with \\bFR-\\d+\\b (formal FR identifiers are in use).
    Check: no priority marker (MoSCoW, P1/P2/P3, High/Medium/Low) anywhere in document.
    """
    p = catalog.get("SPEC-MAQA-MISSING-PRIORITY")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    # Guard: ≥3 non-fenced lines with FR- identifiers.
    fr_count = sum(1 for i, ln in enumerate(lines) if not fenced[i] and _FR_ID_RE.search(ln))
    if fr_count < 3:
        return []
    # Check: any non-fenced line carries a priority marker → silent.
    for i, ln in enumerate(lines):
        if not fenced[i] and _PRIORITY_MARKER_RE.search(ln):
            return []
    return [
        _from_pitfall(
            p,
            art.path,
            "SPEC-MAQA-MISSING-PRIORITY: spec has 3+ FR- requirements but no priority "
            "annotation (MoSCoW, P1/P2/P3, or High/Medium/Low); add priority labels so "
            "teams can triage scope cuts without renegotiating the whole spec.",
            line=1,
        )
    ]


def _spec_missing_out_of_scope(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec with ≥3 normative requirement lines but no Out-of-Scope/Non-Goals heading (SPEC-MISSING-OUT-OF-SCOPE)."""
    p = catalog.get("SPEC-MISSING-OUT-OF-SCOPE")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the spec has enough normative requirement lines to be substantial.
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    normative_count = sum(
        1 for i, ln in enumerate(lines)
        if not fenced[i] and _NORMATIVE_LINE_RE.search(ln)
    )
    if normative_count < 3:
        return []
    # Check whether any heading matches an out-of-scope/non-goals pattern.
    for s in art.sections:
        if _OUT_OF_SCOPE_HEADING_RE.search(s.title):
            return []
    return [
        _from_pitfall(
            p,
            art.path,
            "SPEC-MISSING-OUT-OF-SCOPE: spec has substantial requirements but no Out-of-Scope / Non-Goals section.",
        )
    ]


# SPEC-MISSING-GLOSSARY: spec with ≥3 FR-/NFR- lines but no Glossary/Definitions heading.
_GLOSSARY_HEADING_RE = re.compile(
    r"(?:glossary|definitions?\b|terms?\s+and\s+definitions?|abbreviations?)",
    re.IGNORECASE,
)
_REQ_ID_RE = re.compile(r"\b(?:FR|NFR)-\d+\b", re.IGNORECASE)


def _spec_missing_glossary(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec with ≥3 FR-/NFR- requirement lines but no Glossary/Definitions heading (SPEC-MISSING-GLOSSARY).

    ISO/IEC/IEEE 29148:2018 §5.2.1 mandates a terms-and-definitions clause in every
    requirements specification. Guard: ≥3 non-fenced lines with formal FR-/NFR- identifiers.
    Check: no section heading matches glossary/definitions/terms-and-definitions/abbreviations.
    """
    p = catalog.get("SPEC-MISSING-GLOSSARY")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    # Guard: ≥3 non-fenced lines with FR- or NFR- identifiers.
    req_count = sum(
        1 for i, ln in enumerate(lines)
        if not fenced[i] and _REQ_ID_RE.search(ln)
    )
    if req_count < 3:
        return []
    # Check: any section heading that matches the glossary/definitions pattern → silent.
    for s in art.sections:
        if _GLOSSARY_HEADING_RE.search(s.title):
            return []
    return [
        _from_pitfall(
            p,
            art.path,
            "SPEC-MISSING-GLOSSARY: spec has 3+ FR-/NFR- requirements but no Glossary or "
            "Definitions section; add a shared vocabulary so all readers interpret terms "
            "identically (ISO/IEC/IEEE 29148:2018 §5.2.1).",
            line=1,
        )
    ]


# SPEC-MISSING-MOTIVATION: spec with ≥3 FR-/NFR- lines but no Problem Statement /
# Motivation / Background heading.  Kiro spec template + Tessl spec-first + ISO 29148 §5.2.4.
_MOTIVATION_HEADING_RE = re.compile(
    r"(?:problem\s+statement|motivation|background|rationale|context|purpose"
    r"|^why$|^problem$)",
    re.IGNORECASE,
)


def _spec_missing_motivation(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec with ≥3 FR-/NFR- lines but no Problem Statement / Motivation heading.

    Amazon Kiro mandates a "Problem" section before requirements; Tessl requires the
    spec to explain the *why* before the *what*; ISO/IEC/IEEE 29148:2018 §5.2.4
    mandates a scope/purpose clause.  Guard: ≥3 non-fenced lines with FR-/NFR-
    identifiers.  Check: no section heading matches the motivation-keyword set.
    Distinct from SPEC-MISSING-OUT-OF-SCOPE (non-goals) and SPEC-MISSING-GLOSSARY.
    """
    p = catalog.get("SPEC-MISSING-MOTIVATION")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    # Guard: ≥3 non-fenced lines with FR- or NFR- identifiers.
    req_count = sum(
        1 for i, ln in enumerate(lines)
        if not fenced[i] and _REQ_ID_RE.search(ln)
    )
    if req_count < 3:
        return []
    # Check: any section heading that matches the motivation/problem pattern → silent.
    for s in art.sections:
        if _MOTIVATION_HEADING_RE.search(s.title):
            return []
    return [
        _from_pitfall(
            p,
            art.path,
            "SPEC-MISSING-MOTIVATION: spec has 3+ FR-/NFR- requirements but no "
            "Problem Statement, Motivation, or Background section; add a section "
            "explaining the user need so implementers understand the intent behind "
            "the requirements (Kiro spec template / ISO/IEC/IEEE 29148:2018 §5.2.4).",
            line=1,
        )
    ]


# SPEC-NFR-NO-UNIT: NFR line with a numeric threshold but no measurement unit.
# Complements SPEC-NFR-NO-THRESHOLD (no number at all) — fires when a number IS
# present but has no unit, leaving the threshold unverifiable ("200 what?").
_NFR_UNIT_RE = re.compile(
    # Abbreviated units that often appear glued to digits (e.g. "200ms", "4GB"):
    # match either immediately after a digit (optional space) OR at a word boundary.
    r"(?:(?<=\d)\s*|\b)(?:ms|MB|GB|KB|TB|GiB|MiB|KiB)\b"
    r"|\bmilliseconds?\b"                              # milliseconds written out
    r"|\bsecs?\b|\bsecond(?:s)?\b"                    # seconds
    r"|\bmin(?:ute)?s?\b"                              # minutes
    r"|\bhours?\b"                                     # hours
    r"|\bdays?\b"                                      # days
    r"|\bweeks?\b"                                     # weeks
    r"|\bpercent(?:age)?\b"                            # percent written out
    r"|(?<=\d)\s*%"                                    # digit followed by %
    r"|\bbytes?\b"                                     # bytes
    r"|\brps\b|\brpm\b|\btps\b|\bqps\b"               # rate abbreviations
    r"|\bper\s+second\b|\bper\s+minute\b|\bper\s+hour\b"  # "per X" time rates
    r"|\bvCPU\b|\bcores?\b",                           # compute units
    re.IGNORECASE,
)


def _spec_nfr_no_unit(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """NFR line with a numeric threshold but no measurement unit (SPEC-NFR-NO-UNIT).

    Canon's Scale/Meter/Must rule: every numeric NFR threshold must carry a unit.
    Guard: non-fenced line matches _NFR_RE + _REQUIREMENTish_RE and has a digit
    after stripping requirement IDs (so the digit is a threshold, not an ID).
    Check: no recognized unit token on the same line.
    Distinct from SPEC-NFR-NO-THRESHOLD (no number at all) — this fires when a
    number exists but lacks a unit (Canon, QVscribe Level-1, ISO 29148 §5.2.5(i)).
    """
    p = catalog.get("SPEC-NFR-NO-UNIT")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    for i, (line, in_fence) in enumerate(zip(lines, fenced), start=1):
        if in_fence:
            continue
        # Strip requirement IDs so their digits don't count as a threshold.
        without_ids = re.sub(r"\b(?:FR|NFR|US|T)-?\d+\b", "", line, flags=re.IGNORECASE)
        if (
            _NFR_RE.search(line)
            and _REQUIREMENTish_RE.search(line)
            and _DIGIT_RE.search(without_ids)
            and not _NFR_UNIT_RE.search(line)
        ):
            return [
                _from_pitfall(
                    p, art.path,
                    "SPEC-NFR-NO-UNIT: non-functional requirement states a numeric threshold "
                    "with no measurement unit (Canon Scale/Meter/Must; ISO 29148 §5.2.5(i)). "
                    "Qualify the number — e.g. '200ms', '99.9%', '500 req/s'.",
                    line=i,
                )
            ]
    return []


# SPEC-NFR-NO-LOAD-CONTEXT: performance/latency NFR with a unit'd threshold but no
# stated load or measurement context. Complements SPEC-NFR-NO-THRESHOLD (no number)
# and SPEC-NFR-NO-UNIT (number, no unit): fires when number + unit are both present
# but the measurement context (concurrent users, RPS, peak load, p95, ...) is not.
_LATENCY_NFR_VOCAB_RE = re.compile(
    r"\b(?:latency|throughput|response\s+time|response\s+latency|uptime|availability)\b"
    # Also cover the canonical "shall respond within/in/by <N><time-unit>" idiom.
    r"|\brespond(?:s|ing)?\s+(?:within|in|by|under|after|before)\b",
    re.IGNORECASE,
)
# Time-unit token attached to a digit (200ms, 2 seconds, 30s). Kept narrow so the
# check only fires for latency/throughput thresholds; storage/rate units live under
# other pitfalls (SPEC-NFR-NO-UNIT covers those).
_TIME_THRESHOLD_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|milliseconds?|secs?|seconds?|s\b)"
    r"|\d+(?:\.\d+)?\s*(?:mins?|minutes?|hours?|hrs?|days?)",
    re.IGNORECASE,
)
# Load / measurement context: concurrent users, RPS/TPS/QPS, peak/load, p95/p99,
# "at N users/requests/concurrent". Any hit silences the check.
_LOAD_CONTEXT_RE = re.compile(
    r"\bconcurrent\b|\busers?\b"
    r"|\brequests?\s+per\s+second\b|\brps\b|\btps\b|\bqps\b"
    r"|\bpeak\b|\bload\b"
    r"|\bp9[0-9]\b|\bpercentile\b"
    r"|\bat\s+\d+\s+(?:users?|requests?|concurrent)\b",
    re.IGNORECASE,
)


def _spec_nfr_no_load_context(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Performance NFR states unit'd time threshold but no load/scale context.

    Canon Volere fit-criterion rule: every NFR needs Scale/Meter/Must AND the
    measurement context (at what load level the threshold applies). A "200ms" that
    is unitised (SPEC-NFR-NO-UNIT silent) and present (SPEC-NFR-NO-THRESHOLD silent)
    is still unverifiable if the tester does not know the load conditions.

    Guards (all must fire):
      1. non-fenced line, and
      2. matches performance vocabulary (_LATENCY_NFR_VOCAB_RE), and
      3. matches a normative modal / requirement id (_REQUIREMENTish_RE), and
      4. has a digit+time-unit threshold (_TIME_THRESHOLD_UNIT_RE).
    Silence: any load-context token on the same line (_LOAD_CONTEXT_RE).

    Fire one aggregate finding, anchored at the first offending line.
    """
    p = catalog.get("SPEC-NFR-NO-LOAD-CONTEXT")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    for i, (line, in_fence) in enumerate(zip(lines, fenced), start=1):
        if in_fence:
            continue
        if not _LATENCY_NFR_VOCAB_RE.search(line):
            continue
        if not _REQUIREMENTish_RE.search(line):
            continue
        if not _TIME_THRESHOLD_UNIT_RE.search(line):
            continue
        if _LOAD_CONTEXT_RE.search(line):
            continue
        return [
            _from_pitfall(
                p, art.path,
                "SPEC-NFR-NO-LOAD-CONTEXT: performance requirement states a unit'd threshold "
                "with no load/scale context (Canon Volere fit-criterion; MAQA verifiability). "
                "Qualify the measurement — e.g. 'at 500 concurrent users', 'p95 under peak load'.",
                line=i,
            )
        ]
    return []


# SPEC-NFR-STATISTICAL-AMBIGUITY: latency NFR qualified by "average"/"mean" instead
# of a percentile specifier. The mean masks tail behaviour; p99 can be an order of
# magnitude higher than the mean under realistic load distributions (Google SRE Book,
# Ch.4). ISO 29148 §5.2.5(a) unambiguous + §5.2.5(i) verifiable. Distinct from
# SPEC-NFR-NO-LOAD-CONTEXT (fires even when load IS stated, because the statistical
# qualifier is the problem) and from SPEC-QVSCRIBE-TIMEBOX-VAGUE (fires on vague
# adverbs, not on a present but statistically misleading qualifier).
_LATENCY_QUALITY_RE = re.compile(
    r"\b(?:latency|response[\s-]?time|throughput|query\s+time|processing\s+time)\b",
    re.IGNORECASE,
)
_MEAN_AVERAGE_RE = re.compile(
    r"\b(?:average|mean)\b",
    re.IGNORECASE,
)
_PERCENTILE_SPECIFIER_RE = re.compile(
    r"\b(?:p\d{2,3}|percentile|median|p99|p95|p50)\b",
    re.IGNORECASE,
)
_NORMATIVE_MODAL_RE = re.compile(
    r"\b(?:shall|must)\b",
    re.IGNORECASE,
)


def _spec_nfr_statistical_ambiguity(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Latency NFR uses mean/average instead of a percentile specifier (SPEC-NFR-STATISTICAL-AMBIGUITY).

    ISO 29148 §5.2.5(a) unambiguous + §5.2.5(i) verifiable: a latency threshold
    stated as "average" or "mean" is ambiguous because mean latency masks tail
    behaviour. This check fires even when load IS stated ('at 100 rps, average
    response time shall be < 200ms') because the statistical qualifier itself is the
    problem. QVscribe Imprecise Measurement defect.

    Guards (all must fire on the same non-fenced line):
      1. Latency/performance vocabulary (_LATENCY_QUALITY_RE)
      2. Mean/average qualifier (_MEAN_AVERAGE_RE)
      3. Normative modal: shall/must (_NORMATIVE_MODAL_RE)
    Silence: any percentile specifier on the same line (_PERCENTILE_SPECIFIER_RE).
    Fire one aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-NFR-STATISTICAL-AMBIGUITY")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    for i, (line, in_fence, in_req) in enumerate(zip(lines, fenced, req_mask), start=1):
        if in_fence or not in_req:
            continue
        if not _LATENCY_QUALITY_RE.search(line):
            continue
        if not _MEAN_AVERAGE_RE.search(line):
            continue
        if not _NORMATIVE_MODAL_RE.search(line):
            continue
        if _PERCENTILE_SPECIFIER_RE.search(line):
            continue
        return [
            _from_pitfall(
                p, art.path,
                "SPEC-NFR-STATISTICAL-AMBIGUITY: latency/performance NFR uses 'average' or "
                "'mean' as the statistical qualifier, which masks tail behaviour and is "
                "ambiguous (ISO 29148 §5.2.5(a)/(i); QVscribe Imprecise Measurement). "
                "Replace with a percentile specifier — e.g. 'p95 response time shall be "
                "≤ 200ms at 500 concurrent users'.",
                line=i,
            )
        ]
    return []


# SPEC-MISSING-PII-HANDLING: spec references personal data (PII/GDPR/CCPA) but
# contains no privacy or data-retention statement. Canon Volere Legal/Regulatory
# NFR category + ISO 25010 §4.2.2.5 Confidentiality + GDPR Art. 25 Data
# Protection by Design.
_PII_TRIGGER_RE = re.compile(
    r"\b(?:"
    r"PII"
    r"|personal\s+data"
    r"|personal\s+information"
    r"|email\s+address(?:es)?"
    r"|phone\s+number"
    r"|date\s+of\s+birth"
    r"|social\s+security"
    r"|user\s+profile"
    r"|GDPR"
    r"|CCPA"
    r"|HIPAA"
    r"|sensitive\s+data"
    r"|personally\s+identifiable"
    r")\b",
    re.IGNORECASE,
)
_PII_SILENCE_RE = re.compile(
    r"(?:"
    r"\bdata[\s_-]retention\b"
    r"|\bprivacy\b"
    r"|\banonymis?[ez]\w*"        # anonymize/anonymise/anonymised/anonymized
    r"|\bpseudonymis?[ez]\w*"     # pseudonymize/pseudonymise/pseudonymised/pseudonymized
    r"|\bconsent\b"
    r"|\bdata[\s_-]minimis?[ez]\w*"  # minimise/minimize
    r"|\bdata[\s_-]protection\b"
    r"|\bpurge\w*\b"               # purge/purged/purges
    r"|\bright\s+to\s+(?:erasure|deletion)\b"
    r")",
    re.IGNORECASE,
)


# SPEC-EARS-VAGUE-TRIGGER: EARS event-driven/state-driven requirement with a qualitative
# trigger condition that cannot be objectively tested (EARS §4.4; ISO 29148 §5.2.5(i)).
# Fires when the line has 'shall' and matches a vague trigger in one of three forms:
#   - Adjective-before-noun: "high load", "heavy traffic"
#     (when|while|if) ... (high|heavy|excessive|elevated|abnormal|peak) (load|traffic|demand|usage|volume)
#   - Noun-predicate: "load is high", "traffic is heavy"
#     (when|while|if) ... (load|traffic|demand|usage|volume) ... (high|heavy|excessive|elevated|abnormal|peak)
#   - Spike form: "traffic spikes", "load spikes"
# Silenced when the line also contains a numeric threshold (digit + unit) that grounds the trigger.
_EARS_VAGUE_TRIGGER_PATTERN_RE = re.compile(
    r"""
    (?:
        # Adjective-before-noun form: "high load", "heavy traffic"
        \b(?:when|while|if)\b
        [^.;\n]{0,80}
        \b(?:high|heavy|excessive|elevated|abnormal|peak)\s+
        (?:load|traffic|demand|usage|volume)\b
    |
        # Noun-predicate form: "load is high", "traffic is heavy"
        \b(?:when|while|if)\b
        [^.;\n]{0,80}
        \b(?:load|traffic|demand|usage|volume)\b
        [^.;\n]{0,30}
        \b(?:high|heavy|excessive|elevated|abnormal|peak)\b
    |
        # Spike form: "traffic spikes", "load spikes"
        \b(?:load|traffic|demand|usage)\s+spikes?\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_EARS_VAGUE_TRIGGER_SHALL_RE = re.compile(r"\bshall\b", re.IGNORECASE)
_EARS_VAGUE_TRIGGER_NUMERIC_RE = re.compile(
    r"\b\d+\s*(?:%|rps|qps|req|users?|connections?|ms|MB|GB|tps)\b",
    re.IGNORECASE,
)


def _spec_ears_vague_trigger(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """EARS event-driven requirement with qualitative/unmeasurable trigger condition (SPEC-EARS-VAGUE-TRIGGER).

    EARS (Mavin et al. 2009; ISO/IEC/IEEE 29148:2018 §4.4 and §5.2.5(i)) requires event-driven
    triggers to be objectively observable — the precondition must be deterministically true or
    false at test time. Triggers like 'when the load is high' or 'when traffic spikes' are
    qualitative; acceptance testing cannot determine whether the trigger has fired without a
    numeric threshold (e.g. 'when CPU exceeds 80%', 'when request rate exceeds 1000 rps').
    Distinct from SPEC-EARS-TRIGGER-INVERSION which checks word-order errors ('shall … when');
    this checks the semantic quality of the trigger content when word order is correct.
    Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
    One aggregate finding anchored at the first offending line.
    """
    p = catalog.get("SPEC-EARS-VAGUE-TRIGGER")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    req_mask = _requirement_mask(art, lines)
    first_line: int | None = None
    count = 0
    for i, line in enumerate(lines):
        if fenced[i] or not req_mask[i]:
            continue
        # Must have 'shall' on the line (EARS event-driven form)
        if not _EARS_VAGUE_TRIGGER_SHALL_RE.search(line):
            continue
        # Must match a vague trigger pattern
        if not _EARS_VAGUE_TRIGGER_PATTERN_RE.search(line):
            continue
        # Silenced when a numeric threshold grounds the trigger
        if _EARS_VAGUE_TRIGGER_NUMERIC_RE.search(line):
            continue
        count += 1
        if first_line is None:
            first_line = i + 1  # 1-indexed
    if count == 0:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-EARS-VAGUE-TRIGGER: {count} requirement line(s) use an EARS event-driven form "
            "('when/while/if ... shall') with a qualitative trigger condition (e.g. 'when the load "
            "is high', 'when traffic spikes') that cannot be deterministically tested without a "
            "numeric threshold. Replace with a measurable trigger: 'when CPU exceeds 80%', "
            "'when request rate exceeds 1000 rps' (EARS §4.4; ISO 29148 §5.2.5(i) verifiable).",
            line=first_line,
        )
    ]


def _spec_missing_pii_handling(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Spec references PII/personal data with no privacy or data-retention statement (SPEC-MISSING-PII-HANDLING).

    Canon Volere Legal/Regulatory NFR + ISO 25010 §4.2.2.5 Confidentiality +
    GDPR Article 25 (Data Protection by Design). Fires when:
      1. A non-fenced, non-blockquote line matches PII trigger vocabulary.
      2. No privacy silence token appears anywhere in the document.
    Fires one aggregate finding anchored at the first PII-trigger line.
    """
    p = catalog.get("SPEC-MISSING-PII-HANDLING")
    if p is None or not p.applies_to(art.type):
        return []
    # Fast path: if any silence token appears anywhere, the spec already addresses privacy.
    if _PII_SILENCE_RE.search(art.raw):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    for i, (line, in_fence) in enumerate(zip(lines, fenced), start=1):
        if in_fence:
            continue
        # Skip blockquote lines (> prefix)
        if line.lstrip().startswith(">"):
            continue
        if _PII_TRIGGER_RE.search(line):
            return [
                _from_pitfall(
                    p, art.path,
                    "SPEC-MISSING-PII-HANDLING: spec references personal data or a regulated data "
                    "category (e.g. PII, GDPR, CCPA, email address) but contains no privacy or "
                    "data-retention statement. Add a Privacy/Compliance section covering data "
                    "minimisation, retention schedule, pseudonymisation/anonymisation, and consent "
                    "(Canon Volere Legal NFR; ISO 25010 §4.2.2.5; GDPR Art. 25).",
                    line=i,
                )
            ]
    return []


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
# AC-only requirement ID (XREF-AC-NO-TASK): captures the digit portion for normalisation.
_AC_ID_RE = re.compile(r"\bAC-(\d+)\b", re.IGNORECASE)

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


# Scaling vocabulary: capacity-related terms that imply resource planning is needed (PLAN-MISSING-CAPACITY).
_SCALING_VOCAB_RE = re.compile(
    r"\bscal(?:e|es|ing|able)\b|\breplicas?\b|\binstances?\b|\bnodes?\b"
    r"|\bpods?\b|\bautoscal\w*\b|\bhorizontally\b|\bvertically\b",
    re.IGNORECASE,
)
# Capacity numbers: a digit immediately followed by a resource unit (PLAN-MISSING-CAPACITY).
_CAPACITY_NUMBER_RE = re.compile(
    r"\d+\s*(?:replicas?|instances?|nodes?|pods?|vcpu|GB|MB|RAM|memory|cpu|cores?|workers?)\b",
    re.IGNORECASE,
)


def _plan_missing_capacity(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans that mention scaling but state no concrete capacity numbers (PLAN-MISSING-CAPACITY)."""
    p = catalog.get("PLAN-MISSING-CAPACITY")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the plan uses scaling vocabulary.
    if not _SCALING_VOCAB_RE.search(art.raw):
        return []
    # Silent when any capacity number is present.
    if _CAPACITY_NUMBER_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Deployment plan mentions scaling but states no capacity numbers (replicas, instances, GB RAM, vCPU, etc.).")]


# Third-party integration vocabulary: any "<word> API", webhook, OAuth, third-party, external
# service/endpoint/provider (PLAN-THIRD-PARTY-NO-FALLBACK).
_THIRD_PARTY_RE = re.compile(
    r"\b\w[\w-]*\s+API\b"
    r"|\bwebhook\b"
    r"|\bOAuth\b"
    r"|\bthird[-\s]party\b"
    r"|\bexternal\s+(?:service|endpoint|provider)\b",
    re.IGNORECASE,
)
# Resilience vocabulary: fallback, retry, timeout, circuit breaker, degradation, unavailable,
# offline, error hand* (PLAN-THIRD-PARTY-NO-FALLBACK).
_RESILIENCE_RE = re.compile(
    r"\bfallback\b|\bretr(?:y|ied|ies|ying)\b|\btimeout\b"
    r"|\bcircuit[\s-]breaker\b"
    r"|\bdegrad(?:e|ation)\b"
    r"|\bunavailable\b|\boffline\b"
    r"|\berror\s+hand\w+\b",
    re.IGNORECASE,
)


# Health-check / readiness-probe vocabulary (PLAN-MISSING-HEALTH-CHECK).
_HEALTH_CHECK_RE = re.compile(
    r"\bhealth[\s-]?check[s]?\b"
    r"|\bhealthcheck\b"
    r"|\bliveness[\s-]?probe[s]?\b"
    r"|\breadiness[\s-]?probe[s]?\b"
    r"|\bhealth\s+endpoint\b"
    r"|\bhealth\s+status\b"
    r"|/health\b"
    r"|/ready\b"
    r"|/ping\b",
    re.IGNORECASE,
)


def _plan_missing_health_check(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans with no health-check or readiness-probe mention (PLAN-MISSING-HEALTH-CHECK)."""
    p = catalog.get("PLAN-MISSING-HEALTH-CHECK")
    if p is None or not p.applies_to(art.type):
        return []
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    if _HEALTH_CHECK_RE.search(art.raw):
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Deployment plan mentions deploying/releasing to production but has no health-check or readiness-probe vocabulary.",
    )]


def _plan_third_party_no_fallback(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Integration plans that name an external API/service but lack resilience vocabulary (PLAN-THIRD-PARTY-NO-FALLBACK)."""
    p = catalog.get("PLAN-THIRD-PARTY-NO-FALLBACK")
    if p is None or not p.applies_to(art.type):
        return []
    if not _THIRD_PARTY_RE.search(art.raw):
        return []
    if _RESILIENCE_RE.search(art.raw):
        return []
    return [_from_pitfall(p, art.path, "Integration plan names an external service or API but has no resilience vocabulary (retry, timeout, fallback, circuit breaker, or graceful degradation).")]


# Schema-change vocabulary: signs a plan alters the persistent data model (PLAN-MISSING-MIGRATION guard).
_SCHEMA_CHANGE_RE = re.compile(
    r"\bschema[\s_-]change\b"
    r"|\balter\s+table\b"
    r"|\badd\s+(?:column|field|table)\b"
    r"|\bnew\s+table\b"
    r"|\bdrop\s+(?:column|table)\b"
    r"|\brename\s+(?:column|table)\b"
    r"|\bdatabase[\s_-](?:change|update|migration)\b"
    r"|\bdb[\s_-]migration\b"
    r"|\badd\s+index\b",
    re.IGNORECASE,
)
# Migration-strategy vocabulary: any mention of a data migration plan (PLAN-MISSING-MIGRATION).
_MIGRATION_STRATEGY_RE = re.compile(
    r"\bmigration[\s_-](?:script|plan|strategy|step|guide)\b"
    r"|\bmigrate[\s_-]data\b"
    r"|\bdata[\s_-]migration\b"
    r"|\bbackfill\b"
    r"|\balembic\b"
    r"|\bflyway\b"
    r"|\bliquibase\b"
    r"|\bschema[\s_-]version\b"
    r"|\brollback[\s_-](?:migration|schema)\b"
    r"|\bup\.sql\b"
    r"|\bdown\.sql\b",
    re.IGNORECASE,
)


def _plan_missing_migration(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Plans that mention schema changes but have no data-migration strategy (PLAN-MISSING-MIGRATION)."""
    p = catalog.get("PLAN-MISSING-MIGRATION")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard: only fire when the plan references schema-change operations on non-fenced lines.
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    schema_hit = next(
        (i + 1 for i, line in enumerate(lines) if not fenced[i] and _SCHEMA_CHANGE_RE.search(line)),
        None,
    )
    if schema_hit is None:
        return []
    # Silent when any migration-strategy vocabulary is present anywhere in the document.
    if _MIGRATION_STRATEGY_RE.search(art.raw):
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Plan mentions schema changes (ALTER TABLE / new column / new table) but has no data-migration strategy.",
        line=schema_hit,
    )]


# Runbook / incident-response vocabulary (PLAN-MISSING-RUNBOOK).
_RUNBOOK_RE = re.compile(
    r"\brunbook\b"
    r"|\bplaybook\b"
    r"|\bincident[- ]response\b"
    r"|\bon[- ]?call\b"
    r"|\boncall\b"
    r"|\bescalation\s+(?:proc\w*|path|guide)\b"
    r"|\bops\s+(?:guide|procedure)\b"
    r"|\boperational\s+(?:guide|procedure|playbook)\b",
    re.IGNORECASE,
)


def _plan_missing_runbook(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plans with no runbook or incident-response reference (PLAN-MISSING-RUNBOOK)."""
    p = catalog.get("PLAN-MISSING-RUNBOOK")
    if p is None or not p.applies_to(art.type):
        return []
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    if _RUNBOOK_RE.search(art.raw):
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Deployment plan mentions deploying/releasing to production but has no runbook or incident-response reference.",
    )]


# Async messaging vocabulary: signs a plan describes asynchronous processing (PLAN-ASYNC-NO-DLQ guard).
# Uses the bare form of each word (no plural/inflected variants) to avoid matching negation
# contexts such as "async/queueing is unjustified" in plans that explicitly opt out of messaging.
_ASYNC_MESSAGING_RE = re.compile(
    r"\bqueue\b"
    r"|\bconsumer\b"
    r"|\bproducer\b"
    r"|\bkafka\b"
    r"|\bsqs\b"
    r"|\bsns\b"
    r"|\brabbitmq\b"
    r"|\bpub[/\s-]?sub\b"
    r"|\bevent[- ]?bus\b"
    r"|\bmessage[- ]?broker\b"
    r"|\bcelery\b"
    r"|\bworker[- ]?queue\b"
    r"|\basync(?:hronous)?\s+(?:task|job|message|process)s?\b",
    re.IGNORECASE,
)

# DLQ / poison-message vocabulary: silence the check when any of these are present (PLAN-ASYNC-NO-DLQ).
_DLQ_RE = re.compile(
    r"\bDLQ\b"
    r"|\bdead[- ]letter\b"
    r"|\bpoison[- ](?:message|pill)\b"
    r"|\bunprocessable\b"
    r"|\bmessage[- ]requeue\b"
    r"|\bnack\b"
    r"|\bbreak[- ]queue\b",
    re.IGNORECASE,
)


def _plan_async_no_dlq(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Plans that describe async messaging but have no dead-letter queue strategy (PLAN-ASYNC-NO-DLQ)."""
    p = catalog.get("PLAN-ASYNC-NO-DLQ")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    # Guard: any non-fenced line mentions async messaging.
    async_hit: int | None = None
    for i, line in enumerate(lines):
        if not fenced[i] and _ASYNC_MESSAGING_RE.search(line):
            async_hit = i + 1
            break
    if async_hit is None:
        return []
    # Silence: any line (fenced or not) mentions DLQ / poison-message handling.
    if _DLQ_RE.search(art.raw):
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Plan describes async messaging but has no dead-letter queue or poison-message handling strategy.",
        line=async_hit,
    )]


# Literal IPv4:port pattern on a plan prose line (PLAN-HARDCODED-CONFIG guard A).
_IPV4_PORT_RE = re.compile(
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b",
)

# Credential assignment that is not a placeholder (PLAN-HARDCODED-CONFIG guard B).
# Silenced when value starts with *, < or ${ (masked / templated / env-var reference).
_CREDENTIAL_ASSIGN_RE = re.compile(
    r"\b(?:password|api_key|secret_key|db_pass(?:word)?|private_key|access_key)"
    r"\s*=\s*"
    r"(?!\*+|<|\$\{)"   # negative lookahead: not a placeholder
    r"[^\s]",            # must be followed by a non-space character
    re.IGNORECASE,
)

# Section headings that deliberately contain examples — skip them to avoid false positives.
_EXAMPLE_SECTION_RE = re.compile(r"\b(?:example|sample|reference|demo)\b", re.IGNORECASE)


def _plan_hardcoded_config(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Plan lines with a literal IPv4:port or non-placeholder credential assignment (PLAN-HARDCODED-CONFIG).

    Tessl spec-first / Twelve-Factor App Factor III (Config): plans that hard-code a
    server address or credential are environment-specific and create a secret-leak risk.
    Fenced blocks and 'example'/'sample'/'reference' sections are excluded to avoid
    flagging intentionally illustrative content.
    """
    p = catalog.get("PLAN-HARDCODED-CONFIG")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)

    # Build a mask of lines that belong to intentionally illustrative sections.
    example_section: list[bool] = [False] * len(lines)
    secs = art.sections
    for idx, s in enumerate(secs):
        if _EXAMPLE_SECTION_RE.search(s.title):
            start = s.line - 1
            end = secs[idx + 1].line - 1 if idx + 1 < len(secs) else len(lines)
            for i in range(start, min(end, len(lines))):
                example_section[i] = True

    first_hit: int | None = None
    for i, line in enumerate(lines):
        if fenced[i] or example_section[i]:
            continue
        if _IPV4_PORT_RE.search(line) or _CREDENTIAL_ASSIGN_RE.search(line):
            first_hit = i + 1
            break

    if first_hit is None:
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Plan contains a hard-coded IP address:port or credential assignment; "
        "use environment variables or a secrets manager instead (Twelve-Factor Factor III).",
        line=first_hit,
    )]


# Feature-launch vocabulary: signs a plan introduces a user-visible feature (PLAN-NO-FEATURE-FLAG guard).
# Uses anchored word forms to avoid matching "re-introduce" or "introductory" as launch signals.
_FEATURE_LAUNCH_RE = re.compile(
    r"\bintroduc(?:e|ing|es|ed)\b"
    r"|\bnew\s+feature\b"
    r"|\blaunch(?:es|ing|ed)?\b"
    r"|\broll(?:ing|ed)?\s+out\b"
    r"|\brollout\b"
    r"|\bnew\s+capability\b"
    r"|\bnew\s+endpoint\b"
    r"|\bnew\s+functionality\b"
    r"|\bship(?:ping|ped|s)?\s+(?:the\s+)?(?:new\s+)?feature\b",
    re.IGNORECASE,
)

# Silence tokens: any phased-rollout or feature-flag vocabulary makes the plan safe (PLAN-NO-FEATURE-FLAG).
_FEATURE_FLAG_RE = re.compile(
    r"\bfeature[\s_-]?flag\b"
    r"|\bfeature[\s_-]?toggle\b"
    r"|\bcanary\b"
    r"|\bdark[\s-]launch\w*\b"
    r"|\bblue[\s-]?green\b"
    r"|\bphased[\s-]?rollout\b"
    r"|\bphased[\s-]?deploy\w*\b"
    r"|\bkill[\s_-]switch\b"
    r"|\bpercent(?:age)?\s+of\s+(?:users?|traffic|requests?)\b"
    r"|\btraffic[\s-]?split\b"
    r"|\bflag[\s_-]?(?:gate|guard)\b"
    r"|\blaunch[\s_-]?darkly\b"
    r"|\bgradual[\s-]rollout\b",
    re.IGNORECASE,
)


def _plan_no_feature_flag(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Deployment plan introduces a user-visible feature with no phased-rollout strategy (PLAN-NO-FEATURE-FLAG).

    Amazon Kiro production-readiness and Tessl spec-first require plans that ship a new
    feature to state how the rollout will be staged (feature flags, canary releases,
    dark-launch, blue-green, or percentage-based traffic splits). This is distinct from
    PLAN-MISSING-ROLLBACK (recovery after a bad deploy) and PLAN-MISSING-HEALTH-CHECK
    (detecting a bad deploy via probes). A plan that exposes a new feature to the full user
    base at once forfeits the ability to limit blast radius if the feature malfunctions.
    """
    p = catalog.get("PLAN-NO-FEATURE-FLAG")
    if p is None or not p.applies_to(art.type):
        return []
    # Guard A: deployment vocabulary must be present (reuse existing deploy guard constants).
    has_deploy_section = any(
        _DEPLOY_SECTION_RE.search(s.title) for s in art.sections
    )
    has_deploy_vocab = _DEPLOY_VOCAB_RE.search(art.raw) is not None
    if not (has_deploy_section or has_deploy_vocab):
        return []
    # Guard B: find the first non-fenced line with feature-launch vocabulary.
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    launch_hit: int | None = None
    for i, line in enumerate(lines):
        if not fenced[i] and _FEATURE_LAUNCH_RE.search(line):
            launch_hit = i + 1
            break
    if launch_hit is None:
        return []
    # Silence: any phased-rollout or feature-flag token anywhere in the document.
    if _FEATURE_FLAG_RE.search(art.raw):
        return []
    return [_from_pitfall(
        p,
        art.path,
        "Deployment plan introduces a new feature or capability but has no phased-rollout or feature-flag strategy.",
        line=launch_hit,
    )]


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


def _tasks_untraced_task(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Tasks with T## id but no [US#] tag and no FR-/NFR-/AC-/US- reference (TASKS-UNTRACED-TASK)."""
    p = catalog.get("TASKS-UNTRACED-TASK")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    untraced = [
        (i + 1, ln)
        for i, ln in enumerate(lines)
        if not fenced[i]
        and _TASK_LINE_RE.match(ln)
        and _TASK_ID_RE.search(ln)
        and not _US_TAG_RE.search(ln)
        and not _REQ_ID_RE.search(ln)
    ]
    if not untraced:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"{len(untraced)} task line(s) with no requirement traceability link ([US#] or FR-/NFR-/AC-/US- ref).",
            line=untraced[0][0],
        )
    ]


def _tasks_no_estimate(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Tasks file with T## IDs but no effort estimate annotation (TASKS-NO-ESTIMATE)."""
    p = catalog.get("TASKS-NO-ESTIMATE")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    fenced = _fence_mask(lines)
    task_lines = [
        (i + 1, ln)
        for i, ln in enumerate(lines)
        if not fenced[i] and _TASK_LINE_RE.match(ln) and _TASK_ID_RE.search(ln)
    ]
    if len(task_lines) < 3:
        return []
    if any(_ESTIMATE_RE.search(ln) for ln in lines):
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"{len(task_lines)} task(s) with T## IDs but no effort estimate annotation"
            " (story points, t-shirt size, or hours).",
            line=task_lines[0][0],
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


def _spec_story_compound(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """User story header that bundles 2+ distinct wants via 'and' (INVEST Small violation)."""
    p = catalog.get("SPEC-STORY-COMPOUND")
    if p is None or not p.applies_to(art.type):
        return []
    lines = art.raw.splitlines()
    # Guard: skip specs that contain no Connextra 'I want to' story openers at all.
    # Requiring 'to' avoids false positives on quality-adjective wants
    # like "I want fast and intuitive search" where 'and' joins adjectives.
    has_stories = any(
        _STORY_OPENER_RE.match(line) and _I_WANT_TO_RE.search(line) for line in lines
    )
    if not has_stories:
        return []
    compound: list[int] = []
    for i, line in enumerate(lines):
        if not (_STORY_OPENER_RE.match(line) and _I_WANT_TO_RE.search(line)):
            continue
        # Extract the want-clause: from "I want to" up to "so that" (or end of line).
        want_match = _I_WANT_TO_RE.search(line)
        if want_match is None:
            continue
        want_portion = line[want_match.start():]
        so_that_match = _SO_THAT_RE.search(want_portion)
        if so_that_match:
            want_portion = want_portion[: so_that_match.start()]
        if _COMPOUND_AND_RE.search(want_portion):
            compound.append(i + 1)  # 1-indexed
    if not compound:
        return []
    return [
        _from_pitfall(
            p, art.path,
            f"SPEC-STORY-COMPOUND: user story header bundles multiple wants via 'and': {len(compound)} story(ies).",
            line=compound[0],
        )
    ]


def _spec_ac_vague_outcome(art: Artifact, catalog: dict[str, Pitfall]) -> list[Finding]:
    """Then clause with vague non-observable outcome word (SPEC-AC-VAGUE-OUTCOME).

    Guard: only fires in formal-Gherkin mode — at least one Given AND one When
    line-leader must each start their own line.  Prose ACs and single-line
    'Given … when … then …' styles are not subject to this check.
    """
    p = catalog.get("SPEC-AC-VAGUE-OUTCOME")
    if p is None or not p.applies_to(art.type):
        return []
    raw = art.raw
    # Require formal Gherkin mode: both a Given line-leader and a When line-leader.
    if not (_GHERKIN_GIVEN_RE.search(raw) and _GHERKIN_WHEN_RE.search(raw)):
        return []
    lines = raw.splitlines()
    fenced = _fence_mask(lines)
    hits: list[int] = []
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        if not _GHERKIN_THEN_RE.match(line):
            continue
        if _VAGUE_OUTCOME_RE.search(line):
            hits.append(i + 1)  # 1-indexed
    if not hits:
        return []
    return [
        _from_pitfall(
            p,
            art.path,
            f"SPEC-AC-VAGUE-OUTCOME: {len(hits)} Then clause(s) with vague outcome word "
            f"(correctly/properly/appropriately/as expected/as intended); replace with an observable state.",
            line=hits[0],
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
    out.extend(_spec_story_compound(art, catalog))
    out.extend(_unbounded_scope(art, catalog))
    out.extend(_req_duplicate_id(art, catalog))
    out.extend(_weak_directive(art, catalog))
    out.extend(_pronoun_antecedent(art, catalog))
    out.extend(_future_tense_req(art, catalog))
    out.extend(_req_section_prose_only(art, catalog))
    out.extend(_req_no_id(art, catalog))
    out.extend(_spec_missing_out_of_scope(art, catalog))
    out.extend(_spec_ac_vague_outcome(art, catalog))
    out.extend(_spec_fr_no_story(art, catalog))
    out.extend(_spec_ac_no_fr_link(art, catalog))
    out.extend(_spec_qvscribe_and_or(art, catalog))
    out.extend(_spec_maqa_ac_conditional(art, catalog))
    out.extend(_spec_gherkin_missing_given(art, catalog))
    out.extend(_spec_maqa_missing_priority(art, catalog))
    out.extend(_spec_missing_glossary(art, catalog))
    out.extend(_spec_nfr_no_unit(art, catalog))
    out.extend(_spec_nfr_no_load_context(art, catalog))
    out.extend(_spec_qvscribe_shall_be_able_to(art, catalog))
    out.extend(_spec_qvscribe_temporal_unbounded(art, catalog))
    out.extend(_spec_missing_motivation(art, catalog))
    out.extend(_spec_qvscribe_vague_quantifier(art, catalog))
    out.extend(_spec_qvscribe_weakened_except(art, catalog))
    out.extend(_spec_ears_trigger_inversion(art, catalog))
    out.extend(_spec_qvscribe_biconditional(art, catalog))
    out.extend(_spec_qvscribe_absolute_term(art, catalog))
    out.extend(_spec_qvscribe_timebox_vague(art, catalog))
    out.extend(_spec_nfr_statistical_ambiguity(art, catalog))
    out.extend(_spec_missing_pii_handling(art, catalog))
    out.extend(_spec_ears_vague_trigger(art, catalog))
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
    out.extend(_plan_missing_capacity(art, catalog))
    out.extend(_plan_third_party_no_fallback(art, catalog))
    out.extend(_plan_missing_health_check(art, catalog))
    out.extend(_plan_missing_migration(art, catalog))
    out.extend(_plan_missing_runbook(art, catalog))
    out.extend(_plan_async_no_dlq(art, catalog))
    out.extend(_plan_hardcoded_config(art, catalog))
    out.extend(_plan_no_feature_flag(art, catalog))
    out.extend(_spec_nfr_no_unit(art, catalog))
    out.extend(_spec_nfr_no_load_context(art, catalog))
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

    out.extend(_tasks_untraced_task(art, catalog))
    out.extend(_tasks_no_estimate(art, catalog))
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

        # Dangling req refs: task references an ID not defined in spec.md.
        if spec and (p := catalog.get("XREF-DANGLING-REQ-REF")):
            # Collect IDs defined in spec.md (skip fenced blocks)
            spec_lines = spec.raw.splitlines()
            spec_fenced = _fence_mask(spec_lines)
            spec_ids: set[str] = set()
            for ln, in_fence in zip(spec_lines, spec_fenced):
                if not in_fence:
                    for m in _REQ_ID_RE.finditer(ln):
                        spec_ids.add(m.group(1).upper())
            # Story headings "User Story N" normalise to US-N
            for m in _US_HEADING_RE.finditer(spec.raw):
                spec_ids.add(f"US-{m.group(1)}")
            # Guard: if spec defines no formal IDs, skip
            if spec_ids:
                task_lines = tasks.raw.splitlines()
                task_fenced = _fence_mask(task_lines)
                for ln, in_fence in zip(task_lines, task_fenced):
                    if in_fence or not _TASK_LINE_RE.match(ln):
                        continue
                    refs: set[str] = {m.group(1).upper() for m in _REQ_ID_RE.finditer(ln)}
                    refs |= {f"US-{m.group(1)}" for m in _US_TAG_NUM_RE.finditer(ln)}
                    dangling = sorted(refs - spec_ids)
                    if dangling:
                        examples = ", ".join(dangling[:3])
                        suffix = f" (+{len(dangling) - 3} more)" if len(dangling) > 3 else ""
                        out.append(_from_pitfall(
                            p, tasks.path,
                            f"Task references undefined requirement ID(s): {examples}{suffix}.",
                        ))

        # AC-NNN forward traceability: AC defined in spec but not referenced by any task.
        if spec and (p := catalog.get("XREF-AC-NO-TASK")):
            spec_lines = spec.raw.splitlines()
            spec_fenced = _fence_mask(spec_lines)
            spec_ac_ids: dict[str, int] = {}  # id → first line number (1-based)
            for lineno, (ln, in_fence) in enumerate(zip(spec_lines, spec_fenced), start=1):
                if not in_fence and not ln.lstrip().startswith("#"):
                    for m in _AC_ID_RE.finditer(ln):
                        ac_key = f"AC-{m.group(1)}"
                        if ac_key not in spec_ac_ids:
                            spec_ac_ids[ac_key] = lineno
            if spec_ac_ids:
                task_lines = tasks.raw.splitlines()
                task_fenced = _fence_mask(task_lines)
                referenced: set[str] = set()
                for ln, in_fence in zip(task_lines, task_fenced):
                    if not in_fence and _TASK_LINE_RE.match(ln):
                        for m in _AC_ID_RE.finditer(ln):
                            referenced.add(f"AC-{m.group(1)}")
                orphaned = sorted(
                    (ac for ac in spec_ac_ids if ac not in referenced),
                    key=lambda x: int(x.split("-")[1]),
                )
                if orphaned:
                    examples = ", ".join(orphaned[:3])
                    suffix = f" (+{len(orphaned) - 3} more)" if len(orphaned) > 3 else ""
                    out.append(_from_pitfall(
                        p, spec.path,
                        f"Acceptance-criteria ID(s) in spec.md have no task reference: {examples}{suffix}.",
                    ))

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

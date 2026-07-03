"""Optional key-based judge backend for headless/CI runs.

This is the only place a direct LLM API is used, and it's opt-in (`--api`). Default
reviews use the agent integration and need no key. Uses the official Anthropic SDK with
structured outputs so the judge returns schema-valid JSON.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from ..engine.judge import JUDGE_SCHEMA, artifact_label, build_prompt
from ..engine.judge import JudgeUnavailable
from ..model import Artifact

DEFAULT_MODEL = "claude-opus-4-8"

# Built-in input budget: max characters of artifact content sent in one --api call.
#
# Why 150k chars: markdown/prose runs ~3.5-4 chars per token, so 150k chars is
# roughly 40k input tokens — comfortably inside the model context window once the
# judge instructions and pitfall catalog are added, small enough that key artifacts
# aren't buried mid-prompt in a mega-corpus, and it caps the input cost of a single
# review at roughly $0.20 with the default claude-opus-4-8 ($5 per 1M input tokens).
# Typical repos (a handful of features) are far below this and pass through intact.
# Deliberately not configurable: cost control should not require a flag to be safe.
INPUT_BUDGET_CHARS = 150_000

# Rough chars→tokens divisor for the stderr cost diagnostic (markdown ≈ 4 chars/token).
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Truncation:
    """Record of one artifact shortened to fit the input budget."""

    label: str  # path relative to the repo root
    shown_lines: int
    total_lines: int
    original_chars: int


def _per_artifact_cap(sizes: list[int], budget: int) -> int:
    """Water-filling cap: the largest artifacts absorb the entire cut.

    Walk sizes ascending, granting each artifact an equal share of the remaining
    budget; artifacts under their share fit whole, so only the biggest ones end up
    capped. This is "truncate from the largest down": small artifacts are never
    touched, and every capped artifact keeps the same (maximal) number of chars.
    """
    used = 0
    ordered = sorted(sizes)
    for i, size in enumerate(ordered):
        share = (budget - used) // (len(ordered) - i)
        if size <= share:
            used += size
        else:
            return share
    return budget  # everything fits; callers check the total first


def truncate_to_budget(
    artifacts: list[Artifact], root: Path | None = None, budget: int = INPUT_BUDGET_CHARS
) -> tuple[list[Artifact], list[Truncation]]:
    """Fit total artifact content under ``budget`` chars, largest artifacts first.

    Returns ``(prompt_artifacts, truncations)``. Untouched artifacts are returned
    as-is; truncated ones are copies whose ``raw`` keeps the first whole lines that
    fit and ends with an explicit ``[truncated: ...]`` marker so the judge (and
    anyone reading the prompt) can see coverage narrowed. Never silent.
    """
    if sum(len(a.raw) for a in artifacts) <= budget:
        return list(artifacts), []
    cap = _per_artifact_cap([len(a.raw) for a in artifacts], budget)
    out: list[Artifact] = []
    truncations: list[Truncation] = []
    for a in artifacts:
        if len(a.raw) <= cap:
            out.append(a)
            continue
        lines = a.raw.splitlines(keepends=True)
        kept: list[str] = []
        size = 0
        for line in lines:
            if size + len(line) > cap:
                break
            kept.append(line)
            size += len(line)
        if not kept and lines:  # single line longer than the cap: keep a slice of it
            kept = [lines[0][:cap]]
        marker = f"\n[truncated: showing first {len(kept)} of {len(lines)} lines]\n"
        out.append(replace(a, raw="".join(kept) + marker))
        truncations.append(
            Truncation(
                label=artifact_label(a.path, root),
                shown_lines=len(kept),
                total_lines=len(lines),
                original_chars=len(a.raw),
            )
        )
    truncations.sort(key=lambda t: -t.original_chars)  # report largest first
    return out, truncations


class ApiJudge:
    """Judge via a direct Anthropic API call (requires `sddgrade[api]` + a key)."""

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.model = os.environ.get("SDDREVIEW_MODEL", DEFAULT_MODEL)
        # Coverage caveats produced by this run (e.g. budget truncation). The engine
        # copies these onto the ReviewResult so reports reflect partial coverage.
        self.notes: list[str] = []

    def judge(self, artifacts, root: Path) -> list[dict]:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise JudgeUnavailable("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
        except ImportError as exc:
            raise JudgeUnavailable(
                "anthropic SDK not installed — `pip install 'sddgrade[api]'`"
            ) from exc

        client = anthropic.Anthropic()
        prompt_artifacts, truncations = truncate_to_budget(artifacts, root)
        total = sum(len(a.raw) for a in artifacts)
        sent = sum(len(a.raw) for a in prompt_artifacts)
        # Cost visibility before the call: CI logs show what a run sends (and costs).
        print(
            f"sddgrade: --api input: {sent:,} chars of artifact content across "
            f"{len(artifacts)} artifact(s) (~{sent // _CHARS_PER_TOKEN:,} tokens, "
            f"model {self.model})",
            file=sys.stderr,
        )
        if truncations:
            detail = ", ".join(
                f"{t.label} ({t.shown_lines}/{t.total_lines} lines)" for t in truncations
            )
            note = (
                f"Judge coverage is partial: the corpus is {total:,} chars of artifact "
                f"content, over the built-in {INPUT_BUDGET_CHARS:,}-char --api input "
                f"budget, so {len(truncations)} artifact(s) were truncated (largest "
                f"first): {detail}. For full coverage, review one feature at a time: "
                "`sddgrade review specs/<feature>`."
            )
            self.notes.append(note)
            print(f"sddgrade: notice: {note}", file=sys.stderr)
        prompt = build_prompt(prompt_artifacts, root)
        try:
            # Stream to avoid HTTP timeouts on large specs; structured output guarantees
            # schema-valid JSON in the first text block.
            with client.messages.stream(
                model=self.model,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                message = stream.get_final_message()
        except Exception as exc:  # network/auth/etc. — surface class + detail; the
            # runner decides whether to degrade (agent default) or fail (--api).
            status = getattr(exc, "status_code", None)
            detail = f"{type(exc).__name__}" + (f", HTTP {status}" if status else "")
            raise JudgeUnavailable(f"API call failed ({detail}): {exc}") from exc

        text = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise JudgeUnavailable(f"judge returned non-JSON: {exc}") from exc
        return data.get("findings", [])

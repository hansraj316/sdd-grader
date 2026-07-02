"""Optional key-based judge backend for headless/CI runs.

This is the only place a direct LLM API is used, and it's opt-in (`--api`). Default
reviews use the agent integration and need no key. Uses the official Anthropic SDK with
structured outputs so the judge returns schema-valid JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..engine.judge import JUDGE_SCHEMA, build_prompt
from ..engine.judge import JudgeUnavailable

DEFAULT_MODEL = "claude-opus-4-8"


class ApiJudge:
    """Judge via a direct Anthropic API call (requires `sddgrade[api]` + a key)."""

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.model = os.environ.get("SDDREVIEW_MODEL", DEFAULT_MODEL)

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
        prompt = build_prompt(artifacts)
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

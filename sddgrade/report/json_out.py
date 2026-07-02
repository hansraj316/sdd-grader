"""Machine-readable JSON report for CI and tooling."""

from __future__ import annotations

import json

from ..model import ReviewResult


def render(result: ReviewResult) -> str:
    return json.dumps(result.to_dict(), indent=2)

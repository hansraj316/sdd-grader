# Contributing to sddgrade

Thanks for helping. Bug reports, new pitfall checks, corpus cases, and docs fixes
are all welcome.

## Set up

```bash
git clone https://github.com/hansraj316/sdd-grader.git
cd sdd-grader
uv venv --python 3.11
uv pip install -e ".[dev]"
uv run pytest -q                      # full suite, ~15s
uv run python scripts/benchmark.py    # corpus regression gate (CI runs this too)
```

Try your change on a real spec:

```bash
uv run sddgrade review --rules tests/fixtures/speckit_bad
```

## What a good PR looks like

- **One change per PR.** A new check, a bug fix, or a doc change, not all three.
- **Tests pass and the benchmark gate passes.** CI runs exactly the two commands above.
- **Every finding carries a fix.** Each `Finding` needs a concrete `suggestion`.
  "Improve this" is not a fix; "Replace 'fast' with a p95 latency target" is.
- **No false positives on good specs.** Run new lint checks against
  `corpus/cases/excellent` and `tests/fixtures/speckit_good`. They must stay clean.

## Adding a lint check (the most common contribution)

1. Add a `[[pitfall]]` entry to `sddgrade/rubric/pitfalls.toml`: `id`, `name`,
   `dimension`, `artifacts`, `severity`, `method`, and the `why`, `detect`, and
   `fix` text. Cite a source in `why` where one exists (Spec-Kit docs, ISO 29148,
   EARS, and so on).
2. Implement the detector in `sddgrade/engine/lint.py`, following the existing
   `_spec_*` / `_plan_*` functions.
3. Add `tests/test_<your_check>.py` with at least one positive case and one
   negative look-alike case.
4. If the check changes a corpus case's expected findings, update that case's
   `expected.json` and explain why in the PR.

## Corpus cases

`corpus/cases/<name>/` holds real or realistic artifacts plus an `expected.json`
of the findings they must and must not produce. A new case that shows a defect
we miss (or a false positive we emit) is one of the most valuable contributions
you can make, even without a fix.

## Judge backends

The semantic judges (`agent`, `--api`, `--jev`) are tested with mocks. Never put
real API keys in tests, fixtures, or commits. CI must run without network access
to model providers.

## Commit style

Use short, imperative subject lines with a type prefix, matching the existing log:
`lint: ...`, `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By taking part,
you agree to uphold it.

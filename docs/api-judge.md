# The `--api` judge backend (optional)

The default judge runs in your existing agent (no key). For **headless CI** where no
interactive agent exists, `--api` calls a provider directly.

```bash
pip install 'sddgrade[api]'        # installs the Anthropic SDK
export ANTHROPIC_API_KEY=sk-...     # required; keep it a CI secret
sddgrade review --api --fail-under 70
```

- **Optional and opt-in.** Without `--api`, no key is needed and no network call is made.
- **Default model:** `claude-opus-4-8`. Override with `SDDREVIEW_MODEL` (e.g.
  `SDDREVIEW_MODEL=claude-sonnet-4-6`).
- **Structured output:** the call uses a JSON-schema output config so the judge returns
  schema-valid findings.
- **Cost control (built-in, no flags):** before calling the API, sddgrade prints the
  input size to stderr so CI logs show what a run costs, e.g.
  `sddgrade: --api input: 42,113 chars of artifact content across 6 artifact(s) (~10,528 tokens, model claude-opus-4-8)`.
  Markdown runs roughly 4 characters per token, and the default `claude-opus-4-8`
  bills about **$5 per million input tokens** (≈ $1.25 per million characters), plus
  up to 16k output tokens at $25/M — so a typical few-feature repo costs a few cents
  per review, and a full-budget run costs roughly $0.20 of input.
- **Input budget:** at most **150,000 characters** of artifact content (~40k tokens)
  are sent per call. If the corpus exceeds that, the largest artifacts are truncated
  first (each keeps its first lines and is explicitly marked
  `[truncated: showing first N of M lines]` in the prompt), a notice is printed to
  stderr listing exactly what was cut, and the report/JSON carries the same note
  (`notes` field + coverage note) so a partially-judged score is never silent. For
  full coverage of a large corpus, review one feature at a time:
  `sddgrade review specs/<feature>`.
- **Failure handling:** `--api` implies `--require-judge`. A missing key, missing SDK,
  API error (the message includes the exception class and HTTP status), or malformed
  response makes the review **fail with exit 3** and a message saying what broke and how
  to fix it — it never silently emits a lint-only score in place of the requested
  lint+semantic review, so a CI gate can't stay green on an expired or misnamed secret.
  Only the default agent backend degrades to lint-only (and says so in the coverage
  banner).

## Run-to-run variance and `--fail-under`

The judge is an LLM: on **identical artifacts**, different runs legitimately return
slightly different finding sets (count and severities), so the judged half of the score
has run-to-run variance while the lint half stays fixed. A hard `--fail-under` gate on a
repo whose score hovers near the threshold will therefore intermittently pass and fail
on the same commit. Two deterministic mitigations are built in (no retries, no flags):

- **Capped judge weight** — judge findings are scored at half the lint penalty and a
  single judge finding never subtracts more than 12 points (see
  `engine/scoring.py`), so one borderline judge call can't swing a pass/fail by a
  full lint-severity step, and a judge "critical" can't sink a score by 25 points on
  its own. Deterministic lint findings keep full weight.
- **Noise-band warning** — when the overall score lands within 5 points of the
  configured `fail_under` and the coverage is `lint+semantic`, the review prints a
  stderr warning that the score is within the judge's noise band of the gate, so a CI
  flake is recognizable as judge noise rather than a code regression.

If your repo triggers the warning, either move the threshold away from where scores
hover or gate CI on `--rules` (fully deterministic) and treat the judged score as
advisory.

## Prompt injection

The artifact author being graded controls the text sent to the judge, so the prompt
wraps every artifact body in explicit untrusted-content markers with an instruction
that the content is data under review, never instructions. This is a mitigation, not a
guarantee — see the "What the judge can and can't prove" section of the README for the
honest residual risk (the deterministic lint layer, including the
`SPEC-PROMPT-INJECTION-SUSPECT` check, is the only tamper-proof part).

The backend is covered by mocked unit tests (`tests/test_api_judge.py`) so CI validates
the call shape, error paths, and model configuration without a live key.

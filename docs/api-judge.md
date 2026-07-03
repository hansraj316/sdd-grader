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

The backend is covered by mocked unit tests (`tests/test_api_judge.py`) so CI validates
the call shape, error paths, and model configuration without a live key.

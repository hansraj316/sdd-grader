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
- **Failure handling:** `--api` implies `--require-judge`. A missing key, missing SDK,
  API error (the message includes the exception class and HTTP status), or malformed
  response makes the review **fail with exit 3** and a message saying what broke and how
  to fix it — it never silently emits a lint-only score in place of the requested
  lint+semantic review, so a CI gate can't stay green on an expired or misnamed secret.
  Only the default agent backend degrades to lint-only (and says so in the coverage
  banner).

The backend is covered by mocked unit tests (`tests/test_api_judge.py`) so CI validates
the call shape, error paths, and model configuration without a live key.

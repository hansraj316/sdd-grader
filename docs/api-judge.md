# The `--api` judge backend (optional)

The default judge runs in your existing agent (no key). For **headless CI** where no
interactive agent exists, `--api` calls a provider directly.

```bash
pip install 'sddreview[api]'        # installs the Anthropic SDK
export ANTHROPIC_API_KEY=sk-...     # required; keep it a CI secret
sddreview review --api --fail-under 70
```

- **Optional and opt-in.** Without `--api`, no key is needed and no network call is made.
- **Default model:** `claude-opus-4-8`. Override with `SDDREVIEW_MODEL` (e.g.
  `SDDREVIEW_MODEL=claude-sonnet-4-6`).
- **Structured output:** the call uses a JSON-schema output config so the judge returns
  schema-valid findings; malformed output degrades cleanly (the review falls back to
  lint-only rather than crashing, unless you pass `--require-judge`).
- **Failure handling:** a missing key, missing SDK, or API error raises an internal
  `JudgeUnavailable`; the review degrades to lint-only and says so in the coverage banner.

The backend is covered by mocked unit tests (`tests/test_api_judge.py`) so CI validates
the call shape, error paths, and model configuration without a live key.

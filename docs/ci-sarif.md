# Surfacing findings in GitHub (SARIF)

`sddreview review --sarif <path>` writes a SARIF 2.1.0 file. Each finding becomes a
SARIF result with a stable rule id (the pitfall id where available), so findings show up
in the **Security → Code scanning** tab and as inline PR annotations.

## Sample GitHub Actions workflow

```yaml
name: Spec review
on: pull_request

jobs:
  sddreview:
    runs-on: ubuntu-latest
    permissions:
      security-events: write   # required to upload SARIF
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv tool install sddreview --from git+https://github.com/hansraj316/sddreview.git
      # Rules-only: deterministic, no API key, good for CI gating.
      - run: sddreview review --rules --sarif sddreview.sarif --fail-under 70
        continue-on-error: true   # still upload SARIF even when the gate fails
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sddreview.sarif
```

Drop `continue-on-error` if you want the job (not just the annotations) to fail the PR
when the score is below `--fail-under`. For a semantic review in CI, use `--api` with an
API key configured as a secret instead of `--rules`.

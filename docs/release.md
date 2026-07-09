# Releasing sddgrade

Releases are tag-driven: pushing a `v*` tag runs `.github/workflows/release.yml`,
which tests, builds, creates a GitHub Release with the wheel/sdist attached, and
(once configured) publishes to PyPI.

## Versioning

The version lives in **one place**: `[project].version` in `pyproject.toml`.
`sddgrade/__init__.py` reads it back via `importlib.metadata`, so
`sddgrade --version` and `sddgrade self check` always report the installed
distribution's version — never a second hardcoded string.

Bump the minor for feature batches, the patch for fix-only batches
(the project loosely follows semver pre-1.0: minor = features/behavior changes,
patch = fixes).

## Cutting a release

1. Bump `version` in `pyproject.toml` on `main` (via a normal PR).
2. Tag and push — the tag **must** match the version (the workflow enforces this):

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. The `Release` workflow then:
   - runs the test suite (a failing suite blocks everything downstream);
   - verifies the tag matches `pyproject.toml`, builds the wheel + sdist with
     `uv build`;
   - creates a GitHub Release named after the tag, with auto-generated notes and
     `dist/*` attached;
   - runs the **`publish-pypi`** job (see below).

Users can then pin an exact version:

```bash
uv tool install sddgrade --from git+https://github.com/hansraj316/sdd-grader.git@v0.2.0
# or, once PyPI publishing is live:
uv tool install sddgrade==0.2.0
```

## PyPI Trusted Publisher setup (one-time, repo owner)

The `publish-pypi` job uses [trusted publishing](https://docs.pypi.org/trusted-publishers/)
(`pypa/gh-action-pypi-publish` with an OIDC `id-token`), so **no PyPI API token is
stored in the repo**. It only works after the owner registers this workflow as a
Trusted Publisher on pypi.org:

1. Log in to <https://pypi.org> with the account that will own the `sddgrade` project.
2. Since `sddgrade` has never been published, use the **pending publisher** flow:
   go to <https://pypi.org/manage/account/publishing/> and, under
   "Add a new pending publisher" → **GitHub**, enter exactly:
   - **PyPI project name:** `sddgrade`
   - **Owner:** `hansraj316`
   - **Repository name:** `sdd-grader`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi`
3. (Optional but recommended) In the GitHub repo, create the `pypi` environment
   under *Settings → Environments* and restrict it to `v*` tags. If you skip
   this, GitHub creates the environment automatically the first time the job runs.
4. Push the next `v*` tag. The first successful `publish-pypi` run creates the
   `sddgrade` project on PyPI and converts the pending publisher into a regular
   Trusted Publisher. (For subsequent management:
   *pypi.org → project → Manage → Publishing*.)

### Why the PyPI job is allowed to fail

`publish-pypi` is a **separate job with `continue-on-error: true`**. Until the
Trusted Publisher above exists, PyPI rejects the OIDC exchange and the job fails —
but the tests, the build, and the GitHub Release (the parts that don't need
external setup) still complete, so a tag always yields an installable release.
Once the publisher is configured, the same workflow starts publishing with no
changes. The trade-off: a real publishing regression also won't turn the
workflow red, so check the `publish-pypi` job status on release runs; consider
removing `continue-on-error` after the first successful publish.

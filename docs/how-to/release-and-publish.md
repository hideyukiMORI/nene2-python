# How to release and publish to PyPI

This guide describes the verified release flow: **CHANGELOG → version bump → tag →
automated publish (TestPyPI → PyPI → GitHub Release)**. The automation lives in
[`.github/workflows/publish.yml`](../../.github/workflows/publish.yml) and triggers
on `v*` tags via **PyPI Trusted Publishing** (OIDC — no long-lived tokens).

## One-time setup (maintainer, cannot be automated)

The publish workflow uses Trusted Publishing and GitHub Environments. These must be
configured once on the PyPI side and in the repo settings:

1. **PyPI / TestPyPI — Trusted Publisher** for `nene2-python`:
   - Owner: `hideyukiMORI`, Repository: `nene2-python`
   - Workflow: `publish.yml`
   - Environment: `pypi` (on pypi.org) and `testpypi` (on test.pypi.org)
   - Register at https://pypi.org/manage/account/publishing/ and the TestPyPI equivalent.
2. **GitHub repo → Settings → Environments**: create `testpypi` and `pypi`
   (optionally add required reviewers on `pypi` for a manual approval gate).

Until step 1 is done, `pip install nene2-python` is unavailable — the package has
never been published (the FT sandboxes install it from the local wheel / `git+`).

## Release procedure (per release)

1. **Update `CHANGELOG.md`** — add a `## [X.Y.Z] — YYYY-MM-DD` section. The
   GitHub Release step extracts notes by matching this header, so the section must
   exist or the release notes will be empty.
2. **Bump the version** in `pyproject.toml` and refresh the lock:
   ```bash
   uv lock
   ```
3. **Open a PR**, pass CI (the `package-build` job validates the distribution),
   and merge to `main`.
4. **Tag and push** the release:
   ```bash
   git checkout main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. `publish.yml` runs automatically: `uv build` → publish to **TestPyPI** →
   publish to **PyPI** → create a **GitHub Release** with notes from CHANGELOG and
   the dist artifacts attached.

## Local verification (before tagging)

The CI `package-build` job runs this on every PR, but you can reproduce it:

```bash
uv build                        # sdist + wheel into dist/
uvx twine check dist/*          # PyPI metadata validity
uv venv /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/*.whl
/tmp/verify/bin/python -c "import nene2; print('OK')"   # clean import; example/tests must NOT be importable
```

As of v1.8.163 this passes: `twine check` reports `PASSED`, the wheel imports
cleanly in a fresh venv, and only `src/nene2` is shipped (`example`/`tests` are
excluded by `[tool.hatch.build.targets.wheel] packages = ["src/nene2"]`).

## Notes

- **Versioning**: `pyproject.toml` `version` is the source of truth and is bumped
  per FT / feature / fix PR. Git `v*` tags are created selectively at release time
  (the publish workflow only fires on tags), so `pyproject` runs ahead of tags.
- **CHANGELOG granularity**: per-version one-liners live in the
  [`docs/todo/current.md`](../todo/current.md) milestone table; `CHANGELOG.md`
  records release-grained aggregated entries.
- This procedure corresponds to the **FT7-class "publish flow" trial** (#541): the
  build is verified and the automation is in place; the only remaining step is the
  maintainer's one-time Trusted Publishing setup followed by the first `v*` tag.

# Development Scripts

## Purpose

`scripts/` exposes the canonical wrappers for repository tooling so every agent or human
invocation behaves consistently: terse summaries on success, temp-log disclosures on failure,
and predictable exit codes. Use these scripts instead of calling tooling directly so we preserve
the progressive-disclosure and logging conventions defined by GenTool.

## Scripts

### `scripts/run-tests`

- **Description**: Runs the full matrix of automated tests — unit, property, integration (if present),
  and Cypress e2e — while admitting selective skips for expensive suites. Each suite is timed,
  stdout/stderr is captured to a temp log, and `[OK]`/`[FAIL]` summaries are emitted in a consistent format.
- **Underlying tools**:
  - `python -m pytest tests/unit`
  - `python -m pytest tests/property`
  - `python -m pytest tests/integration` (only if `tests/integration` exists)
- `npx cypress run --e2e --browser chrome`
- **Options**:
  - `--skip-property`: omit the Hypothesis-heavy property suite
  - `--skip-integration`: omit the integration PyTest suite (or skip if no suite directory)
  - `--skip-e2e`: omit the Cypress end-to-end run
  - `--filter SUITE[:PATTERN]`: target a single suite; e.g. `--filter unit:budgeting` or `--filter e2e:01-payday-assignment`
  - `-h`/`--help`: show the manpage-style header
- **Behavior**:
  - Shrinks verbose logs on success by deleting per-suite temp files.
  - Keeps temp logs when a suite fails and points to them as `(log: /tmp/dojo-run-tests-...)`.
  - Prints final `[OK] scripts/run-tests (all requested suites passed)` or `[FAIL] scripts/run-tests (one or more suites failed)` line.

#### Example usage

```
scripts/run-tests
scripts/run-tests --skip-e2e
scripts/run-tests --skip-integration
scripts/run-tests --skip-property --skip-integration
```

### `scripts/run-migrations-check`

- **Description**: Applies all migrations against a temporary DuckDB file and logs the plan (optional) so migration safety can be verified in CI or locally without touching real data. Cleans up the temp file on success and prints its path on failure.
- **Underlying tools**: `python -m dojo.core.migrate --database <temp>.duckdb [--log-plan]`
- **Options**:
  - `--log-plan`: print the ordered migrations and statements before execution.
  - `-h`/`--help`: show usage.
- **Behavior**:
  - Creates a temp DuckDB under `${TMPDIR:-/tmp}`.
  - Runs the migration runner; removes the file on success.
  - Emits `[OK] scripts/run-migrations-check (migrations applied cleanly)` on success or `[FAIL] ... (see <path>)` on failure.

### `scripts/extract-release-notes`

- **Description**: Extracts the release notes for a specific version tag (e.g. `v0.1.1`) from `CHANGELOG.md`. Designed for use in CI/CD pipelines to populate GitHub Release bodies.
- **Options**:
  - `version`: The version tag to extract.
  - `changelog_path` (optional): Path to the changelog file (defaults to `CHANGELOG.md`).
  - `-h`/`--help`: show usage.
- **Behavior**:
  - Prints the extracted notes to stdout.
  - Exits with error if the section is not found.

#### Example usage

```
scripts/extract-release-notes v0.1.1
scripts/extract-release-notes v0.1.1 custom_changelog.md
```

### `scripts/release`

- **Description**: Preflight guardrails (fetch tags, ensure on `master`, clean tree), bumps semantic version (`--bump patch|minor|major`), rolls `CHANGELOG.md` by moving the `[Unreleased]` section into a dated `vX.Y.Z` entry, optionally generates release notes via an LLM (`codex` by default, `gemini` as an alternative), updates `pyproject.toml`, creates an annotated git tag, and pushes branch + tag. Dry-run mode computes everything without touching the working tree.
- **Options**:
  - `--bump {patch|minor|major}` (default: patch)
  - `--dry-run` to preview changes only
  - `--notes-file PATH` to save the release notes extracted from the changelog
  - `--notes-llm {codex|gemini|none}` to pick the LLM provider (default: `codex`; `none` skips LLM generation and uses the changelog or commit fallback directly)
- **Behavior**:
  - Aborts if the current branch is not `master` or the git tree is dirty.
  - Fetches tags before measuring upstream so the script knows the last published release.
  - Emits logfmt lines for each step (preflight, version, changelog, done) and records whether release notes came from the LLM, `CHANGELOG.md`, or the commit history.
  - Uses the LLM output when available, otherwise falls back to `[Unreleased]` or the commit summary, and leaves `[Unreleased]` populated with the template sections after rolling.

#### Example usage

```
scripts/release --dry-run --bump patch
scripts/release --bump minor
scripts/release --bump patch --notes-file /tmp/dojo-release-notes.md
```

## Notes for Agents

1. When asked to run tests, call `run-tests` (with optional skip flags) instead of invoking `pytest`, `npx cypress`, or other tooling directly.
2. Direnv loads the Nix dev shell automatically in this repo; assume scripts in `scripts/` are already on `PATH` (no need to prefix with `nix develop` or `./scripts/`).
3. Treat `[FAIL]` lines as the authoritative failure signal: read the referenced temp log (`tail`, `cat`, `rg`, etc.) instead of re-running the underlying command until a fix is in place.
4. Document any new or changed scripts in this README and follow the manpage/summary/logging conventions before updating `AGENTS.md`.

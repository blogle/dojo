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

## Notes for Agents

1. When asked to run tests, call `scripts/run-tests` (with optional skip flags) instead of invoking `pytest`, `npx cypress`, or other tooling directly.
2. Treat `[FAIL]` lines as the authoritative failure signal: read the referenced temp log (`tail`, `cat`, `rg`, etc.) instead of re-running the underlying command until a fix is in place.
3. Document any new or changed scripts in this README and follow the manpage/summary/logging conventions before updating `AGENTS.md`.

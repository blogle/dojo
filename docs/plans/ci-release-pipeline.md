# Nix-First CI and Release Pipeline for Dojo

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: .agent/PLANS.md — maintain this document in accordance with that guidance.

## Purpose / Big Picture

Deliver a deterministic CI and release pipeline that turns every `master` commit into a tested, Nix-built container image tagged by Git SHA, and turns every annotated tag `vX.Y.Z` into a published image plus a GitHub Release whose notes come from `CHANGELOG.md`. We continue using the existing Docker-based load-and-push flow (no requirement to switch to `skopeo`). A maintainer should be able to run a single local release script to bump the version, roll the changelog forward, tag, push, and let GitHub Actions handle publishing. The goal is that a novice can follow this plan alone to make the pipeline real and observable.

## Progress

Use a list with checkboxes and timestamps (UTC) to reflect real progress; update at every stopping point.

- [x] (2025-11-30 22:30Z) Wired `scripts/release` to call `codex`/`gemini` for release notes (with deterministic changelog/commit fallbacks) and logged the note source for observability.
- [x] (2025-11-30 20:30Z) Added commit-summary fallback to the release helper, captured release-note sourcing in logs, and taught the CI + release workflows to log derivations, load/push steps, and registry/tag metadata per the ExecPlan.
- [x] (2025-11-30 18:00Z) Drafted ExecPlan for CI/release pipeline refresh.
- [x] (2025-12-01 15:30Z) Expanded plan with novice definitions, milestones, and concrete commands.
- [x] (2025-12-01 17:10Z) Drafted and implemented `scripts/release` with guardrails, changelog roll-forward, tagging, and dry-run support.
- [x] (2025-12-01 17:40Z) Replaced CI workflow to run `scripts/run-tests`, build Nix image, and push GHCR tags on `master` with concurrency control.
- [x] (2025-12-01 18:00Z) Added tag-driven release workflow that rebuilds the image, pushes SHA + version tags, and publishes GitHub Releases from `CHANGELOG.md`.
- [x] (2025-12-01 18:10Z) Updated docs/changelog guidance (CHANGELOG entry, scripts/README, AGENTS) and kept validation guidance intact.

## Surprises & Discoveries

- Cypress e2e suite currently failing in CI-equivalent run: `scripts/run-tests` reports e2e failure (see log `/tmp/nix-shell.../dojo-run-tests-...`); will need follow-up before declaring validation complete.
- `scripts/release --dry-run` fails preflight on a dirty working tree, as expected while changes are in progress.

## Decision Log

- Decision: Keep the existing `packages.<system>.docker` flake output as the canonical image build and continue using Docker load/tag/push inside CI rather than switching to `skopeo`. Rationale: user confirmed the current Docker-based publish path is acceptable; minimizes churn while retaining Nix-built images. Date/Author: 2025-11-30 / agent.

## Outcomes & Retrospective

 Pending; summarize once the pipeline is implemented and exercised.

## Context and Orientation

Repository facts relevant to this work:
- CI today: `.github/workflows/ci.yml` builds with `nix build .#docker`, loads the tarball into Docker, and pushes via the Docker daemon. This path is acceptable per the latest guidance.
- Nix outputs: `flake.nix` defines `packages.<system>.docker` using `dockerTools.buildLayeredImage` with tag `latest`. We can continue to rely on this output; adjust tagging as needed for SHA/version.
- Tests: `scripts/run-tests` is the canonical runner; it wraps pytest suites and Cypress with skip flags. Use it in CI unless an explicit skip is justified.
- Versioning: `pyproject.toml` holds `version = "0.1.0"`. Tags follow `vX.Y.Z`. `CHANGELOG.md` follows Keep a Changelog with an `[Unreleased]` section.
- Git workflow: trunk-based on `master`; force-push is rare. Registry: currently GHCR (GitHub Container Registry). Kubernetes manifests live in `deploy/k8s/`, but environment overlays reside elsewhere; deployment is out of scope. GHCR is the container registry hosted by GitHub; Docker commands push images there with repository name `ghcr.io/<owner>/<image>`.

Definitions and assumptions for novices: Nix builds reproducible artifacts described in `flake.nix`; `dockerTools.buildLayeredImage` emits a tarball loadable by `docker load`, which creates a local image that can then be retagged. `github.sha` refers to the commit SHA provided by GitHub Actions; we will use its short form for tags. GHCR authentication uses the standard Docker login with `GITHUB_TOKEN` or a PAT scoped for packages. All commands assume the working directory `/home/ogle/src/dojo` inside the Nix dev shell described in `AGENTS.md`.

## Plan of Work

Describe in prose the edits and additions needed to satisfy the spec; keep each item self-contained.

1) Confirm the Nix image output used by CI. Keep or rename the existing `docker` package as the canonical image artifact; ensure it builds deterministically and is suitable for `docker load` (as today). Document the attribute name used by workflows and ensure tags (SHA/version) are applied after load. Explain that `docker load < result` produces a local image named `dojo:latest` that must be retagged before push.

2) Design the local release script (`scripts/release`, likely Python or POSIX shell) with these behaviors: guardrails (on `master`, clean tree, optional `git fetch`/up-to-date check), version bump logic (default patch; flags for minor/major), changelog roll-forward from latest `v*` tag to `HEAD`, release-notes summarization (LLM hook optional but must have deterministic fallback using commit messages grouped under Added/Changed/Fixed/Breaking), log output for each step, commit and annotated tag creation, push of branch and tag, and dry-run mode for testing. Ensure the script updates all versioned locations (at least `pyproject.toml`) and stages both the changelog and version change together. Define the CLI exactly: `scripts/release --bump {patch|minor|major} [--dry-run] [--notes-file PATH]`.

3) Replace CI workflow for pushes to `master`. Create `.github/workflows/ci.yml` (or rewrite existing) that checks out the pushed commit, installs Nix via `cachix/install-nix-action@v27`, runs `scripts/run-tests` inside `nix develop . --command ...`, and on success builds the image (`nix build .#docker` or the renamed attribute). Use the Docker daemon to publish `REGISTRY/dojo:<git_sha>` and optionally move `:staging`. Enforce concurrency so only the latest run per branch continues. Emit logfmt output for publish steps including derivation path, registry, tag, and status so a novice can match logs to actions.

4) Add release workflow for tags `v*.*.*` as `.github/workflows/release.yml`. Workflow should check out at the tag, install Nix, build the same image attribute, push via Docker as both `<git_sha>` and `vX.Y.Z`, and remain idempotent (re-push is fine). Parse `CHANGELOG.md` to extract the section for the tag and create or update a GitHub Release (title = version, body = extracted notes) using `gh release` or `actions/create-release`. Keep secrets minimal: registry credentials and `GITHUB_TOKEN`.

5) Wire registry configuration. Define environment variables or workflow inputs for `REGISTRY` (default GHCR), image name (`ghcr.io/<owner>/dojo` lowercase), and determine SHA via `github.sha` or `git rev-parse`. Prefer the short 12-character SHA for readability; document the choice and keep tags immutable once pushed.

6) Documentation and changelog updates. Add a brief note to `CHANGELOG.md` under `[Unreleased]` summarizing the pipeline overhaul once implemented. If developer ergonomics change (new script), add a short usage block to `scripts/README.md` and mention in `AGENTS.md` if expectations shift for running releases.

7) Validation plan. Define how to exercise the release script in dry-run mode, how to run the CI workflow locally (via `act` if feasible or by running `nix build` followed by `docker load/tag/push` in a smoke environment), and how to confirm images land in GHCR with correct tags. Include checks that the GitHub Release body matches the changelog section.

Milestones (narrative, each should leave the repo in a better observable state): first, lock down the canonical Nix image attribute and prove a docker load/push round-trip locally. Second, land the revised CI workflow so `master` pushes produce SHA-tagged images. Third, introduce the release workflow so tagging produces a GitHub Release with matching notes. Fourth, ship the local release script that bumps versions and tags with dry-run safety. Fifth, document and validate end to end by cutting a test tag in a private namespace.

## Concrete Steps

State exact commands with working directory `/home/ogle/src/dojo`. Adjust as discoveries occur.

- Inspect current image output and determinism: 
    nix build .#docker 
    nix path-info -S result 
  Use this to confirm the derivation and ensure reproducibility; the path-info output shows closure size to watch for regressions.

- After confirming the image attribute, verify Docker load flow: 
    docker load < result 
    docker images | head 
  Expect to see the image tagged `dojo:latest` (before retagging to SHA); this proves the tarball is usable by Docker.

- Draft and dry-run release script: 
    scripts/release --dry-run --bump patch 
  Expected logfmt snippets: step=preflight status=ok, step=changelog status=ok commits=N, step=version old=0.1.0 new=0.1.1.

- Validate changelog extraction for a tag: 
    python - <<'PY' 
    import changelog_parser  # whichever helper the script uses or inline parser 
    PY 
  Ensure the parser isolates the `## vX.Y.Z – YYYY-MM-DD` block and strips the `[Unreleased]` section.

- Manual push smoke (against a throwaway registry or using a personal token): 
    docker tag dojo:latest ghcr.io/OWNER/dojo:test-sha 
    echo "$CR_PAT" | docker login ghcr.io -u OWNER --password-stdin 
    docker push ghcr.io/OWNER/dojo:test-sha 
  Expect successful push and logfmt step=push tag=test-sha status=ok.

- Workflow lint: 
    act pull_request --job test  # optional if `act` available 
  Otherwise, validate YAML via `actionlint`.

## Validation and Acceptance

The implementation is acceptable when:
- Pushing to `master` triggers a workflow that runs `scripts/run-tests`, builds the Nix image, loads it into Docker, and publishes `REGISTRY/dojo:<git_sha>` successfully; concurrency cancels stale runs.
- Tagging `vX.Y.Z` triggers a workflow that rebuilds the same image, pushes `<git_sha>` and `vX.Y.Z` tags, and creates/updates a GitHub Release whose body matches the corresponding `CHANGELOG.md` section.
- The local release script aborts on dirty trees or wrong branch, bumps versions consistently, appends a dated changelog section, creates an annotated tag, pushes branch and tag, and emits logfmt lines for each step. A dry run performs all calculations without mutating the repo.
- Re-running release workflow for the same tag is idempotent: it overwrites the release notes and re-publishes the same image without duplicate artifacts.

## Idempotence and Recovery

- Nix builds are deterministic; rebuilding the same commit should yield identical digests. If a workflow fails after publishing `<git_sha>` but before moving `:staging`/`:latest`, rerun the job; Docker pushes are safe to repeat. If the release script aborts mid-run, unstage files (`git reset --hard` only if explicitly approved) and rerun with `--dry-run` to verify readiness before retrying. Avoid deleting tags unless intentionally rolling back a bad release; document any rollback steps taken.

## Artifacts and Notes

- Keep short evidence snippets (digests, logfmt lines) as the plan evolves, for example:  
    step=build derivation=/nix/store/.../docker-image-dojo status=ok sha=abcd123  
    step=push registry=ghcr.io/owner/dojo tag=abcd123 status=ok  
- When updating the plan, append a note here summarizing what changed and why, with date/author.

## Interfaces and Dependencies

- Nix attribute: continue using `packages.<system>.docker` (or a renamed equivalent) that yields a Docker-loadable image tarball. Document the attribute name consumed by CI/release workflows.
- Release script: `scripts/release` CLI with flags `--bump {patch|minor|major}`, `--dry-run`, optional `--notes-file`. It must call `git describe --tags --abbrev=0` to find the previous tag, parse `CHANGELOG.md`, and update `pyproject.toml`. Commit message: 2–5 sentences explaining why the release is cut and expected impact; tag annotated with the same version string.
- Workflows: `.github/workflows/ci.yml` and `.github/workflows/release.yml` using `cachix/install-nix-action@v27` (or newer), Docker daemon for load/tag/push, and `gh` or `actions/create-release` for GitHub Releases. Secrets: `GITHUB_TOKEN` (built-in) and registry credentials (e.g., `CR_PAT` if needed).

---
Change log for this ExecPlan:
- 2025-11-30: Initial version to align CI and release automation with Nix-built images.
- 2025-11-30: Updated to keep the existing Docker-based load/push flow (no `skopeo` requirement) per maintainer guidance.
- 2025-12-01: Made the plan fully self-contained for novices, added explicit milestones, SHA tagging rationale, and command expectations.
- 2025-12-01: Implemented release script, CI workflow refresh, and tag-driven release workflow; progress updated accordingly.
- 2025-11-30: Extended the release helper and workflows to match the ExecPlan (commit-based fallback notes, logfmt build/push steps, registry/tag metadata) and now invoke codex/gemini to draft release notes before falling back to changelog/commit summaries.

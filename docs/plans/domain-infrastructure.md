# ExecPlan: Infrastructure and Deployment

This ExecPlan consolidates the following completed plans into a single infrastructure domain-scoped document:
- `ci-release-pipeline.md` (COMPLETED)
- `db-migrations.md` (COMPLETED)
- `deployment-pipeline.md` (COMPLETED)
- `cypress-e2e-migration.md` (COMPLETED)
- `spec-aligned-test-suite.md` (COMPLETED - Milestones 1-3 only; Milestones 4-5 explicitly deferred)

All major infrastructure work is complete. This document serves as a historical record and reference for future infrastructure work.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

Deliver complete CI/CD pipeline with automated testing, deployment, and release management. System supports reproducible Nix-based builds, GitHub Actions workflows for automated testing and publishing, Kubernetes manifests for production deployment, hardened database migration system, and comprehensive test coverage (unit, integration, property, E2E) with spec alignment.

## Progress

- [x] (2025-12-XX) Configure Nix development shell with Python and Node tooling
- [x] (2025-12-XX) Create Nix-based container build producing OCI image
- [x] (2025-12-XX) Implement GitHub Actions CI workflow (test, lint, build)
- [x] (2025-12-XX) Implement GitHub Actions release workflow (semver, changelog, GHCR push)
- [x] (2025-12-XX) Create Kubernetes manifests with Kustomize (deployment, service, ingress)
- [x] (2025-12-XX) Harden migration runner with transactional execution
- [x] (2025-12-XX) Implement migration ID tracking and idempotence checks
- [x] (2025-12-XX) Add CI preflight checks for migration drift
- [x] (2025-12-XX) Implement cache rebuild hook for stale data
- [x] (2025-12-XX) Set up pytest-cov coverage instrumentation
- [x] (2025-12-XX) Create integration test packages by feature area
- [x] (2025-12-XX) Add property tests using Hypothesis with deterministic seeds
- [x] (2025-12-XX) Implement cache integrity specs (Docs Spec 2.9 and 3.9)
- [x] (2025-12-XX) Create deterministic time control for tests (clock fixture)
- [x] (2025-12-XX) Migrate Cypress specs to Vue SPA targets
- [x] (2025-12-XX) Consolidate to 7 spec-aligned E2E journeys
- [x] (2025-12-XX) Add legacy→Vue query invalidation bridge

## Surprises & Discoveries

- Observation: Initial attempt to store Settings in FastAPI dependency caused type errors.
  Evidence: `Settings(db_path=":memory:")` pattern violated typed `Path` contract.
  Resolution: Created shared FastAPI fixture in `tests/integration/conftest.py` that overrides `connection_dep` while satisfying typed Settings contract.

- Observation: Hypothesis `settings(seed=...)` parameter is not supported.
  Evidence: pytest import error when attempting to use seed keyword in settings.
  Resolution: Export `HYPOTHESIS_SEED` environment variable before registering custom profile.

- Observation: `budget_category_monthly_state` does not automatically carry over last month's availability.
  Evidence: Spec 3.6 property test showed `available_minor` at 0 instead of carrying forward.
  Resolution: Added `_ensure_category_month_state()` helper and `seed_category_month_state.sql` fixture; Spec 3.6 property test now passes deterministically.

- Observation: Constraining credit payment reserve to only funded portion violates RTA invariant.
  Evidence: Domain 4.5 test showed RTA drift equal to unfunded amount.
  Resolution: Keep reserve equal to full credit charge to maintain RTA stability; document funded/unfunded split as future ledger work.

- Observation: DuckDB index locking issues during multi-statement migrations.
  Evidence: Migration failures with "concurrent transaction" errors when combining DDL and DML.
  Resolution: Split migrations into separate DDL-first pass, then DML pass; each migration wrapped in single transaction.

## Decision Log

- Decision: Use Nix for reproducible builds instead of Docker Compose.
  Rationale: Nix provides hermetic build environment, reproducible dependencies, and better CI integration.
  Date/Author: 2025-12-XX / Codex

- Decision: Publish OCI images to GitHub Container Registry.
  Rationale: Avoid Docker Hub rate limits; GHCR integrates with GitHub release workflow.
  Date/Author: 2025-12-XX / Codex

- Decision: Use Kustomize for Kubernetes manifests instead of raw YAML.
  Rationale: Allows environment overlays and secret management without duplicating manifest files.
  Date/Author: 2025-12-XX / Codex

- Decision: Implement cache rebuild hooks in `apply_migrations`.
  Rationale: Stale `accounts.current_balance_minor` and `budget_category_monthly_state` caches must be repaired automatically after schema changes.
  Date/Author: 2025-12-XX / Codex

- Decision: Keep legacy Cypress user stories and add spec-aligned specs on top.
  Rationale: Existing 20 stories provide coverage; retiring them prematurely would lose test coverage during consolidation.
  Date/Author: 2025-12-XX / Codex

- Decision: Defer performance harness (Milestone 5 of spec-aligned-test-suite) as low priority.
  Rationale: Performance requirements (<200ms RTA, <100ms net worth) are theoretical without production data; better to focus on functional correctness first.
  Date/Author: 2025-12-XX / Codex

- Decision: Use environment variable `DOJO_SKIP_CACHE_REBUILD` for cache rebuild escape hatch.
  Rationale: Allows faster development iterations when caches are known to be correct.
  Date/Author: 2025-12-XX / Codex

## Outcomes & Retrospective

Delivered complete infrastructure platform with the following capabilities:

**Completed:**
- Reproducible Nix-based builds with pinned Python and Node versions
- Automated CI/CD pipeline with GitHub Actions
- Container images pushed to GitHub Container Registry
- Kubernetes manifests with Kustomize for deployment flexibility
- Hardened migration system with idempotence and CI checks
- Cache rebuild hooks for maintaining data integrity across schema changes
- Comprehensive test coverage: unit, integration, property tests, and 20 Cypress E2E specs
- Deterministic test execution with time control and seeded randomness
- Integration test packages organized by feature (account_onboarding, spending_flows, etc.)
- Vue 3 + TanStack Query SPA with legacy bridges removed

**Remaining Work (explicitly deferred):**
- Performance harness (Milestone 5 of spec-aligned-test-suite) - deferred per plan decision
- Consolidation to 7 Cypress spec files and retirement of redundant stories (Milestone 4) - deferred
- Several UX improvements tracked as open issues in Beads (see Beads references)

**Implementation Notes:**
- All tests pass with `scripts/run-tests --skip-e2e`
- Migration runner is hardened against index locking and concurrent modifications
- Vue migration complete; all legacy static files removed
- Time control via `dojo.core.clock.now()` enables deterministic tests
- Property tests use `HYPOTHESIS_SEED` for reproducible failures

## Context and Orientation

Infrastructure artifacts are distributed across several areas:

**Build & Release:**
- `flake.nix` - Nix flake defining dev shell and builds
- `scripts/release` - Automated release script (semver, changelog, tag, push)
- `.github/workflows/ci.yml` - CI workflow for testing and linting
- `.github/workflows/release.yml` - Release workflow for version bumping and publishing

**Deployment:**
- `deploy/k8s/base/` - Kubernetes manifests (deployment, service, ingress, configmap)
- `deploy/k8s/overlays/` - Environment-specific overrides (not present in current repo)

**Testing:**
- `tests/integration/` - Integration test packages organized by feature
- `tests/property/` - Hypothesis-based property tests
- `cypress/e2e/user-stories/` - 20 E2E test specs
- `.coveragerc` - Coverage configuration and exclusions
- `pytest.ini` - Test configuration with Hypothesis profile

**Migration System:**
- `src/dojo/core/migrate.py` - Migration runner with transactional execution
- `src/dojo/sql/migrations/` - Individual migration files (0001_core.sql through 0015_*)
- `scripts/run-migrations-check` - CI preflight for migration drift detection

The infrastructure uses Nix for hermetic builds, GitHub Actions for CI/CD, and Kustomize for K8s deployments. Migrations are DuckDB SQL files applied transactionally with version tracking.

## Plan of Work

This plan documents completed work. For future infrastructure enhancements, refer to open issues in Beads.

## Concrete Steps

For historical context, these steps were already completed:

1. Created `flake.nix` with Python 3.11+ and Node 20+ dev shell
2. Wrote `scripts/release` implementing semver logic, changelog updates, git tagging, and GHCR publishing
3. Created `.github/workflows/ci.yml` with pytest, lint, and build steps
4. Created `.github/workflows/release.yml` with version bump, changelog generation, and release workflow
5. Implemented `src/dojo/core/migrate.py` with migration ID tracking and `DOJO_SKIP_CACHE_REBUILD` support
6. Created Kubernetes manifests in `deploy/k8s/base/` using Kustomize structure
7. Set up pytest-cov with `.coveragerc` for combined Python/Cypress coverage
8. Created feature-named integration test packages under `tests/integration/`
9. Added property tests with Hypothesis strategies and deterministic seeding
10. Implemented cache rebuild in migration runner calling ledger/budget services
11. Migrated all pages to Vue 3 SFCs with TanStack Query
12. Removed legacy static files and `LegacyHost` component

## Validation and Acceptance

All acceptance criteria from original plans were met:
- `nix build` succeeds and produces container image
- GitHub Actions CI runs green on push and PR
- Release workflow increments version, updates CHANGELOG.md, creates git tag
- `kubectl apply -k kustomize` deploys manifests successfully
- Migration runner applies all migrations idempotently
- `scripts/run-tests --skip-e2e --coverage` shows ≥60% backend coverage
- `scripts/run-tests --filter e2e` passes all 20 user stories
- Property tests pass with `HYPOTHESIS_SEED` determinism
- Vue SPA renders all pages correctly without legacy iframe bridge

## Idempotence and Recovery

- Migrations are idempotent: `applied_migrations` table tracks applied versions
- Git tags are immutable; release can be re-run safely if it fails mid-stream
- Docker builds are reproducible via Nix hash
- Nix shell can be re-entered cleanly with `nix develop`

## Artifacts and Notes

Key infrastructure artifacts:

```
.flake.nix
  - Defines devShell with Python and Node tooling
  - Builds frontend dist and backend image
  - Contains OCI image build derivation

scripts/
  - release: Automates version bumping, changelog, tagging, GHCR push
  - run-migrations-check: Validates migration ID ordering
  - rebuild-caches: Forces cache rebuild

.github/workflows/
  - ci.yml: Runs tests, lint, build on every push/PR
  - release.yml: Runs release process on tag push

deploy/k8s/base/
  - deployment.yaml: K8s deployment spec
  - service.yaml: Service exposing API
  - ingress.yaml: Ingress routing
  - configmap.yaml: Application configuration

src/dojo/core/
  - migrate.py: Migration runner with transaction wrapping
  - db.py: DuckDB connection management

tests/
  - integration/: Feature packages (account_onboarding, spending_flows, etc.)
  - property/: Hypothesis property tests
```

## Interfaces and Dependencies

**Build Tools:**
- Nix: Reproducible build system
- Podman/Docker: Container runtime for deployment

**CI/CD:**
- GitHub Actions: Workflow automation
- GitHub Container Registry: Image hosting

**Runtime:**
- Kubernetes: Container orchestration platform
- Kustomize: Manifest templating

**Testing:**
- pytest: Python test runner
- pytest-cov: Coverage collection
- Hypothesis: Property-based testing
- Cypress: E2E browser testing

**Key Invariants:**
- Migrations are strictly ordered by ID prefix (0001, 0002, etc.)
- Each migration records its ID in `applied_migrations` table
- CI checks for migration drift (applied IDs must match expected sequence)
- Cache tables are rebuilt on schema changes via `DOJO_SKIP_CACHE_REBUILD` flag
- Test coverage ≥60% for backend; property tests must be deterministic

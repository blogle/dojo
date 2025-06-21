# Agents.md – Operating Guide for OpenAI Codex

This file tells automated coding agents (Codex, GPT‑4o, etc.) exactly **how to work inside the Dojo repository**.

---

## 1 North‑Star

> *Build a small, self‑hostable envelope‑budgeting webapp (two users, real‑time sync, bank import) in **Rust + TypeScript** with a single **Postgres** database, matching Aspire‑Sheet parity.*
> Keep this objective in context for every task.

---

## 2 Project Structure for Navigation

```text
.
├─ docs/                     ← spec & ADRs (source of truth)
│  ├─ 00_overview.md
│  ├─ 01_requirements.md
│  ├─ 02_data_model.md
│  ├─ 03_api_contract.yaml
│  ├─ 04_architecture.md
│  ├─ 06_test_plan.md
│  └─ ADR/
├─ backend/                  ← Rust API service
│  ├─ src/                   ← production code
│  │   ├─ auth/              ← Google OIDC
│  │   ├─ domain/            ← business logic (transactions, envelopes)
│  │   ├─ db/                ← SQLx queries
│  │   └─ ws/                ← in‑process hub
│  ├─ tests/                 ← integration & property tests
│  └─ migrations/            ← SQLx *.sql
├─ frontend/                 ← React SPA
│  ├─ src/
│  │   ├─ components/        ← UI atoms/molecules (PascalCase.tsx)
│  │   ├─ pages/             ← route components
│  │   ├─ hooks/             ← custom hooks (camelCase.ts)
│  │   ├─ services/          ← OpenAPI‑generated client hooks
│  │   └─ styles/
│  └─ cypress/               ← e2e specs
├─ tests/fixtures/           ← seed data & CSVs for migration parity
├─ setup.sh                  ← provision script for Codex container
└─ .github/workflows/        ← CI pipelines
```

*Codex must not create files outside these folders without human approval.*

---

## 3 Coding Conventions

### 3.1 General

| Rule                                                  | Why               |
| ----------------------------------------------------- | ----------------- |
| **TypeScript** for all new frontend code              | Type‑safety       |
| **Rust stable** (≥1.78) for backend                   | performance & ADR |
| Formatters must pass (`cargo fmt`, `eslint+prettier`) | consistency       |
| Expressive names & doc comments for complex logic     | readability       |
| No `TODO:`/`FIXME:` in committed code                 | code health       |

### 3.2 Backend

* Frameworks: **axum**, **tokio**, **sqlx** only—introducing others requires a new ADR.
* All DB access via `sqlx::query!` / `query_as!` with compile‑time checks.
* Tests: unit + property + integration live under `backend/tests/` or inline modules.
* Commands (Codex should run **inside the provisioned shell**; no Docker):

  ```bash
  # run all Rust tests
  cargo test --all
  # micro‑benchmarks
  cargo bench
  ```
* Environment: rely on variables set by `setup.sh` (`DATABASE_URL`, etc.).

### 3.3 Frontend

* Functional React components with hooks.
* File naming: **PascalCase.tsx** (components), **camelCase.ts** (hooks, utils).
* Styling: TailwindCSS utility classes; fallback to module CSS sparingly.
* Data access exclusively through generated hooks in `src/services/*` (never call `fetch`).
* Commands:

  ```bash
  # unit / integration
  pnpm test
  # e2e (headless)
  pnpm cypress run
  # lint & type‑check
  pnpm lint && pnpm type-check
  ```

---

## 4 Testing & Quality Gates

Run **all** checks before opening a PR:

```bash
# Backend tests & lints
cargo fmt -- --check && cargo clippy -- -D warnings && cargo test --all
# Frontend tests & lints
pnpm lint && pnpm type-check && pnpm test && pnpm build --dry-run
# E2E
pnpm cypress run
```

The CI pipeline mirrors these; commits that fail locally will fail CI.

Benchmarks (`cargo bench`, `pnpm vitest bench`) run nightly; keep them green but they are not required on every PR.

---

## 5 Pull‑Request Checklist

1. **Description** – what & why; reference `US‑xx` / `NFR‑xx` IDs.
2. **Docs updated** when API/schema/behaviour changes.
3. **Tests added/updated**; all pass.
4. **Screenshots** for UI changes (attach PNG/GIF).
5. **One concern per PR** – no kitchen‑sink.
6. **CI green** – lint, type‑check, build.
7. **Target branch = `master`**; never push directly.

---

## 6 Forbidden Actions

| ID   | Action                                            | Reason                        |
| ---- | ------------------------------------------------- | ----------------------------- |
| F‑01 | Add another runtime service (broker, redis, etc.) | Simplicity ADR.               |
| F‑02 | Use JavaScript in production code                 | TS mandate.                   |
| F‑03 | Modify `.github/workflows/` to skip tests         | Integrity.                    |
| F‑04 | Commit to `master` directly                       | PR review required.           |
| F‑05 | Change OpenAPI without updating docs/tests        | Spec drift.                   |
| F‑06 | Assume Docker/Compose availability                | Codex container lacks Docker. |

---

## 7 Provisioning Environment for Codex

*Codex should execute the repo‑root `setup.sh` script once per workspace.*  It installs Postgres, pnpm, SQLx CLI, applies migrations, and launches both the API and Vite dev servers.  All commands in this guide assume that script has been executed and services are reachable at:

* API – [http://localhost:3000](http://localhost:3000)
* Frontend – [http://localhost:5173](http://localhost:5173)

---

## 8 Canonical Reference Docs

* `docs/01_requirements.md` – functional scope
* `docs/02_data_model.md` – schema
* `docs/03_api_contract.yaml` – endpoint shapes
* Any ADR in `docs/ADR/` – immutable decisions

Codex must consult these before coding.

---

## 9 Clarifications & Questions

If the task is ambiguous, open an **issue** titled `clarify:<topic>` and await human guidance instead of guessing.

---

*Last updated: 2025‑06‑20*


# Dojo – Personal Finance App

Welcome to **Dojo**, a web‑based envelope‑budgeting tool that replaces the Aspire Budget Google‑Sheets workflow while adding real‑time collaboration and automatic bank imports.

---

## Project Structure

```text
.
├─ README.md                  ← (this file)
├─ docs/                      ← design docs & ADRs
│  ├─ 00_overview.md
│  ├─ 01_requirements.md
│  ├─ 02_data_model.md
│  ├─ 03_api_contract.yaml
│  ├─ 04_architecture.md
│  ├─ 05_migrations.md
│  ├─ 06_test_plan.md
│  └─ ADR/
├─ backend/                   ← Rust API service
│  ├─ Cargo.toml
│  ├─ src/
│  └─ tests/
├─ frontend/                  ← React SPA
│  ├─ package.json
│  └─ src/
├─ docker-compose.yml         ← local dev stack
└─ .github/workflows/         ← CI / CD definitions
```

---

## Getting Started (local)

1. **Prerequisites**

   * Docker ≥ 24
   * Node ≥ 20 + pnpm (for frontend)
   * Rust ≥ 1.78; install with `rustup`.
2. **One‑liner**

   ```bash
   docker compose up --build
   ```

   This starts Postgres, the Rust API in watch‑mode, and the React dev server.
3. **Login**

   * Visit [http://localhost:5173](http://localhost:5173) → Sign‑in with Google (OAuth callback points to `http://localhost:5173`).
4. **Run tests**

   ```bash
   just test      # or: cargo test && pnpm vitest
   just e2e       # runs Cypress
   ```

---

## Reference Material

| Doc                    | Purpose                                                   |
| ---------------------- | --------------------------------------------------------- |
| `00_overview.md`       | Mission, glossary.                                        |
| `01_requirements.md`   | Functional & non‑functional requirements (US‑xx, NFR‑xx). |
| `02_data_model.md`     | Postgres schema + ER diagram.                             |
| `03_api_contract.yaml` | OpenAPI 3 contract for REST endpoints.                    |
| `04_architecture.md`   | Component architecture & data flow.                       |
| `05_migrations.md`     | SQLx migrations & CSV import mapping.                     |
| `06_test_plan.md`      | Test layers, CI matrix, pass/fail gates.                  |
| `ADR/`                 | Immutable architectural decisions.                        |

---

## Contributing

1. Create a feature branch from `master`.
2. Update or add docs **before** writing code.
3. Ensure `just check` passes (lint, unit, property tests).
4. Open PR – CI must be green to merge.
5. Follow existing coding conventions; reference requirement IDs in commits (e.g. `US‑05: implement manual transaction endpoint`).

---


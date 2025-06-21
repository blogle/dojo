# Backend – Dojo API Service

Rust · Axum · SQLx · Tokio · WebSockets

---

## 1 Code Layout

```text
backend/
├─ src/
│  ├─ main.rs              ← axum server bootstrap
│  ├─ router.rs            ← route tree generated from OpenAPI
│  ├─ auth/                ← Google OIDC verifier & middleware
│  ├─ domain/              ← business services (transactions, envelopes)
│  │   ├─ mod.rs
│  │   ├─ transactions.rs
│  │   ├─ categories.rs
│  │   └─ transfers.rs
│  ├─ db/                  ← SQLx queries, migrations helpers
│  ├─ ws/                  ← in‑process hub, message structs
│  └─ telemetry.rs         ← tracing + JSON subscriber
├─ migrations/             ← SQLx CLI migrations (*.sql)
├─ tests/                  ← integration tests (Tokio)
└─ tools/                  ← optional Python scripts (import, analysis)
```

## 2 Key Libraries / Frameworks

| Area          | Crate                           | Notes                                                  |
| ------------- | ------------------------------- | ------------------------------------------------------ |
| HTTP server   | `axum`                          | Async router; extracted from OpenAPI via `oai-gen`.    |
| Async runtime | `tokio`                         | Multi‑thread runtime, pinned to LTS version.           |
| Database      | `sqlx` (Postgres)               | Compile‑time checked queries; uses `sqlx::migrate!()`. |
| Auth          | `openidconnect`, `jsonwebtoken` | Verifies Google tokens, signs household JWT.           |
| WebSocket     | `tokio-tungstenite`             | Hub holds `HashMap<HouseholdId, Vec<Tx>>`.             |
| Observability | `tracing`, `tower-http::trace`  | JSON structured logs.                                  |
| Benchmarks    | `criterion`                     | Micro‑benchmarks in `benches/`.                        |

## 3 Development Workflow

Development is container‑first—no local Rust toolchain required.

### 3.1 Start the stack

```bash
# start Postgres + API container
docker compose -f docker-compose.dev.yml up --build
```

Services started:

| Container | Purpose                                                    |
| --------- | ---------------------------------------------------------- |
| `db`      | Postgres 15 with volume‑backed data                        |
| `api`     | Rust source mounted; runs `cargo run` inside the container |

API listens on [http://localhost:3000](http://localhost:3000) and auto‑applies migrations on startup.

> **Reloading code** – Rebuild the API container when Rust sources change:
>
> ```bash
> docker compose exec api cargo run   # quick recompile without rebuilding image
> # or simply restart container
> docker compose restart api
> ```

### 3.2 Interactive shell

```bash
docker compose exec api bash          # inside container with cargo + sqlx-cli
```

 Interactive shell

```bash
docker compose exec api bash          # inside container with cargo + sqlx-cli
```

### 3.3 Database tasks

```bash
# create migration (inside api shell)
sqlx migrate add create_foo_table

# apply migrations (automatically done on start, but can run manually)
just db-migrate
```

### 3.4 Running tests

```bash
# unit + property
docker compose exec api cargo test

# integration (hits running db)
docker compose exec api cargo test --test integ

# benchmarks (criterion)
docker compose exec api cargo bench
```

---

## 4 API Docs

* Swagger UI exposed at `http://localhost:3000/api/docs`.

---

 Patterns & Conventions

* **Hexagonal-ish**: HTTP layer -> service layer -> repository (SQLx).  No business logic in handlers.
* **Error handling**: thiserror enums converted to `axum::response::IntoResponse` with proper status codes.
* **Validation**: `validator` derives on request DTOs; complex invariants in domain layer (e.g. inflow XOR outflow).
* **Tracing spans**: every request gets `trace_id`; DB queries attach `record="sqlx"` field.
* **Idempotency**: external IDs (Plaid transaction\_id) have `UNIQUE` constraints to ensure upsert.

---

## 5 Running in Production

* Build: `cargo build --release` -> single static binary (\~15 MB).
* Config via env vars (see `.env.example`).
* Health checks: `/healthz` (200 if DB reachable) used by Fly.
* Logging: `RUST_LOG=info,dojo=debug` prints JSON to stdout.

---

## 6 Further Reading

* [04\_architecture.md](../docs/04_architecture.md)
* [02\_data\_model.md](../docs/02_data_model.md)
* ADR‑2025‑06‑20‑core‑tech‑stack

---


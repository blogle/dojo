# ADR - 2025-06-20-core-tech-stack

*Status* | Accepted  
*Deciders* | Brandon Ogle, Project “dojo” team  
*Date* | 2025-06-20  

## 1  Context

We are porting the Aspire Budget Google-Sheets system to a small, real-time web application used by exactly two people.
Key constraints:

* **Low-cost hosting** – ideally free hobby tier or inexpensive VPS.  
* **Low operator burden** – no fleets of supporting services, minimal DevOps.  
* **Strong type-safety** and performance (historical budget logic must stay correct forever).  
* Existing team proficiency in Rust, TypeScript, SQL; some tasks easier in Python.  

The architecture doc (04_architecture.md) already drafts a single-service model and eliminated heavyweight options (Kafka, RabbitMQ, separate OLAP store, etc.).  
This ADR locks the core technology choices so that future automated code generation (Codex) cannot “wander off.”

## 2  Decision

| Concern | Decision |
|---------|----------|
| **Backend language** | **Rust 1.78+** using `axum`, `tokio`, `sqlx`.  Python may be used *only* for off-path tooling (one-shot data import, ad-hoc analysis) and lives under `backend/tools/`; it will not serve runtime traffic. |
| **Frontend language** | **TypeScript 5** (React + Vite).  No JavaScript “plain” files in production code. |
| **Database** | **PostgreSQL 15** single cluster.  Same instance serves OLTP and analytic queries.  Bitemporal (“system-versioned”) tables provide as-of queries. |
| **Deployment platform** | **Fly.io** as the default reference deployment (shared-CPU hobby tier).  Secondary option: self-host via `docker compose` on any VPS (Hetzner CX11). |
| **Auth** | Google OAuth 2 / OIDC; no Auth0, Cognito, Clerk, etc. |
| **Message bus / broker** | **None.**  Real-time updates delivered via WebSocket hub inside the Axum process. |
| **CI/CD** | GitHub Actions ➜ `flyctl deploy`.  Failed health-check triggers `fly release revert`. |
| **Observability** | `tracing` JSON logs to stdout; rely on Fly log aggregation.  No Prometheus/Grafana stack. |

## 3  Rationale

1. **Rust** gives compile-time guarantees and excellent perf while remaining resource-light—perfect for hobby-tier hardware.  
2. **TypeScript** eliminates an entire class of front-end runtime errors and unifies types with generated OpenAPI client code.  
3. **Single Postgres** keeps operations simple; 6 000 transactions in five years is trivial for modern Postgres even with historical tables.  
4. **Fly.io** offers the easiest path to free TLS, global Anycast, one-command deploy, and built-in Postgres.  It matches our “zero-maintenance” goal better than AWS.  
5. **Removing brokers and extra stores** avoids y-axis complexity that does not benefit a two-user system.  
6. **Google OAuth** is free, our users already have Google accounts, and it avoids vendor lock-in.  

## 4  Consequences

* Codex and human contributors **must not introduce** alternative stacks (Node.js, Go, Django, NoSQL, etc.) without a superseding ADR.  
* All shared types flow Rust → OpenAPI → TypeScript to keep end-to-end type safety.  
* Local dev remains one-liner (`docker compose up`) because only three containers are needed: api, postgres, pgadmin.  
* Future features (mobile PWA, scheduled jobs) must fit within the single-service Rust process or be justified in a new ADR.  
* If Fly.io changes its pricing/free-tier terms, the fallback self-hosting path is pre-blessed and requires no architectural change.  

---

*“Fixed rails yield smoother coding trains.”*  
Any proposal to diverge from this ADR must be captured in a new ADR and approved by the same deciders.


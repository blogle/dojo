# Frontend – Dojo React SPA

React 18 · TypeScript 5 · Vite · TanStack Query · Cypress

---

## 1 Directory Layout

```text
frontend/
├─ src/
│  ├─ index.tsx            ← entrypoint (React‑DOM)
│  ├─ App.tsx              ← router & layout shell
│  ├─ pages/               ← route components (Dashboard, Reports, Settings)
│  ├─ components/          ← reusable UI widgets (EnvelopeCard, AccountList)
│  ├─ hooks/               ← custom hooks (useCategoryTransfer)
│  ├─ services/            ← auto‑generated API client (OpenAPI)
│  ├─ context/             ← AuthProvider, HouseholdProvider
│  ├─ styles/              ← tailwind.css + postcss config
│  ├─ tests/               ← vitest unit tests
│  └─ vite-env.d.ts
├─ public/                 ← static assets (favicons, logo)
├─ cypress/                ← e2e specs & fixtures
├─ vitest.config.ts
└─ vite.config.ts
```

## 2 Key Libraries

| Purpose            | Library                        | Notes                                          |
| ------------------ | ------------------------------ | ---------------------------------------------- |
| UI framework       | React 18                       | functional components, hooks                   |
| Routing            | React Router 6                 | nested routes (`/dashboard`, `/reports/:kind`) |
| Data‑fetching      | TanStack Query v5              | caching, optimistic updates, WS invalidation   |
| Forms & validation | React Hook Form + Zod          | schema‑derived TS types                        |
| Styling            | Tailwind CSS                   | configured via `tailwind.config.ts`            |
| Icons              | Lucide‑react                   | tree‑shakeable SVG icons                       |
| Charts             | Recharts                       | used in trends & spending reports              |
| State management   | TanStack Query + React Context | no Redux                                       |
| Testing            | Vitest + Testing Library       | unit & integration                             |
| E2E                | Cypress 13                     | CI browser tests                               |

## 3 Development

```bash
pnpm i            # install deps
pnpm dev          # runs Vite on http://localhost:5173
```

Environment variables (`.env.local`):

```env
VITE_API_URL=http://localhost:3000
GOOGLE_OAUTH_CLIENT_ID=<client-id>
```

### 3.1 Generate API Client

```bash
pnpm openapi      # runs oai-gen – updates src/services/**
```

Client hooks (`useTransactionsQuery`, etc.) are code‑gen’d; manual edits will be overwritten.

### 3.2 Tests

```bash
pnpm test         # vitest
pnpm cypress open # interactive e2e
```

## 4 Patterns & Conventions

* **Atomic components** live in `components/` with Storybook (future).
* **API hooks** are the single source of data; components never call `fetch` directly.
* **Optimistic UI**: mutations use `queryClient.setQueryData` & `onError` rollback.
* **WebSocket invalidation**: WS messages map to `queryClient.invalidateQueries` keys.
* **Accessibility**: components meet WCAG 2.1 AA; verified by eslint‑plugin‑jsx‑a11y.
* **Code style**: eslint + prettier (run on pre‑commit).

## 5 Build & Deploy

```bash
pnpm build        # outputs dist/ (~100 kB gzipped)
```

`dist/` is served by the Rust API at `/` in production.

---

## 6 Further Reading

* [04\_architecture.md](../docs/04_architecture.md)
* [06\_test\_plan.md](../docs/06_test_plan.md)

---



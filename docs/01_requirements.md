# Dojo – Functional & Non‑functional Requirements

> All IDs are stable.  Codex and humans must reference them exactly.

---

## 1 Functional user stories

| ID        | Title                           | GIVEN                                             | WHEN                                                         | THEN                                                                                                  |
| --------- | ------------------------------- | ------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| **US‑01** |  Create category                | The primary user is on **Settings > Categories**  | They submit a new name, group, monthly amount, and goal      | The system stores the category, emits `category.created`, and shows it in the UI with `balance = 0`   |
| **US‑02** |  Edit category                  | A category exists                                 | The user updates any field                                   | The system persists the change, recalculates reports, broadcasts `category.updated`                   |
| **US‑03** |  Archive category               | A category exists with historical data            | The user clicks **Archive**                                  | The category is hidden from selectors, but historical transactions remain valid                       |
| **US‑04** |  Create account                 | The primary user is on **Settings > Accounts**    | They enter name, type (asset / credit), and starting balance | The system stores the account, emits `account.created`, balance appears on dashboard                  |
| **US‑05** |  Record transaction (manual)    | A user is on **Add Transaction**                  | They enter date, payee, amount, account, category, status    | The system inserts a transaction row, updates account & category balances instantly                   |
| **US‑06** |  Import bank transactions       | The user linked a Chase account via Plaid         | The nightly sync runs                                        | New cleared and pending transactions are fetched, de‑duplicated, and inserted with `source = plaid`   |
| **US‑07** |  Categorise pending transaction | A pending transaction exists and is uncategorised | The user selects a category                                  | The category field updates; when the transaction settles it keeps the chosen category                 |
| **US‑08** |  Transfer between accounts      | **Transfer** modal open                           | User selects from‑account, to‑account, amount                | Two offsetting transactions are written; account balances update; no category impact                  |
| **US‑09** |  Transfer between categories    | **Budget** screen open                            | User drags money from source to destination envelope         | A `category_transfer` record is created; both category balances update; `Available to budget` adjusts |
| **US‑10** |  Reconcile account              | Sheet balance ≠ bank balance                      | User enters official balance and clicks **Reconcile**        | System auto‑generates an adjusting transaction or flags discrepancies for review                      |
| **US‑11** |  View dashboard                 | Data exists                                       | User opens **Dashboard**                                     | The page streams current `Available to budget`, account list, category table, and alerts              |
| **US‑12** |  Run spending report            | User selects date range                           | User opens **Reports > Spending**                            | The system returns grouped totals and charts within 100 ms                                            |
| **US‑13** |  Real‑time collaboration        | Two users view the same household budget          | One saves a new transaction                                  | The other sees the update within 1 s without refreshing                                               |

---

## 2 Non‑functional requirements

| ID         | Requirement                   | Metric                                                                             |
| ---------- | ----------------------------- | ---------------------------------------------------------------------------------- |
| **NFR‑01** | **Performance – dashboard**   | p99 render time ≤ 100 ms with 10 years (\~50 k tx)                                 |
| **NFR‑02** | **Real‑time latency**         | Update fan‑out ≤ 1 s 95th percentile                                               |
| **NFR‑03** | **Bank sync reliability**     | Missed‑day rate < 0.1 % per institution per year                                   |
| **NFR‑04** | **Mobile usability**          | Core flows reachable on screens ≥ 375 px; Lighthouse mobile perf ≥ 80              |
| **NFR‑05** | **Security**                  | All data encrypted in transit (TLS 1.3) and at rest (AES‑256); OWASP Top‑10 tested |
| **NFR‑06** | **Privacy**                   | Budget data never leaves US‑region server; no third‑party analytics without opt‑in |
| **NFR‑07** | **Availability**              | 99.5 % monthly uptime (single‑AZ acceptable)                                       |
| **NFR‑08** | **Test coverage**             | ≥ 90 % unit coverage backend; ≥ 70 % e2e critical paths                            |
| **NFR‑09** | **Accessibility**             | WCAG 2.1 AA; keyboard‑only navigation passes axe audit                             |
| **NFR‑10** | **Internationalisation prep** | All strings externalised; date / currency formatting via i18n util                 |

---

## 3 Out‑of‑scope (MVP)

* Multi‑household support
* Attachments / receipt images
* Offline edits with conflict‑free merge
* Payroll / invoice generation

---


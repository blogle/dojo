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


## 4 Aspire‑sheet parity

### 4.1 Configuration
- **SB‑CONF‑01** – Columns: `household_id` (UUID), `current_month` (DATE), `default_currency` (TEXT), `last_import_ts` (TIMESTAMPTZ).
- **SB‑CONF‑02** – Validation: `current_month` must be the first day of a month; `default_currency` is ISO‑4217.
- **SB‑CONF‑03** – User actions: update currency, advance `current_month` when closing a month.
- **SB‑CONF‑04** – SQL: `UPDATE configuration SET current_month = DATE_TRUNC('month', $next) WHERE household_id = $hid;`

### 4.2 Category Transfers
- **SB‑CT‑01** – Columns: `id`, `date`, `from_category_id`, `to_category_id`, `amount`, `memo`, `created_by`.
- **SB‑CT‑02** – Validation: amount > 0; categories exist, not archived, and cannot be identical.
- **SB‑CT‑03** – User actions: create, edit, or delete a transfer via drag‑and‑drop in Budget.
- **SB‑CT‑04** – SQL:
  ```sql
  INSERT INTO category_transfers (household_id, date, from_category_id, to_category_id, amount, memo, created_by)
  VALUES ($hid, $date, $from, $to, $amount, $memo, $uid);
  ```

### 4.3 Transactions
- **SB‑TX‑01** – Columns: `id`, `date`, `payee`, `memo`, `account_id`, `category_id`, `inflow`, `outflow`, `status`, `source`, `external_id`, `created_by`.
- **SB‑TX‑02** – Validation: `inflow` and `outflow` are mutually exclusive; `status` in {pending, settled}; FK household check.
- **SB‑TX‑03** – User actions: add/edit transaction, import from bank, change category, reconcile.
- **SB‑TX‑04** – SQL example:
  ```sql
  SELECT starting_balance + SUM(inflow - outflow) AS balance
    FROM transactions
   WHERE account_id = $acc AND status = 'settled';
  ```

### 4.4 Balances
- **SB‑BAL‑01** – Views `v_category_balance` and `v_account_balance` expose computed `balance` per category or account.
- **SB‑BAL‑02** – `v_category_balance` formula:
  ```sql
  SELECT  c.id AS category_id,
          COALESCE(SUM(t.inflow - t.outflow),0)
        + COALESCE(SUM(ct_in.amount),0)
        - COALESCE(SUM(ct_out.amount),0) AS balance
  FROM    categories c
  LEFT JOIN transactions t      ON t.category_id = c.id AND t.status = 'settled'
  LEFT JOIN category_transfers ct_in  ON ct_in.to_category_id = c.id
  LEFT JOIN category_transfers ct_out ON ct_out.from_category_id = c.id
  GROUP BY c.id;
  ```
- **SB‑BAL‑03** – Materialised views refresh after every write.

### 4.5 Dashboard
- **SB‑DB‑01** – Controls: filter by `as_of` date; open add‑transaction/transfer dialogs.
- **SB‑DB‑02** – Data: shows available‑to‑budget total, account balances, category balances, and alerts.
- **SB‑DB‑03** – SQL combines `v_account_balance`, `v_category_balance`, and configuration to compute `available_to_budget`.

### 4.6 Spending
- **SB‑SPEND‑01** – Columns: `month`, `category_id`, `outflow_total`, `percent_of_income`.
- **SB‑SPEND‑02** – User actions: choose date range and optional category group.
- **SB‑SPEND‑03** – SQL:
  ```sql
  SELECT date_trunc('month', date) AS month,
         category_id,
         SUM(outflow) AS outflow_total
    FROM transactions
   WHERE date BETWEEN $from AND $to AND status = 'settled'
   GROUP BY month, category_id;
  ```

### 4.7 Trend
- **SB‑TREND‑01** – Columns: `month`, `category_id`, `running_balance`.
- **SB‑TREND‑02** – SQL:
  ```sql
  SELECT date_trunc('month', date) AS month,
         category_id,
         SUM(inflow - outflow) OVER (PARTITION BY category_id ORDER BY date_trunc('month', date)) AS running_balance
    FROM transactions
   WHERE status = 'settled';
  ```

### 4.8 Category
- **SB‑CAT‑01** – Columns: `id`, `group_id`, `name`, `type`, `monthly_amount`, `goal_amount`, `balance`, `is_archived`, `sort_order`.
- **SB‑CAT‑02** – Validation: name unique per household; amounts ≥ 0; `sort_order` integer.
- **SB‑CAT‑03** – User actions: create, edit, reorder, and archive categories.
- **SB‑CAT‑04** – SQL: balance derived via `v_category_balance`.

### 4.9 Account
- **SB‑ACC‑01** – Columns: `id`, `name`, `type`, `starting_balance`, `is_archived`, `created_at`.
- **SB‑ACC‑02** – Validation: name unique per household; starting_balance numeric; type ∈ {asset, credit}.
- **SB‑ACC‑03** – User actions: create account, rename, archive, reconcile.
- **SB‑ACC‑04** – SQL: balance derived via `v_account_balance`.

### 4.10 Income vs Expense
- **SB‑IVE‑01** – Columns: `month`, `income_total`, `expense_total`, `difference`.
- **SB‑IVE‑02** – User actions: choose date range for the report.
- **SB‑IVE‑03** – SQL:
  ```sql
  SELECT date_trunc('month', date) AS month,
         SUM(inflow) AS income_total,
         SUM(outflow) AS expense_total,
         SUM(inflow - outflow) AS difference
    FROM transactions
   WHERE date BETWEEN $from AND $to AND status = 'settled'
   GROUP BY month;
  ```


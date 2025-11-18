# Architecture Domain: Assets and Liabilities

This document defines the structure, behavior, and persistence rules for financial instruments that contribute to the system’s Net Worth calculation. It establishes the relationship between the Transaction Ledger and the Budgeting Domain and formalizes how money moves and is categorized throughout the application.


## 1. Account Hierarchy and Contribution to Net Worth


All accounts are classified into six primary classes reflecting their operational purpose and relationship to budgeting. Conceptually, each account has a class (cash, credit card, investment, etc.) and a role (on‑budget vs tracking‑only). The canonical `accounts` table stores lifecycle and balance information; per‑class SCD‑2 tables store configuration details that may change over time (interest rates, terms, fair values).

The balance of every financial account is a derived value computed from the complete transaction history, beginning with an explicit opening balance entry on the ledger. Adjustments should occur only via explicit corrective transactions to preserve an auditable history.

The primary classes of accounts and their budgeting and net worth characteristics are:

| Account Class            | Operational Role           | Budget Impact                                                                 | Net Worth Contribution        |
|--------------------------|----------------------------|-------------------------------------------------------------------------------|-------------------------------|
| Cash and Checking        | Active (On‑Budget)         | Sole source of Ready to Assign funds and envelope allocations                | Full                          |
| Credit and Borrowing     | Active (On‑Budget)         | Destination for budgeted debt payments; purchases consume funded envelopes    | Full (Negative)               |
| Accessible Assets        | Passive (Tracking, Off‑Budget) | Off‑budget savings; flows to/from cash must be categorized in the budget | Full                          |
| Investments (Brokerage)  | Passive (Tracking)         | Budgeted contributions reduce category balances; decumulation may be income   | Full                          |
| Long‑Term Borrowing      | Passive (Tracking)         | Budgeted payments reduce envelopes; liability balance comes from the ledger   | Full (Negative)               |
| Tangibles                | Passive (Tracking)         | No direct budget effect; affects net worth via fair value only                | Net Worth only                |

Every financial account’s balance is derived from historical ledger entries referencing that account. Users reconcile these balances to external statements using the reconciliation log, with rare corrective entries allowed to maintain historical integrity. Tangibles are the exception: they contribute to net worth via an SCD‑2 fair value rather than a cash ledger balance.


## 2. Invariance Rules and Budgeting Mechanics


The system enforces invariance rules necessary for a zero-based budgeting model and a clean separation between on‑budget liquidity and tracking accounts.

### 2.1 Ready to Assign from Cash Only

Ready to Assign (RTA) is computed from on‑budget Cash and Checking accounts only. Income transactions placed directly into a cash account increase RTA and provide money for allocation to envelopes. Non‑cash accounts never directly increase or decrease RTA; their effect on the budget is always mediated through categories.

When budgeted spending occurs using a credit card:

- The credit account’s balance becomes more negative (liability increases).
- The category’s available funds decrease based on the transaction amount.
- RTA is unaffected, because it was reduced at allocation time when envelopes were funded from cash.

Payments from Cash accounts to Credit and Borrowing accounts are modeled as categorized transfers:

- A payment category (for example, “Payment: House Credit Card”) receives funding on the Budget page.
- When the user pays the card, a transfer from Cash to the Credit account is paired with a movement out of the payment category.
- This does not alter RTA directly; it consumes previously allocated funds.

### 2.2 Accessible Assets and Investment Transfers

Accessible Assets are always off‑budget tracking accounts. They do not participate in RTA. However, movements between Cash and Accessible Assets must follow budgeting principles:

- Cash → Accessible Asset:
  - A categorized outflow from a Cash account (for example, to “Short‑Term Savings”) reduces a budget envelope and RTA.
  - An inflow into the Accessible Asset account is categorized as an “Account transfer” and affects balances only.
- Accessible Asset → Cash:
  - An inflow into a Cash account must be categorized. By default, it is treated as income to RTA (for example, “Available to Budget”), but the user may assign it to any category (for example, reimbursements).
  - The corresponding outflow from the Accessible Asset account is categorized as an “Account transfer”.

Investment transfers are modeled identically:

- Cash → Investments (contribution):
  - A categorized outflow from a Cash account (for example, “Brokerage Contributions”) reduces envelopes and RTA.
  - An inflow to the Investment account is categorized as an “Account transfer”.
- Investments → Cash (decumulation):
  - An inflow to a Cash account is categorized by the user (default “Investment Income” or “Available to Budget”; alternatively a return of contributions or reimbursement).
  - The Investment account sees a matching outflow categorized as an “Account transfer”.

The user separately updates investment holdings and prices; market movements do not create ledger transactions.

### 2.3 Long‑Term Borrowing and Loan Tracking

Long‑term borrowing accounts (mortgages, student loans, etc.) are modeled as tracking liabilities. The loan’s balance used in net worth comes from the ledger, not from a pure amortization model:

- Users budget into dedicated payment categories (for example, “Payment: Main Mortgage”) or broader debt categories (for example, “Student Loans”) on the Budget page.
- A real payment is represented as a categorized transfer:
  - Cash account outflow categorized to a payment or debt category (budget is reduced).
  - Matching inflow to the loan account categorized as an “Account transfer” (liability balance is reduced).
- Interest, fees, and escrow drift are reconciled by occasionally updating the loan account balance to match the external statement. This reconciliation may insert a corrective transaction that increases the liability to reflect accrued interest or fees.

Amortization parameters (initial principal, rate, schedule, escrow configuration) are stored in the loan’s SCD‑2 configuration and used for forecasting and analytics, but they do not directly override the ledger‑derived loan balance.


## 3. Account Data Contracts and Temporal Modeling (SCD‑2)


Each account has:

- A canonical row in the `accounts` table capturing identity, current balance, lifecycle state (`is_active`), and minimal metadata (name, account_type).
- A per‑class SCD‑2 configuration table (`cash_account_details`, `credit_account_details`, `accessible_asset_details`, `investment_account_details`, `loan_account_details`, `tangible_asset_details`) that stores fields unique to that class and versions them over time using validity ranges (`valid_from`, `valid_to`) and an `is_active` flag.

Updates to interest rates, terms, and valuations generate new SCD‑2 versions; historical rows remain immutable.

The following sections summarize the fields for each account type.

### A. Cash and Checking

| Field              | Description                                           | Temporal |
|--------------------|-------------------------------------------------------|----------|
| institution_name   | Name of the banking institution                       | No       |
| account_name       | User-defined nickname                                 | No       |
| interest_rate_apy  | Current annual percentage yield                       | Yes      |

### B. Credit and Borrowing (Cards and Lines)

| Field               | Description                                           | Temporal |
|---------------------|-------------------------------------------------------|----------|
| institution_name    | Name of the banking institution                       | No       |
| account_name        | User-defined nickname                                 | No       |
| card_type           | Card network type (e.g., Visa, Mastercard)           | No       |
| apr                 | Purchase APR                                          | Yes      |
| cash_advance_apr    | Cash advance APR                                      | Yes      |

### C. Accessible Assets

Accessible Assets represent short‑term deposits and cash equivalents that are kept off‑budget but still contribute to net worth.

| Field                    | Description                                     | Temporal |
|--------------------------|-------------------------------------------------|----------|
| institution_name         | Name of the bank or provider                    | No       |
| account_name             | User-defined nickname                           | No       |
| term_end_date            | Maturity or term end date, if applicable        | Yes      |
| nominal_rate_apy         | Stated annual percentage yield                  | Yes      |
| early_withdrawal_penalty | Whether early withdrawal incurs a penalty       | Yes      |

### D. Investments (Brokerage)

| Field               | Description                                           | Temporal |
|---------------------|-------------------------------------------------------|----------|
| institution_name    | Name of the brokerage                                 | No       |
| account_name        | User-defined nickname                                 | No       |
| self_directed       | Whether the account is user-managed                   | No       |
| account_type        | IRA, 401k, taxable brokerage, etc.                    | No       |
| risk_free_sweep_rate| Current interest rate of the sweep fund               | Yes      |

### E. Long‑Term Borrowing

| Field                   | Description                                      | Temporal |
|-------------------------|--------------------------------------------------|----------|
| institution_name        | Lender name                                      | No       |
| loan_name               | User-defined nickname                            | No       |
| initial_principal       | Original loan amount                             | No       |
| current_rate            | Current loan interest rate                       | Yes      |
| mortgage_escrow_config  | Breakdown of tax and insurance escrow            | Yes      |

### F. Tangibles (Tracking Accounts)

Tangibles are physical assets (for example, vehicles, art, or collectibles) whose contribution to net worth comes from user‑maintained fair values rather than cash flows.

| Field             | Description                                            | Temporal |
|-------------------|--------------------------------------------------------|----------|
| asset_name        | User-defined asset name                                | No       |
| acquisition_cost  | Original purchase price                                | No       |
| current_fair_value| Updated fair value for net worth reporting             | Yes      |


## 4. Account Lifecycle and Retirement


Lifecycle is governed by the canonical `accounts` table. An account is considered active if `accounts.is_active = TRUE`. Per‑class SCD‑2 tables rely on validity ranges rather than their own lifecycle flags.

Financial accounts must satisfy a Zero‑Balance Constraint before being retired. If the balance is non-zero, the user must transfer the remainder to an active account or record an explicit payoff transaction on the ledger. Once the balance is zero, the system marks the account as inactive by setting `accounts.is_active = FALSE`. Historical SCD‑2 rows remain unchanged.

Tangible assets do not hold funds but have a `current_fair_value`. To retire a tangible asset:

- The user records a sale inflow in the relevant Cash account (and any associated tax or fee expenses) on the ledger.
- The tangible’s SCD‑2 record is updated so that `current_fair_value` is set to zero as of the retirement date.
- The corresponding account in `accounts` is marked inactive.

Historical visibility rules ensure retired accounts appear in reports for periods in which they were active. UI views that show “current accounts” filter for `accounts.is_active = TRUE`, while historical reports query the account’s state as of the reporting date, restoring correct past visibility.



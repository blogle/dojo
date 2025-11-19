# Budgeting and Transactions

This document details the functionality, data model, and flow for the day-to-day operational core of the application: managing financial transactions and implementing the envelope budgeting system.

The primary goal of this domain is to provide a fast, reliable, and fully auditable interface for recording financial activity while strictly adhering to the principles of zero-based, envelope budgeting. This requires ensuring all income is assigned to a specific budget category (envelope) before it is spent and maintaining complete historical integrity of all financial entries.

## Core Entities and Data Model

The domain manages the accounts, budget categories, transactions, and the reconciliation history. It is responsible for the Ready to Assign (RTA) computation and all envelope movements.

The `Accounts` entity tracks the current state of all financial accounts, whether they are checking, savings, credit cards, or liabilities like mortgages. It stores the display name, an `account_type` flag (`asset` or `liability`), and the application's calculated current balance. Accounts are considered active when `is_active = TRUE` and do not hold reconciliation status; lifecycle and reconciliation are handled through separate logs.

The `BudgetCategories` entity defines the available envelopes and tracks their current status on a monthly basis. For each month, it records the total funds that have been allocated to the envelope, the total spending or activity charged to it, and calculates the resulting available balance. Budget categories are also used to model liability payment envelopes (for example, “Payment: House Credit Card” or generic “Student Loans”).

The `BudgetAllocations` ledger captures every movement of Ready-to-Assign between envelopes. Each row records the allocation date, the normalized `month_start`, optional source category, mandatory destination category, memo, and amount. The API exposes these rows via `GET /api/budget/allocations`, allowing the SPA to render an auditable ledger and month-to-date inflow/Ready-to-Assign summaries while the POST endpoint enforces RTA guard rails and verifies the source envelope has sufficient available funds before reassigning dollars.

The `Transactions` entity serves as the core, system-versioned table. Every transaction and every subsequent edit or correction to that transaction is permanently preserved. A conceptual identifier remains constant across all versions of the same real-world transaction. Each version is time-stamped upon creation and includes a flag to mark which version is currently active. Furthermore, all changes are audited by storing the identifier of the user who created or last modified that specific version. The transaction itself records the real date it occurred, the amount, the associated account, the assigned budget category, and a descriptive memo. Opening balances are represented as normal transactions assigned to a dedicated “Opening Balance” category, with a synthetic counterparty account.

The `Reconciliations` entity is a separate log that serves as the validated "commit" history for an account. It records the state of an account at the time of validation, including the account identifier, the time the reconciliation was performed, the application's calculated balance at that moment, and the confirmed balance as seen in the external source (e.g., the bank statement).

## Key Transactional Flows

### New Transaction Entry

When a user submits one or more new transactions, the system executes a single, atomic database transaction. DuckDB's architecture allows for this concurrent write from a single application process without requiring complex staging tables. A unique conceptual transaction identifier is generated, and a new row is inserted into the Transactions table, marked as active. Following this, the BudgetCategories entity is updated to adjust allocations or activity for the relevant envelopes, and the Accounts entity is updated to reflect the new current balance.

Ready to Assign is derived from on-budget Cash and Checking accounts only. Income transactions posted into cash with income or inflow-style categories increase RTA; budget allocations move RTA into envelopes; spending transactions (including credit card spending against funded categories) reduce envelope availability without changing RTA directly.

### Transfers, Contributions, and Liability Payments

The system represents categorized transfers and contributions as pairs of transactions:

- Cash → Investments or Accessible Assets:
  - A categorized outflow from a Cash account (for example, contributions or short-term savings) reduces envelope balances and RTA.
  - A matching inflow to the Investment or Accessible Asset account is categorized as an account transfer and affects balances only.
- Investments or Accessible Assets → Cash:
  - An inflow to a Cash account is categorized by the user. By default, this is treated as income to RTA, but it may instead be a reimbursement or correction assigned to a specific envelope.
  - A matching outflow from the Investment or Accessible Asset account is categorized as an account transfer.

Liability payments follow the same pattern:

- A cash outflow is categorized to a liability payment envelope (for example, “Payment: House Credit Card”) or a generic debt envelope.
- A matching inflow is posted to the liability account (credit card or long-term loan) as an account transfer, reducing the liability balance.

This double-entry approach ensures that every movement affecting net worth and budgets is explicit in the ledger while keeping RTA solely driven by cash-side inflows and allocations.

### Reconciliation and Data Correction

Reconciliation is formalized as a commit process. When a user confirms that an account balance in the application matches the bank's balance, a Reconciliation record is created. This record time-stamps the account's state, marking a definitive point in history where the application's records are known to be correct relative to the external source of truth.

When a subsequent data discrepancy is discovered, the application leverages the Reconciliations log to isolate the error. It retrieves the date of the last successful reconciliation for the affected account. The application then executes a specialized query against the temporal Transactions table to identify all records that were created or modified since that last known good commit point. By isolating this small set of transactions, the user can review only the recent "diff" against their bank statement, simplifying the process of finding and correcting the erroneous transaction.

Correction of a data entry error still adheres to the robust temporal data pattern. Instead of overwriting data, the existing active version of the transaction is logically closed by setting its active flag to false. A completely new row is then inserted with the corrected data, a new system time-stamp, and is marked as the new active version. Following this, the application recalculates the balances of all affected Budget Categories and Accounts based on the change, ensuring the application's current state remains accurate.

Balance corrections are treated as exceptional. When the only way to reconcile a ledger with an external statement is a direct adjustment (for example, a bank-side fee that was not entered), the user records an explicit “Adjustment” transaction type through a guided reconciliation flow. The UI adds friction and clear audit tagging to discourage casual use in favor of correcting the underlying transactions wherever possible.

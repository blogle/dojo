# Budgeting and Transactions

This document details the functionality, data model, and flow for the day-to-day operational core of the application: managing financial transactions and implementing the envelope budgeting system.

The primary goal of this domain is to provide a fast, reliable, and fully auditable interface for recording financial activity while strictly adhering to the principles of zero-based, envelope budgeting. This requires ensuring all income is assigned to a specific budget category (envelope) before it is spent and maintaining complete historical integrity of all financial entries.

## Core Entities and Data Model

The domain manages the accounts, budget categories, transactions, and the new reconciliation history.

The `Accounts` entity tracks the current, active state of all financial accounts, whether they are checking, savings, credit cards, or liabilities like mortgages. It stores the display name, the account type (asset or liability), and the application's calculated current balance. This entity no longer holds reconciliation status, relying instead on the separate log.

The `BudgetCategories` entity defines the available envelopes and tracks their current status on a monthly basis. For each month, it records the total funds that have been allocated to the envelope, the total spending or activity charged to it, and calculates the resulting available balance.

The `Transactions` entity serves as the core, system-versioned table. Every transaction and every subsequent edit or correction to that transaction is permanently preserved. A conceptual identifier remains constant across all versions of the same real-world transaction. Each version is time-stamped upon creation and includes a flag to mark which version is currently active. Furthermore, all changes are audited by storing the identifier of the user who created or last modified that specific version. The transaction itself records the real date it occurred, the amount, the associated account, the assigned budget category, and a descriptive memo.

The `Reconciliations` entity is a new, separate log that serves as the validated "commit" history for an account. It records the state of an account at the time of validation, including the account identifier, the time the reconciliation was performed, the application's calculated balance at that moment, and the confirmed balance as seen in the external source (e.g., the bank statement).

## Key Transactional Flows

### New Transaction Entry

When a user submits one or more new transactions, the system executes a single, atomic database transaction. DuckDB's architecture allows for this concurrent write from a single application process without requiring complex staging tables. A unique conceptual transaction identifier is generated, and a new row is inserted into the Transactions table, marked as active. Following this, the BudgetCategories entity is updated to immediately increase the activity charged to the relevant envelope, and the Accounts entity is updated to reflect the new current balance.

### Reconciliation and Data Correction

Reconciliation is formalized as a commit process. When a user confirms that an account balance in the application matches the bank's balance, a Reconciliation record is created. This record time-stamps the account's state, marking a definitive point in history where the application's records are known to be correct relative to the external source of truth.

When a subsequent data discrepancy is discovered, the application leverages the Reconciliations log to isolate the error. It retrieves the date of the last successful reconciliation for the affected account. The application then executes a specialized query against the temporal Transactions table to identify all records that were created or modified since that last known good commit point. By isolating this small set of transactions, the user can review only the recent "diff" against their bank statement, simplifying the process of finding and correcting the erroneous transaction.

Correction of a data entry error still adheres to the robust temporal data pattern. Instead of overwriting data, the existing active version of the transaction is logically closed by setting its active flag to false. A completely new row is then inserted with the corrected data, a new system time-stamp, and is marked as the new active version. Following this, the application recalculates the balances of all affected Budget Categories and Accounts based on the change, ensuring the application's current state remains accurate.

# Dojo Personal Finance App – Overview

## Mission

Dojo is a privacy‑focused web application that lets a household of two manage their finances with the envelope‑budgeting workflow of the Aspire Budget Google Sheet. It delivers the same calculations and reports, adds real‑time collaboration and automatic bank imports, and scales smoothly to years of data.

## Actors

* **Primary user** – initiates the budget, manages categories, and imports historical data.
* **Partner user** – collaborates in real time, adds transactions, and reviews reports.
* **Bank‑sync service (Plaid)** – supplies cleared and pending transactions plus account balances.
* **Dojo system** – backend written in Rust (Axum + Tokio) with Postgres/DuckDB storage, frontend TypeScript/React, real‑time updates via WebSocket.

## Glossary

* **Envelope / Category** – a virtual “bucket” of money allocated for a specific purpose (e.g. Groceries).
* **Category Group** – a logical grouping of related categories (e.g. Food).
* **Available to budget** – funds not yet assigned to any envelope.
* **Transaction** – a dated inflow or outflow that affects an account balance and a category balance.
* **Account** – a financial store of value such as Checking, Savings, or a Credit Card.
* **Transfer (Account)** – a money movement between two accounts; does not affect category totals.
* **Transfer (Category)** – a money movement between two categories; adjusts budget allocations.
* **Goal amount** – a target balance for a category that accumulates over time.
* **Monthly amount** – the desired starting balance for a category at the beginning of each month.
* **Pending transaction** – a bank‑authorized charge that has not yet settled.
* **Reconciliation** – the act of matching Dojo’s account balances to bank statements.
* **Report** – a generated view (dashboard, spending, trend, income‑vs‑expense) derived from transactions.

---

Everything else lives in the detailed requirements documents.


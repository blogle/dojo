# Account Onboarding Field Matrix

This note is the compact field matrix for a shared account-creation wizard that must work both in normal Dojo account onboarding and in the Aspire net worth handover flow.

## Shared rules

- Money persisted in Dojo must remain integer minor units; analytics may derive float-based metrics later.
- Opening values should be created via `opening_balance` / `balance_adjustment` / measurement records, never by setting `accounts.current_balance_minor` directly.
- Net worth must come from exactly one source at a time per real-world balance: ledger, investment reconcile state, tangible valuation, or loan principal checkpoint.
- Migration should default to Aspire-derived values when confidence is high and only ask the user for fields that unlock future planning or prevent ambiguity.
- Persisted account semantics should not rely on weak name-based heuristics. If Aspire does not provide a field with high confidence, the wizard should ask the user.

## Universal fields for every account

| Field | Why it matters | Aspire source | User input? |
| --- | --- | --- | --- |
| `name` | Primary label in ledger, net worth, and wizard review | account/category labels | only to rename/split |
| `institution_name` | UX, grouping, future import/reconcile hints | not exported | usually yes |
| `account_class` + `account_type` + `account_role` | Drives accounting semantics, validations, and detail forms | partly inferred from `cfg_Accounts`, `cfg_Cards`, and net worth asset/debt lists | confirm unless source is explicit |
| `opened_on` / cutover date | Needed for charts, amortization start points, and as-of correctness | cutover can default from latest Aspire mark/statement month | often yes |
| opening/current signed value | Seeds ledger/valuation state at handoff | latest ledger balance or latest net worth mark | yes only if Aspire is incomplete |
| `is_active` | preserves historical entities without deleting them | hidden/retired lists | usually inferred |

## Account-type matrix

### Cash / credit / accessible

These are mostly schema-complete today. Aspire can already supply the account name, active/retired state, and current balance from ledger history.

| Fields to capture | Enables | Aspire source | Notes |
| --- | --- | --- | --- |
| balance at cutover | correct ledger-derived net worth | transaction history | required |
| `interest_rate_apy` (cash/accessible) | yield reporting, future forecasting | none | optional |
| `term_end_date`, `early_withdrawal_penalty` (accessible) | CD maturity reminders, liquidity planning | none | optional but useful |
| `apr`, `cash_advance_apr`, `card_type` (credit) | debt cost context, payoff prioritization | `cfg_Cards` only tells us it is a card | APRs require user input |

### Loan / mortgage

Current schema stores `initial_principal_minor`, `interest_rate_apy`, and free-text `mortgage_escrow_details`. That is enough for metadata display, but not enough for the payoff/planning feature set described in the RFC.

| Fields to capture | Enables | Aspire source | Recommendation |
| --- | --- | --- | --- |
| current principal at cutover | net worth liability value | latest net worth mark | required |
| `initial_principal_minor` / original principal | principal-paid-to-date, lifetime interest math | sometimes inferable from oldest mark, but not reliable | ask user |
| `interest_rate_apy` | amortization math, overpayment scenarios | not exported | ask user |
| loan start date | payoff timeline, term progress | not exported | ask user if planning features matter |
| original term or term end date | remaining schedule, payoff forecast | not exported | add to wizard/schema |
| tracking mode (`statement_principal` vs `split_payments`) | determines reconcile UX and whether principal moves on payment dates | not exported | add explicit choice; default statement principal |
| linked payment category + linked source account(s) | lightweight payment rollups and inferred principal/interest estimates | can sometimes be guessed from transaction category/account names | optional but high value |
| escrow/tax/insurance note | explains mortgage payment composition | Aspire note field may hold hints, but no structure | optional free text |

Minimal migration stance: prefill current principal from Aspire, ask only for rate plus either `(start date + term)` or `term end date`, and treat original principal as recommended for better analytics.

### Tangible asset

Current runtime needs both account metadata and a `tangible_assets` valuation row. The wizard should treat tangibles as valuation-driven, not ledger-balance-driven.

| Fields to capture | Enables | Aspire source | Recommendation |
| --- | --- | --- | --- |
| appraised/current fair value at cutover | net worth contribution | latest net worth mark | required |
| `asset_name` | readable detail page + valuation history | category label often sufficient | prefill from Aspire |
| `acquisition_cost_minor` | appreciation/depreciation since purchase | not exported | recommended |
| acquisition date / start date | ownership-period return and CAGR | not exported | add to wizard/schema |
| valuation source | confidence/provenance, stale-value UX | Aspire notes may hint, not structured | recommended |
| valuation note | context for estimate/appraisal | `ntw_Notes` | prefill when present |
| appraisal/valuation date | history accuracy and staleness | mark date | required, usually inferred from cutover |

Minimal migration stance: prefill name, current value, valuation date, and note from Aspire marks; ask user for acquisition cost only when they want appreciation analytics.

### Investment account

This is the most developed downstream path today. Current schema and services already use statement cash, holdings, `ledger_baseline_minor`, `tax_classification`, and `is_self_directed`.

| Fields to capture | Enables | Aspire source | Recommendation |
| --- | --- | --- | --- |
| cutover date | reconcile baseline and historical handoff | latest net worth mark date | required |
| statement cash (`uninvested_cash_minor`) | correct NAV after cutover | not exported | ask user |
| holdings: ticker + quantity | portfolio composition, NAV, history | not exported | ask user |
| holdings cost basis | gain attribution, future tax-aware rebalancing | not exported | strongly recommended |
| `tax_classification` | account-level tax treatment for future advisory logic | not exported | ask user |
| `is_self_directed` | UX defaults and future advisory posture | not exported | optional ask |
| `institution_name` | broker context | not exported | optional |
| sweep/risk-free rate | cash drag / idle cash analytics | not exported | optional |

Minimal migration stance: Aspire only gives the aggregate account value. The user must supply statement cash and holdings to unlock performance, composition, and future rebalancing. If they skip holdings, Dojo can preserve net worth continuity but not portfolio analytics.

## What Aspire can reliably prefill vs what it cannot

### Reliable from Aspire

- Budget account names, credit-vs-noncredit distinction, active/retired hints.
- Ledger-derived balances for transaction-backed accounts.
- Net worth category names, asset/debt sign, latest mark value, latest mark date, and optional free-text note.
- Duplicate candidates between ledger accounts and net worth categories.

### Do not infer silently

- Net worth destination class from account/category name alone.
- Investment tax classification from account name.
- Self-directed vs managed posture.
- Loan payment category/source linkage from transaction labels alone.

These can be suggested in the UI as non-binding defaults, but they should never be persisted without an explicit user confirmation.

### Must come from the user for downstream goals

- APR / interest rate fields.
- Loan term, start date, and payment-tracking mode.
- Investment statement cash, holdings, and cost basis.
- Tangible acquisition cost and any ownership-date metadata.
- Any tax-sensitive attributes needed for future tax-aware rebalancing.

## Wizard design implications

- Use one shared wizard shell with a tight four-step order: select account type -> static details -> dynamic details/current state -> review.
- Treat step 2 as slow-changing identity + structural fields (`name`, institution, tax status, original principal, acquisition cost, term metadata).
- Treat step 3 as as-of state at creation/cutover (opening balance, statement principal, holdings, appraisal, valuation date).
- During Aspire migration, prefill all high-confidence fields and visibly mark any field that still needs user confirmation.
- Keep planning-only fields hidden unless the selected account type benefits from them, but do not replace them with heuristics.
- Add schema support before finalizing the wizard for: loan term/start-date/mode/linkage, tangible acquisition date + valuation provenance surfaced end-to-end, and clearer investment cost-basis capture.

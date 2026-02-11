# Aspire Migration Wizard Alignment (UI + Flow Spec)

This document defines the migration wizard flow and UI elements used by the clickable prototype (`aspire_onboarding_mockup.html`) and the later in-app implementation.

Primary references:

- `docs/rfcs/aspire-migration-and-account-semantics.md`
- `docs/aspire/*.md`

This file intentionally stays explicit and step-by-step so implementation can follow it without guessing.

## Scope

- In scope: wizard steps, UI components, value definitions, validation/gating behavior, and user-facing copy direction.
- Out of scope: backend endpoint design and DB schema details.

## Non-negotiable UX constraints

1. Wizard uses persistent footer stepper buttons (`Back` / `Continue`, then `Finish` on preview).
2. Step progress is driven by footer stepper only.
3. If a step cannot progress, `Continue` stays available but shows user-facing validation error.
4. Header shows progress + validation badge (`Passing`, `Needs Attention`, `Blocked`) with tooltip.
5. During onboarding, normal app navigation links are hidden; header context is `Onboarding`.

## Persistence strategy (mockup and implementation)

- Mockup: local storage only.
- Implementation default: local storage is sufficient for single-browser resumability and should be first-class.
- Implementation optional enhancement: backend migration sessions for cross-browser/device recovery.
- Do not require cross-browser persistence to ship MVP.

## User-facing copy guardrail

Avoid deep accounting implementation terms in wizard body copy.

- Good: “Set starting values”, “Resolve unmatched transfers”, “Link overlapping accounts”.
- Avoid in-step copy: “ledger baselines”, “fabricated cashflows”, “transactional idempotency”, etc.

Technical specifics still belong in tooltips, docs, and validation logic.

## Flow definition

## Step 1. Welcome to Dojo

Two cards:

- `Start Fresh`
  - Action: exits migration path and continues standard empty onboarding.
- `Migrate from Aspire`
  - Action: starts migration flow at step 2.

## Step 2. Connect Google Drive

UI elements:

- Title: `Connect Google Drive`
- Subtext describing read-only permission scope.
- CTA button: `Connect Google Account`

Behavior:

- Click initiates OAuth flow.

## Step 3. Which Sheet Are We Using?

UI elements:

- Title: `Which sheet are we using?`
- One text input for spreadsheet URL.
- Optional positive validation indicator when URL pattern is valid.

Validation:

- `Continue` checks URL validity.
- On invalid URL, remain on step 3 and show inline user-facing error.

Note:

- No extra progress CTA on this page; progression is via footer stepper only.

## Transition. Extraction spinner (between steps 3 and 4)

UI elements:

- Spinner
- Rotating progress text indicating extraction phases

Copy should remain informational and user-friendly, not raw logs.

## Step 4. Extraction Overview

Title: `We found your data`

Summary cards:

- Accounts count
- Transactions count
- Net worth marks count
- History span

## Step 5. Budget Accounts

Title: `Budget accounts`

Table columns:

1. `Account Name`
2. `Type`
3. `Status`
4. `Settled Balance`
5. `Pending Balance`

Definitions:

- `Type`: one of on-budget account types represented from Aspire mapping.
- `Status`: `Active` or `Retired`.
- `Settled Balance`: sum of cleared transactions for account.
- `Pending Balance`: sum of pending transactions for account.

## Step 6. Budget Categories

Title: `Budget categories`

### Active budgets table

Columns:

1. `Category`
2. `Group`
3. `Config`
4. `Configured Budget`
5. `Available`
6. `Edit`

Definitions:

- `Configured Budget`: target plan amount for cadence (not “amount budgeted this month”).
- `Available`: current envelope remainder.
- `Available` tooltip shows:
  - `Activity`: current-month categorized spending/income impact.
  - `Budgeted`: current-month assigned amount.

Edit behavior:

- Pencil icon opens category editor.
- Editable fields: category name, group, budget configuration.
- Supported configs:
  - recurring (weekly/monthly/quarterly/annually + amount)
  - target date (date + target amount)

### Retired budgets table

Columns:

1. `Category`
2. `Configured Budget (Last)`
3. `Available Balance`

Behavior:

- Keep this advisory and low-friction during onboarding.
- Non-zero retired balances are flagged for post-onboarding follow-up.

Not listed on this step:

- Dojo system categories (for example, Ready to Assign, transfer markers, opening/balance adjustment markers)
- Auto-generated credit card payment categories

## Step 7. Transfer Exceptions

Title: `Transfer exceptions`

Purpose:

- Resolve orphan transfer legs that could not be deterministically paired.

Table columns:

1. select checkbox
2. `Date`
3. `Account`
4. `Category`
5. `Memo`
6. `Amount`
7. `State`

Allowed actions:

- Inline edit row (category/memo) to resolve as non-transfer.
- Select exactly two unresolved rows -> `Link as Transfer` action bar.
- `Undo` is available for resolved rows:
  - undo linked pair restores both rows to unresolved
  - undo edited row restores original unresolved values

Progress rule:

- Must reach zero unresolved exceptions before `Finish`.

## Step 8. Link Overlapping Accounts

Purpose:

- Pair budget accounts with matching Aspire net worth entries to avoid duplicate counting.

Table columns:

1. `Budget Account`
2. `Aspire Net Worth Account`
3. `Reason`
4. `Strategy`

Strategy options:

- `Merge (recommended)`
- `Keep Legacy Marks Only`

Naming options considered for this step (if we rename before implementation freeze):

1. `Link Overlapping Accounts` (current)
2. `Resolve Overlapping Accounts`
3. `Unify Shared Accounts`
4. `Merge Duplicate Accounts`
5. `Account Overlap Review`

## Step 9. Net Worth Accounts

Title: `Net worth accounts`

Purpose:

- For remaining net worth entities (not merged in step 8), create destination Dojo accounts for forward tracking.

Top summary banner fields:

1. `Last Reported Net Worth`
   - Definition: net worth from Aspire marks at migration time.
2. `Derived Net Worth`
   - Definition: net worth implied by mappings + cutover account setup.
3. `Difference`
   - Definition: derived minus last reported.

Entity accordion/card:

- Header shows Aspire entity name + source balance + match badge (`Matched` / `Unbalanced`).
- Body lists destination accounts created so far.
- CTA: `+ Add Destination Account`.

Destination account modal requirements:

- Reuse account onboarding wizard style.
- Supports all account classes in scope.
- For investment destinations, include positions/lots entry UI:
  - ticker/symbol
  - quantity
  - current price
  - optional cost basis
- Show holdings subtotal and total account starting value (cash + holdings).

Financial baseline requirement:

- Investment cutover must establish a non-zero starting capital baseline where appropriate (cash and/or holdings) so returns are not undefined/infinite from an implicit zero base.
- When balances differ from prior Aspire marks, difference is shown as drift/warning, not hidden.

## Step 10. Preview Migration

Title: `Preview migration`

UI elements:

- Chart comparing Aspire legacy marks history and Dojo-derived history.
- Validation cards with pass/warn/block states.
- Footer CTA text: `Finish`.

## Transition. Apply spinner

After `Finish`:

- Spinner with friendly phase text while migration is applied.
- No debug traces in user copy.

## Step 11. Migration Complete

UI elements:

- Title: `Migration Complete`
- CTA: `Go to Dashboard`

Post-onboarding expectation:

- Dashboard includes a follow-up tasks section (for example, reconcile reminders and retired-category cleanup).

## Required blockers before apply

These are the minimum sufficient/necessary gating checks before final apply:

1. No unresolved transfer exceptions.
2. No unresolved duplicate mapping collisions.
3. Any category included in Dojo-derived net worth has explicit asset/debt classification.
4. Budget parity check passes, or user explicitly acknowledges documented semantic differences.
5. Apply runs as one all-or-nothing operation.

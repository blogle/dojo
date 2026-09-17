# Account Creation Wizard Redesign Plan

This plan details the redesign of the account creation wizard to support both standard onboarding and Aspire migration with a unified, tight, and low-overhead flow. The design prioritizes accuracy over weak heuristics and adheres to the project's minimalist earth-tone style guide.

## Goals

1.  **Unified Flow:** A single wizard component for both new account creation and Aspire migration handover.
2.  **Explicit Accuracy:** Avoid silent inferences. Require user confirmation for fields not strictly defined by the source (Aspire).
3.  **Comprehensive Modeling:** Capture necessary fields for downstream features (loan payoffs, tangible appreciation, investment analysis) without clutter.
4.  **Minimalist UX:** standard components, no "cute" interactions, earth tones.

## Wizard Steps

The wizard will follow a strict four-step linear process:

1.  **Select Account Type**
2.  **Static Details** (Identity, structure, metadata)
3.  **Starting State** (Balances, valuations, holdings as of cutover/creation date)
4.  **Review**

### Step 1: Select Account Type

User selects one of the high-level account classes.
*   **Options:**
    *   **Budget Account:** Cash (Checking/Savings), Credit Card.
    *   **Loan / Mortgage:** Liability with amortization/payoff tracking.
    *   **Investment:** Brokerage, Retirement (IRA/401k), HSA.
    *   **Tangible Asset:** Vehicle, Real Estate, Art/Collectibles.
    *   **Accessible Asset:** CDs, Locked Savings (tracking only).

### Step 2: Static Details

Fields that define *what* the account is. These rarely change.

#### All Accounts
*   **Account Name** (Required)
*   **Institution** (Optional but recommended)
*   **Account Role** (Inferred from type, but strictly: Budget vs. Tracking. Loans/Investments/Tangibles are always Tracking. Cash/Credit defaults to Budget.)

#### Specific Fields by Type

*   **Credit Card:**
    *   `apr` (%, Optional - for payoff planning)
    *   `cash_advance_apr` (%, Optional)
    *   `card_type` (Select: Visa, MC, Amex, etc. - Optional)

*   **Loan / Mortgage:**
    *   `initial_principal` (Money, Optional - for "paid off so far" stats)
    *   `interest_rate` (%, Required for amortization)
    *   `start_date` (Date, Optional - for accurate timeline)
    *   `term_months` (Int, Optional - e.g., 360 for 30yr mortgage)
    *   `payment_mode` (Select: "Statement Principal" (default) vs "Split Payments")

*   **Investment:**
    *   `tax_classification` (Select: Taxable, Trad IRA, Roth IRA, 401k, etc. - Required)
    *   `is_self_directed` (Checkbox - Optional)
    *   `sweep_rate` (%, Optional - for cash drag analysis)

*   **Tangible Asset:**
    *   `acquisition_date` (Date, Optional - for ownership duration)
    *   `acquisition_cost` (Money, Optional - for appreciation/depreciation stats)
    *   `notes` (Text, Optional - for VIN, address, etc.)

*   **Accessible (CDs):**
    *   `apy` (%, Optional)
    *   `term_end_date` (Date, Optional)
    *   `early_withdrawal_penalty` (Checkbox)

### Step 3: Starting State

Fields that define the account's value *at a specific point in time*.

#### All Accounts
*   **As-Of Date** (Date, Required. Defaults to Today or Migration Cutover Date)

#### Specific Fields by Type

*   **Cash / Credit / Accessible:**
    *   `cleared_balance` (Money, Required. Signed: positive for asset, negative for debt.)

*   **Loan:**
    *   `current_principal` (Money, Required. Positive value representing the debt magnitude.)

*   **Tangible:**
    *   `current_fair_value` (Money, Required.)
    *   `valuation_source` (Text, Optional - e.g., "KBB", "Zillow", "Appraisal")

*   **Investment:**
    *   `uninvested_cash` (Money, Required.)
    *   **Holdings List:** (Repeater field)
        *   `ticker` (Text)
        *   `quantity` (Number)
        *   `cost_basis_per_share` (Money, Optional but recommended)
        *   *Note: Total value is derived (Cash + (Qty * Market Price)).*

### Step 4: Review

*   Read-only summary of all entered data.
*   "Create Account" button.
*   *Migration Context:* Shows diff against Aspire reported value if applicable.

## Backend Schema Updates

To support the "Planning" features, we need to extend the schema.

### 1. Loans (`loan_account_details`)
*   Add `loan_start_date` (DATE, nullable)
*   Add `original_term_months` (INTEGER, nullable)
*   Add `payment_mode` (TEXT, check constraint: 'statement' or 'split', default 'statement')

### 2. Tangibles (`tangible_asset_details`)
*   Add `acquisition_date` (DATE, nullable)
*   *Note: `acquisition_cost_minor` already exists in `tangible_assets` table but maybe should be in details for the static record? The `tangible_assets` table is SCD2 for valuation. `tangible_asset_details` is for the account metadata. We should probably mirror `acquisition_cost` in details or strictly use the `tangible_assets` SCD2 table. RFC says `tangible_assets` is for valuation. Let's add `acquisition_date` to `tangible_asset_details`.*

### 3. Investment (`investment_account_details`)
*   Existing fields `risk_free_sweep_rate`, `tax_classification` (needs migration?), `is_self_directed` (needs migration?) seem to be in frontend but need verification in DB.
*   *Check:* `tax_classification` and `is_self_directed` are likely missing from `investment_account_details` based on previous greps.

## Implementation Steps

1.  **DB Migrations:** Create SQL migrations for the new fields in `loan_account_details`, `tangible_asset_details`, and `investment_account_details`.
2.  **Backend API:** Update `AccountCreateRequest` and `AccountUpdateRequest` Pydantic models and the `AccountService` to handle these new fields.
3.  **Frontend Components:**
    *   Build `WizardStepType.vue`
    *   Build `WizardStepStatic.vue` (dynamic form based on type)
    *   Build `WizardStepStartingState.vue` (dynamic form based on type)
    *   Build `WizardStepReview.vue`
    *   Orchestrate in `AccountWizard.vue` (replacing the modal logic in `AccountsPage.vue`).
4.  **Aspire Integration:** Update `OnboardingPage.vue` to invoke this new Wizard with pre-filled props when "Mapping" accounts.


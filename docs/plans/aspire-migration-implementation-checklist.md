# Aspire Migration Implementation Checklist

Purpose: execution checklist + scratch space for implementing the approved Aspire migration wizard.

Primary references:

- `docs/rfcs/aspire-migration-and-account-semantics.md`
- `migration_wizard_alignment.md`
- `aspire_onboarding_mockup.html`
- `docs/plans/aspire-migration-codex-kickoff-prompt.md`

## Locked decisions (must remain true)

- [x] Transfer exceptions allow only:
  - link exactly two unresolved rows as transfer
  - resolve single orphan to `opening_balance` or `balance_adjustment`
- [x] No arbitrary budget-category mapping for transfer exceptions
- [x] Transfer resolution supports undo
- [x] `v_BreakSymbol` rows never surface as transfer exceptions
- [x] localStorage-first wizard UX persistence
- [x] Investment cutover uses opening baseline + reconcile cash/positions
- [x] Source migrated entity is zeroed post-cutover (no double counting)
- [x] Budget parity failures block by default; explicit acknowledgment only for known semantic differences

## UI parity checklist (mockup fidelity)

- [x] Onboarding route uses full-page shell (no nested app chrome/duplicate logo/nav)
- [x] Header shows onboarding context + progress + validation badge
- [x] Footer steppers (`Back` / `Continue`, final `Finish`) exclusively drive progression
- [x] Step 3 has single progression path (no duplicate extract CTA)
- [x] Continue shows user-facing validation errors when blocked
- [x] Step 6 tables and column/value alignment match approved mockup
- [x] Step 7 supports link + system-only resolution + undo
- [x] Step 8 naming and behavior align with approved wording
- [x] Step 9 net worth accordions render and support destination setup per mock
- [x] Step 9 summary banner uses neutral palette (no red-on-green clash)
- [x] Investment destination modal supports positions/lots input and total value preview

## Screenshot parity checklist

Store screenshots under a gitignored artifacts path (example: `artifacts/onboarding-mockup/`).

- [x] Step 1 reference
- [x] Step 2 reference
- [x] Step 3 reference
- [x] Step 4 reference
- [x] Step 5 reference
- [x] Step 6 reference
- [x] Step 7 reference
- [x] Step 7 action-bar (2 selected) reference
- [x] Step 8 reference
- [x] Step 9 reference
- [x] Step 9 account-modal reference
- [x] Step 10 reference
- [x] Step 11 reference

## Backend/API checklist

- [x] `schemas.py`: transfer exception payload supports link + system-only resolution shapes
- [x] `routers.py`: transfer exception save/apply enforces system-only categories
- [x] `routers.py`: persist manual pair links + undo semantics
- [x] `routers.py`: apply blocker checks include unresolved transfer exceptions
- [x] `routers.py`: preview returns meaningful blockers, not placeholders
- [x] Preserve deterministic IDs (dataset fingerprint + stable staging identity)
- [x] Preserve transactional apply (all-or-nothing)

## Net worth cutover checklist

- [x] Track-forward decision path creates destination accounts correctly
- [x] Investment destination initializes baseline capital and statement state correctly
- [x] Holdings + cash initialization does not create double-counting
- [x] Legacy source entity contribution is neutralized post-cutover
- [x] Performance math does not treat non-zero NAV as zero-contribution baseline
- [x] Tangible and loan initialization paths remain consistent with account semantics

## Data correctness checklist

- [x] Transfer neutrality invariant holds (internal transfers net to zero)
- [x] Historical inactive/retired entities remain reportable as-of date
- [x] Legacy marks preserved for Aspire-parity views
- [x] Budget parity check compares expected vs actual (`allocated`, `activity`, `available`, RTA)
- [x] No float persistence for money fields (minor units / fixed precision where required)

## Testing checklist

- [x] Add/adjust backend tests for transfer exceptions (link/system-only/undo)
- [x] Add/adjust tests for apply blockers and unblock transitions
- [x] Add/adjust tests for investment cutover baseline correctness
- [x] Add/adjust tests for budget parity gating behavior
- [x] Add/adjust frontend tests for step 5/6/9 data rendering and category editing
- [x] Run `scripts/run-tests` and record results

## Scratch space

### Current status

- Owner: OpenCode
- Branch: `master`
- Last updated: 2026-02-12

### In-progress notes

- Transfer exceptions now enforce system-only or mirrored linked-pair resolutions in both API validation and apply path.
- Step 7 UI now supports two-row link action bar, per-row system resolution, and undo; footer continue blocks with explicit error until zero unresolved.
- Step 8 copy/table labels now match "Link Overlapping Accounts" wording; Step 9 banner copy + palette shifted to neutral summary styling.
- Added integration coverage in `tests/integration/aspire_migration/test_transfer_exceptions_api.py` for system-only contract, link flow, unblock/block transition, and undo-by-resave.
- Added localStorage draft persistence for step state + transfer drafts and expanded Step 6 to active/retired budget tables with mockup-style columns/tooltips.
- Preview now emits budget parity data (`allocated`, `activity`, `available`, and `Ready to Assign`) plus new blockers for duplicate mapping collisions and net-worth classification/destination gaps.
- Budget parity mismatch gating now has deterministic integration coverage by monkeypatching parity output in preview/apply tests.
- Added parity guardrail tooling: `scripts/capture-onboarding-parity` + `scripts/check-onboarding-parity` with a required parity report template (`docs/plans/aspire-onboarding-parity-report-template.md`).
- Step 9 now includes destination setup modal with investment lot inputs and value preview; parity capture now generates all live shots (steps 1-11 + step 7 action bar + step 9 modal).
- Added mockup baseline capture script (`scripts/capture-onboarding-mockup-reference`) so reference screenshots are regenerated consistently from `aspire_onboarding_mockup.html`.
- Added integration tests for budget parity gating behavior (`force=False` blocks, `force=True` acknowledges) via deterministic parity-mismatch monkeypatching in `tests/integration/aspire_migration/test_transfer_exceptions_api.py`.
- Added integration coverage that investment imports seed `investment_account_details.ledger_baseline_minor` and `uninvested_cash_minor` from imported ledger cash to preserve explicit starting capital.
- Validation run: `scripts/run-tests --skip-frontend --skip-property --skip-e2e --filter integration:aspire_migration` (pass).
- Apply path now materializes `track_forward` net-worth destinations into tracking accounts (investment/loan/tangible), including account-class-specific initialization records and deterministic IDs.
- Added integration coverage for track-forward cutover semantics: destination account creation, investment baseline + holdings/cash initialization, loan/tangible detail initialization, and legacy-mark persistence.
- Added integration assertion that investment cutover baseline avoids double counting in `/api/net-worth/current` (positions value reflects statement NAV, not NAV + opening balance).
- Onboarding UI now uses an onboarding-specific header shell (logo/context + step meta + validation badge), hides the global app header on `/onboarding`, and keeps footer stepper hidden on the completion step.
- Step 5 account table now matches mockup columns (`Settled Balance`/`Pending Balance`) and Step 9 cards now include the in-flow `+ Add Destination Account` CTA; step 10 footer CTA now reads `Finish`, and step 11 includes an inline `Go to Dashboard` action.
- Validation run: `scripts/run-tests --skip-property --skip-integration --skip-e2e` (pass).
- Completed iterative screenshot loop (`capture-onboarding-mockup-reference` + `capture-onboarding-parity`) and tightened parity for step 1 copy/icons, step 2 OAuth CTA card, step 7 floating action bar, step 8 strategy selector, step 9 account-type modal shell, and step 10 blocked validation card.
- Updated parity Cypress specs to wait for step-ready markers before screenshot capture to avoid transition/blank-shot artifacts.
- Updated live parity fixture data to mirror mock scenario values (accounts, categories, duplicate mapping, net-worth setup, and preview blockers) so visual deltas primarily reflect UI differences instead of fixture drift.
- Validation run: `scripts/run-tests --skip-property --skip-integration --skip-e2e && scripts/check-onboarding-parity` (tests pass, parity gate blocked only by report approval requirement).
- Fixed major header/progress-bar drift caused by global `.wizard-header` CSS collisions from account-onboarding styles; onboarding header now uses explicit block layout and mock-matching typography/progress treatment.
- Additional parity pass completed to tighten top nav/progress styling and copy/fixture alignment for steps 2, 3, and 10; recaptured live artifacts after each iteration.
- Reviewer acceptance: parity is considered "decent enough for now" with only explicit, documented deviations remaining.
- Validation run: `scripts/check-onboarding-parity` (pass, report approved).
- Budget parity apply gating now requires explicit acknowledgment with a documented semantic difference key (`month_rollover_overspending`); `force` no longer bypasses parity mismatches.
- Added Cypress coverage in `cypress/e2e/parity/aspire-onboarding-validation.cy.js` for footer-stepper validation gates (step 7 unresolved transfers and step 9 open destination modal).
- Validation run: `scripts/run-tests --skip-frontend --skip-property --skip-e2e --filter integration:aspire_migration` (pass), `scripts/run-tests --skip-property --skip-integration --skip-e2e` (pass), `npx cypress run --e2e --spec cypress/e2e/parity/aspire-onboarding-validation.cy.js` (pass).
- Added integration coverage proving track-forward cutover ignores legacy mark amounts in `/api/net-worth/current`, preventing post-cutover double counting from migrated net-worth entities.
- Account deactivation now preserves `include_in_net_worth`; net-worth history remains as-of reportable for retired entities instead of dropping them from all prior periods.
- Audited SQL schema for money columns: all persisted money values remain integer minor-unit columns (`BIGINT`), with no float money storage patterns.
- Step 5 and Step 6 now compute balances from staged rows with an as-of cutoff at `v_Today` (inclusive), explicitly excluding future-dated transactions/allocations.
- Step 6 configured-budget column now comes from staged Aspire monthly target values (`Configuration!G` proxy via extracted config/user-def ranges), with row-level drift flags against Aspire dashboard proxy values.
- Added extraction/session persistence for Aspire dashboard proxy rows and surfaced category proxy coverage + drift counts through `/api/onboarding/aspire/mapping`.
- Added integration coverage for mapping preview math/parity in `tests/integration/aspire_migration/test_transfer_exceptions_api.py`.
- Added Cypress coverage for stale-draft refresh + Step 5/6 data rendering/editor behavior in `cypress/e2e/parity/aspire-onboarding-data.cy.js`.
- Validation run: `scripts/run-tests --skip-property --skip-integration --skip-e2e` (pass), `scripts/run-tests --skip-frontend --skip-property --skip-e2e --filter integration:aspire_migration` (pass), `npm run build` (pass), `npx cypress run --e2e --spec cypress/e2e/parity/aspire-onboarding-validation.cy.js,cypress/e2e/parity/aspire-onboarding-data.cy.js` (pass).

### Blockers / risks

- Remaining functional scope: none.
- Remaining parity deltas are now mostly fine-grained visual differences (modal iconography/exact scroll composition and minor copy metadata in steps 2-3); these are accepted for now and tracked in parity docs.

### Decisions made during implementation

- Chose strict API schema (`linked` | `opening_balance` | `balance_adjustment`) to make arbitrary category remap impossible at contract level.
- Manual linked transfer pairs are imported as `account_transfer` with deterministic concept IDs (`manual_transfer` namespace key).
- Treat duplicate mapping collisions and unknown net-worth classifications as correctness blockers before apply.

### Follow-ups (post-MVP)

- 

## Definition of done

- [x] Wizard behavior matches mockup + alignment doc for all steps
- [x] Locked product decisions implemented exactly
- [x] Backend validation/gating enforces critical invariants
- [x] Tests updated and passing
- [x] Screenshots reviewed for parity
- [x] Docs updated if implementation required clarifications

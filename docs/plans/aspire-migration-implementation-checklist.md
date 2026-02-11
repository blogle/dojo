# Aspire Migration Implementation Checklist

Purpose: execution checklist + scratch space for implementing the approved Aspire migration wizard.

Primary references:

- `docs/rfcs/aspire-migration-and-account-semantics.md`
- `migration_wizard_alignment.md`
- `aspire_onboarding_mockup.html`
- `docs/plans/aspire-migration-codex-kickoff-prompt.md`

## Locked decisions (must remain true)

- [ ] Transfer exceptions allow only:
  - link exactly two unresolved rows as transfer
  - resolve single orphan to `opening_balance` or `balance_adjustment`
- [ ] No arbitrary budget-category mapping for transfer exceptions
- [ ] Transfer resolution supports undo
- [ ] `v_BreakSymbol` rows never surface as transfer exceptions
- [ ] localStorage-first wizard UX persistence
- [ ] Investment cutover uses opening baseline + reconcile cash/positions
- [ ] Source migrated entity is zeroed post-cutover (no double counting)
- [ ] Budget parity failures block by default; explicit acknowledgment only for known semantic differences

## UI parity checklist (mockup fidelity)

- [ ] Onboarding route uses full-page shell (no nested app chrome/duplicate logo/nav)
- [ ] Header shows onboarding context + progress + validation badge
- [ ] Footer steppers (`Back` / `Continue`, final `Finish`) exclusively drive progression
- [ ] Step 3 has single progression path (no duplicate extract CTA)
- [ ] Continue shows user-facing validation errors when blocked
- [ ] Step 6 tables and column/value alignment match approved mockup
- [ ] Step 7 supports link + system-only resolution + undo
- [ ] Step 8 naming and behavior align with approved wording
- [ ] Step 9 summary banner uses neutral palette (no red-on-green clash)
- [ ] Investment destination modal supports positions/lots input and total value preview

## Screenshot parity checklist

Store screenshots under a gitignored artifacts path (example: `artifacts/onboarding-mockup/`).

- [ ] Step 1 reference
- [ ] Step 2 reference
- [ ] Step 3 reference
- [ ] Step 4 reference
- [ ] Step 5 reference
- [ ] Step 6 reference
- [ ] Step 7 reference
- [ ] Step 7 action-bar (2 selected) reference
- [ ] Step 8 reference
- [ ] Step 9 reference
- [ ] Step 9 account-modal reference
- [ ] Step 10 reference
- [ ] Step 11 reference

## Backend/API checklist

- [ ] `schemas.py`: transfer exception payload supports link + system-only resolution shapes
- [ ] `routers.py`: transfer exception save/apply enforces system-only categories
- [ ] `routers.py`: persist manual pair links + undo semantics
- [ ] `routers.py`: apply blocker checks include unresolved transfer exceptions
- [ ] `routers.py`: preview returns meaningful blockers, not placeholders
- [ ] Preserve deterministic IDs (dataset fingerprint + stable staging identity)
- [ ] Preserve transactional apply (all-or-nothing)

## Net worth cutover checklist

- [ ] Track-forward decision path creates destination accounts correctly
- [ ] Investment destination initializes baseline capital and statement state correctly
- [ ] Holdings + cash initialization does not create double-counting
- [ ] Legacy source entity contribution is neutralized post-cutover
- [ ] Performance math does not treat non-zero NAV as zero-contribution baseline
- [ ] Tangible and loan initialization paths remain consistent with account semantics

## Data correctness checklist

- [ ] Transfer neutrality invariant holds (internal transfers net to zero)
- [ ] Historical inactive/retired entities remain reportable as-of date
- [ ] Legacy marks preserved for Aspire-parity views
- [ ] Budget parity check compares expected vs actual (`allocated`, `activity`, `available`, RTA)
- [ ] No float persistence for money fields (minor units / fixed precision where required)

## Testing checklist

- [ ] Add/adjust backend tests for transfer exceptions (link/system-only/undo)
- [ ] Add/adjust tests for apply blockers and unblock transitions
- [ ] Add/adjust tests for investment cutover baseline correctness
- [ ] Add/adjust tests for budget parity gating behavior
- [ ] Add/adjust frontend tests for stepper-only progression and validation errors
- [ ] Run `scripts/run-tests` and record results

## Scratch space

### Current status

- Owner:
- Branch:
- Last updated:

### In-progress notes

- 

### Blockers / risks

- 

### Decisions made during implementation

- 

### Follow-ups (post-MVP)

- 

## Definition of done

- [ ] Wizard behavior matches mockup + alignment doc for all steps
- [ ] Locked product decisions implemented exactly
- [ ] Backend validation/gating enforces critical invariants
- [ ] Tests updated and passing
- [ ] Screenshots reviewed for parity
- [ ] Docs updated if implementation required clarifications

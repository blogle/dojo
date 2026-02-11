# Codex Kickoff Prompt: Aspire Migration Wizard Implementation

Use this prompt to start implementation work in this repository.

---

You are implementing the Aspire migration onboarding flow in Dojo. Follow the approved mockup and alignment spec closely, and do not introduce major UX/flow deviations unless explicitly required by backend constraints.

## Primary references (read first)

1. `docs/rfcs/aspire-migration-and-account-semantics.md`
2. `migration_wizard_alignment.md`
3. `aspire_onboarding_mockup.html`
4. `docs/aspire/named-ranges.md`
5. `docs/rules/frontend.md`
6. `docs/rules/style_guide.md`
7. `AGENTS.md`

## Existing implementation surfaces

- Frontend wizard page: `src/dojo/frontend/vite/src/pages/OnboardingPage.vue`
- Frontend API client: `src/dojo/frontend/vite/src/services/api.js`
- Backend Aspire migration router: `src/dojo/aspire_migration/routers.py`
- Backend migration schemas: `src/dojo/aspire_migration/schemas.py`
- Extraction logic: `src/dojo/aspire_migration/extract.py`
- Transfer pairing logic: `src/dojo/aspire_migration/pairing.py`
- Legacy net worth logic: `src/dojo/aspire_migration/legacy_marks.py`
- Migration tables/session persistence: `src/dojo/sql/migrations/0018_aspire_migration_onboarding.sql`
- Investments baseline/reconcile semantics: `src/dojo/investments/service.py`, `src/dojo/investments/dao.py`

## Locked product decisions (do not reinterpret)

1. **Transfer exceptions policy**
   - Auto-pair deterministically first.
   - For unresolved orphans, allow only:
     - link exactly two rows as a transfer concept (with undo), or
     - resolve single orphan as system category (`opening_balance` or `balance_adjustment`).
   - Do not allow arbitrary budget-category mapping for transfer exceptions.
   - Aspire reconciliation marker rows (`v_BreakSymbol`) are non-financial and must never appear as transfer exceptions.

2. **Persistence strategy**
   - localStorage-first UX state persistence is acceptable and preferred for wizard progress/drafts.
   - Backend session persistence remains for extracted/staged/apply-critical data.

3. **Investment cutover baseline**
   - Use opening-balance seed + reconcile cash/positions approach for destination investment accounts.
   - Ensure the source migrated net-worth entity is zeroed out post-cutover (no double counting).
   - Ensure starting capital baseline is explicit so performance is not computed from implicit zero.

4. **Budget parity gating**
   - Budget parity failures are blockers by default.
   - Allow explicit acknowledgment only for known/documented semantic differences.

## UX parity requirements

- Match the approved mockup layout and sequence step-by-step.
- Treat the mockup as the **full-page onboarding view**.
- Do not render duplicate brand chrome (no repeated app logos/nav bars or nested "page-inside-page" shell).
- During onboarding route, hide standard navigation links and keep onboarding-specific top context.

## Screenshot-driven implementation guardrail

Before significant UI coding, capture reference screenshots for each mockup step and use them as parity targets.

- Capture at minimum: steps 1..11, transfer action bar state, net worth account modal state.
- Store artifacts under a gitignored path (for example: `artifacts/onboarding-mockup/`).
- During implementation, compare live onboarding screenshots against mockup references and iterate until visually close.

## Implementation goals

1. Bring `OnboardingPage.vue` into close parity with `aspire_onboarding_mockup.html` and `migration_wizard_alignment.md`.
2. Update backend transfer-exception contracts and persistence to support link/undo + system-only resolutions.
3. Complete preview/apply flows so blockers and validation states are correctly enforced.
4. Implement cutover account initialization semantics consistent with RFC and locked decisions.
5. Keep money values in minor units and preserve temporal/SCD2 invariants.

## Safety and correctness constraints

- No fabricated balancing money.
- No double counting of the same real-world balance.
- Transfer neutrality invariant must hold.
- Preserve legacy net worth marks for Aspire parity.
- Maintain auditability and deterministic IDs by dataset fingerprint + stable staging identity.

## Deliverables

1. Updated frontend wizard flow and styling matching mockup/alignment.
2. Backend API updates for transfer exception resolution/linking.
3. Apply path updates for cutover funding/baseline logic.
4. Tests for:
   - transfer resolution/link/undo behavior,
   - apply blockers,
   - investment baseline correctness,
   - budget parity gating behavior.
5. Brief implementation note summarizing any intentional deviations and why.

## Validation checklist

- Run relevant tests via `scripts/run-tests`.
- Manually exercise full onboarding flow end-to-end.
- Confirm no duplicate app shell on onboarding route.
- Confirm transfer exceptions cannot be resolved to arbitrary budget categories.
- Confirm cutover destinations do not produce double counting and have explicit baseline capital.

---

If anything in code conflicts with the RFC + alignment decisions above, update code to match the approved behavior, and document the change clearly.

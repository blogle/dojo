"""Schemas for onboarding + Aspire migration."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

OnboardingMode = Literal["manual", "aspire"]
OnboardingStatus = Literal["not_started", "in_progress", "completed"]


class OnboardingStatusResponse(BaseModel):
    """Current onboarding state as persisted in DuckDB."""

    onboarding_mode: OnboardingMode | None = Field(
        description="Selected onboarding mode (manual vs aspire), if chosen.",
    )
    onboarding_status: OnboardingStatus = Field(
        description="Overall onboarding status.",
    )
    migration_session_id: str | None = Field(
        description="Active migration session id for Aspire onboarding, if any.",
    )
    should_onboard: bool = Field(
        description="True when the UI should force the onboarding route.",
    )

    aspire_migration_allow_partial_mapping: bool = Field(
        default=False,
        description="Whether the server allows partial mapping completion (dev/test helper).",
    )


class StartOnboardingRequest(BaseModel):
    onboarding_mode: OnboardingMode = Field(description="Which onboarding path the user chose.")


class CancelOnboardingResponse(BaseModel):
    ok: bool = Field(True, description="Whether the onboarding state was reset.")


class GoogleOAuthStartResponse(BaseModel):
    authorization_url: str = Field(description="URL to start Google OAuth flow.")


class GoogleOAuthStatusResponse(BaseModel):
    connected: bool = Field(description="Whether the server holds a short-lived access token.")
    expires_at_s: float | None = Field(
        description="Epoch seconds when the stored credentials will be discarded.",
    )


class VerifyAspireSheetRequest(BaseModel):
    spreadsheet: str = Field(description="Spreadsheet id or full URL.")


class VerifyAspireSheetResponse(BaseModel):
    readable: bool = Field(description="Whether the sheet metadata was accessible.")
    looks_like_aspire: bool = Field(description="True when required Aspire named ranges are present.")
    missing_named_ranges: list[str] = Field(
        default_factory=list,
        description="Required named ranges that were not found.",
    )
    named_range_count: int = Field(description="Total named ranges seen on the spreadsheet.")


class ExtractAspireRequest(BaseModel):
    spreadsheet: str = Field(description="Spreadsheet id or full URL.")
    force: bool = Field(
        default=False,
        description="Force re-extraction even if a summary already exists for the session.",
    )


class ExtractAspireResponse(BaseModel):
    migration_session_id: str = Field(description="Migration session id.")
    dataset_fingerprint: str = Field(description="SHA-256 fingerprint of extracted dataset.")

    transactions_count: int
    transactions_date_min: str | None
    transactions_date_max: str | None

    allocations_count: int
    allocations_date_min: str | None
    allocations_date_max: str | None

    net_worth_snapshots_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None


class MappingCandidatesResponse(BaseModel):
    accounts: list[str] = Field(description="Distinct Aspire account names found in staging.")
    categories: list[str] = Field(description="Distinct Aspire category names found in staging.")


MappingStatus = Literal["not_started", "in_progress", "completed", "failed"]


AccountClass = Literal["cash", "credit", "investment", "accessible", "loan", "tangible"]
AccountRole = Literal["on_budget", "tracking"]
AccountType = Literal["asset", "liability"]

GoalType = Literal["target_date", "recurring"]
GoalFrequency = Literal["monthly", "quarterly", "yearly"]


class AspireAccountMapping(BaseModel):
    dojo_name: str = Field(min_length=1, description="Name to use for the Dojo account.")
    account_class: AccountClass = Field(description="Dojo account class to create/match.")
    account_role: AccountRole = Field(description="Whether this account is on-budget or tracking.")
    is_active: bool = Field(
        default=True,
        description="Whether the migrated account should be active (not retired).",
    )


class AspireCategoryMapping(BaseModel):
    dojo_name: str = Field(min_length=1, description="Name to use for the Dojo budget category.")
    group_name: str = Field(min_length=1, description="Budget category group name to use/create.")
    is_active: bool = Field(
        default=True,
        description="Whether the migrated category should be active (not retired).",
    )

    # Optional budgeting goals. These map directly to Dojo's budget category fields.
    goal_type: GoalType | None = None
    goal_amount_minor: int | None = None
    goal_target_date: date | None = None
    goal_frequency: GoalFrequency | None = None


class AspireMapping(BaseModel):
    accounts: dict[str, AspireAccountMapping] = Field(
        default_factory=dict,
        description="Mapping from Aspire account name to Dojo account definition.",
    )
    categories: dict[str, AspireCategoryMapping] = Field(
        default_factory=dict,
        description="Mapping from Aspire category name to Dojo category definition.",
    )


class GetAspireMappingResponse(BaseModel):
    mapping_status: MappingStatus = Field(description="Current persisted mapping step status.")
    mapping: AspireMapping = Field(description="Current mapping (defaulted if not yet saved).")

    aspire_hidden_accounts: list[str] = Field(
        default_factory=list,
        description="Aspire HiddenAccounts list (retired accounts).",
    )
    aspire_hidden_categories: list[str] = Field(
        default_factory=list,
        description="Aspire HiddenCategories list (retired categories).",
    )

    aspire_net_worth_assets: list[str] = Field(
        default_factory=list,
        description="Aspire NetWorthAssets list (net worth asset entities).",
    )
    aspire_net_worth_debts: list[str] = Field(
        default_factory=list,
        description="Aspire NetWorthDebts list (net worth debt entities).",
    )
    aspire_net_worth_categories: list[str] = Field(
        default_factory=list,
        description="Aspire NetWorthCategories list (assets + debts).",
    )

    aspire_special_labels: dict[str, str] = Field(
        default_factory=dict,
        description="Aspire special labels (v_AtoB, v_AccountTransfer, v_StartingBalance, v_BalanceAdjustment).",
    )


class SaveAspireMappingRequest(BaseModel):
    mapping: AspireMapping = Field(description="Mapping payload to persist.")
    complete: bool = Field(
        default=False,
        description="When true, mark mapping as completed (server validates completeness).",
    )


TransferPairingStatus = Literal["not_started", "in_progress", "completed", "failed"]


class AspireTransferRow(BaseModel):
    row_index: int
    transaction_date: str | None
    account_name: str | None
    amount_minor: int
    memo: str | None


class AspireTransferCandidateGroup(BaseModel):
    group_key: str = Field(description="Stable key: date|abs(amount_minor).")
    transaction_date: str | None
    amount_minor_abs: int
    rows: list[AspireTransferRow]


class GetAspireTransfersResponse(BaseModel):
    transfer_pairing_status: TransferPairingStatus
    auto_pairs: list[tuple[int, int]] = Field(
        default_factory=list,
        description="Auto-paired (outflow_row_index, inflow_row_index).",
    )
    ambiguous_groups: list[AspireTransferCandidateGroup] = Field(
        default_factory=list,
        description="Groups requiring user review.",
    )


class HandoffDestination(BaseModel):
    # This is intentionally shaped like AccountCreateRequest (minus account_id),
    # so the UI can collect details once and the import step can create accounts
    # without duplicating mapping logic.
    name: str = Field(min_length=1, description="Name for the new Dojo account")

    # Optional for backward-compat with previously saved decisions.
    account_type: AccountType | None = Field(default=None, description="asset or liability")
    account_class: AccountClass = Field(description="Dojo account class")
    account_role: AccountRole = Field(default="tracking", description="on_budget or tracking")

    # Stored for parity with the normal account creation flow; during import we still
    # initialize balances via migration logic rather than this value.
    current_balance_minor: int = Field(default=0, description="Initial balance in minor units")
    currency: str = Field(default="USD", description="Currency code")
    opened_on: date | None = Field(default=None, description="Optional account open date")
    is_active: bool = Field(default=True, description="Whether the account is active")
    institution_name: str | None = Field(default=None, description="Institution name")

    # Polymorphic detail fields (optional)
    interest_rate_apy: float | None = None
    card_type: str | None = None
    apr: float | None = None
    cash_advance_apr: float | None = None
    term_end_date: date | None = None
    early_withdrawal_penalty: bool | None = None
    risk_free_sweep_rate: float | None = None
    is_self_directed: bool | None = None
    tax_classification: str | None = None
    initial_principal_minor: int | None = None
    mortgage_escrow_details: str | None = None
    asset_name: str | None = None
    acquisition_cost_minor: int | None = None

    # Optional opening balance for the destination account. This makes the onboarding
    # wizard feel identical to the normal account creation flow, even though the
    # account is created during the apply step.
    opening_balance_minor: int | None = Field(default=None, description="Optional opening balance in minor units")
    opening_balance_date: date | None = Field(default=None, description="Optional as-of date for opening balance")


class NetWorthTreatmentConfig(BaseModel):
    # Treatment A: derive_from_ledger
    budget_account_id: str | None = Field(default=None, description="Budget account ID to derive balance from")

    # Treatment B: tracking_snapshots
    acknowledge_drift: bool = Field(default=False, description="User acknowledges balance may drift")

    # Treatment C: handoff
    # cutover_date is always "today" - not configurable
    destinations: list[HandoffDestination] = Field(
        default_factory=list, description="New accounts to create at cutover"
    )

    # Treatment D: linked_budget
    linked_category_id: str | None = Field(default=None, description="Budget category ID for inflows")


class NetWorthDecision(BaseModel):
    treatment: Literal["derive_from_ledger", "tracking_snapshots", "handoff", "linked_budget"] = Field(
        description="Treatment type for this net worth entity"
    )
    config: NetWorthTreatmentConfig = Field(default_factory=NetWorthTreatmentConfig)


class SaveNetWorthDecisionsRequest(BaseModel):
    decisions: dict[str, NetWorthDecision] = Field(description="Map from Aspire net worth account name to decision.")


class GetNetWorthDecisionsResponse(BaseModel):
    decisions: dict[str, NetWorthDecision] = Field(
        default_factory=dict,
        description="Saved net worth decisions for the current migration session.",
    )


ImportStatus = Literal["not_started", "in_progress", "completed", "failed"]


class ApplyAspireMigrationRequest(BaseModel):
    force: bool = Field(
        default=False,
        description=(
            "When true, re-run apply even if the session was already imported. "
            "This is primarily for recovery from partial/failed imports."
        ),
    )


class ApplyAspireMigrationResponse(BaseModel):
    import_status: ImportStatus
    accounts_created: int = 0
    category_groups_created: int = 0
    categories_created: int = 0
    transactions_imported: int = 0
    transfers_imported: int = 0


class BudgetParityRow(BaseModel):
    aspire_category_name: str
    dojo_category_id: str

    expected_allocated_minor: int
    actual_allocated_minor: int
    diff_allocated_minor: int

    expected_activity_minor: int
    actual_activity_minor: int
    diff_activity_minor: int

    expected_available_minor: int
    actual_available_minor: int
    diff_available_minor: int


class AspireBudgetParityResponse(BaseModel):
    month_start: date
    mismatches: int
    max_abs_diff_minor: int
    rows: list[BudgetParityRow] = Field(default_factory=list)

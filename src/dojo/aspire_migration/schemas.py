"""Pydantic schemas for onboarding + Aspire migration."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


OnboardingMode = Literal["manual", "aspire"]
OnboardingStatus = Literal["not_started", "in_progress", "completed"]


class OnboardingStatusResponse(BaseModel):
    onboarding_mode: OnboardingMode | None
    onboarding_status: OnboardingStatus
    migration_session_id: str | None
    should_onboard: bool

    aspire_migration_allow_partial_mapping: bool = Field(
        default=False,
        description="Dev/test helper: allow wizard to advance with partial mapping/decisions.",
    )


class StartOnboardingRequest(BaseModel):
    onboarding_mode: OnboardingMode


class CancelOnboardingResponse(BaseModel):
    ok: bool = True


class GoogleOAuthStartResponse(BaseModel):
    authorization_url: str


class GoogleOAuthStatusResponse(BaseModel):
    connected: bool
    expires_at_s: float | None


class VerifyAspireSheetRequest(BaseModel):
    spreadsheet: str = Field(description="Spreadsheet id or full URL")


class VerifyAspireSheetResponse(BaseModel):
    readable: bool
    looks_like_aspire: bool
    missing_named_ranges: list[str] = Field(default_factory=list)
    named_range_count: int


class ExtractAspireRequest(BaseModel):
    spreadsheet: str
    force: bool = False


class ExtractAspireResponse(BaseModel):
    migration_session_id: str
    dataset_fingerprint: str

    transactions_count: int
    transactions_date_min: str | None
    transactions_date_max: str | None

    allocations_count: int
    allocations_date_min: str | None
    allocations_date_max: str | None

    net_worth_marks_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None


MappingStatus = Literal["not_started", "in_progress", "completed", "failed"]

AccountClass = Literal["cash", "credit", "investment", "loan", "tangible", "accessible"]
AccountRole = Literal["on_budget", "tracking"]


class AspireAccountMapping(BaseModel):
    dojo_name: str = Field(min_length=1)
    account_class: AccountClass
    account_role: AccountRole
    is_active: bool = True

    # Preview-only fields (computed from staged transactions).
    display_type: str | None = None
    current_balance_minor: int | None = None
    pending_balance_minor: int | None = None


class AspireCategoryMapping(BaseModel):
    dojo_name: str = Field(min_length=1)
    group_name: str = Field(min_length=1)
    is_active: bool = True

    # Budget goal configuration (maps onto Dojo budget category goal fields).
    goal_type: Literal["recurring", "target_date"] | None = None
    goal_amount_minor: int | None = None
    goal_target_date: date | None = None
    goal_frequency: Literal["monthly", "quarterly", "yearly"] | None = None

    # Preview-only fields (computed from staged transactions/allocations).
    config_label: str | None = None
    configured_budget_minor: int | None = None
    budgeted_minor: int | None = None
    activity_minor: int | None = None
    available_minor: int | None = None

    # Best-effort validation against Aspire dashboard proxies.
    proxy_configured_budget_minor: int | None = None
    proxy_budgeted_minor: int | None = None
    proxy_activity_minor: int | None = None
    proxy_available_minor: int | None = None
    drift_configured_budget_minor: int | None = None
    drift_budgeted_minor: int | None = None
    drift_activity_minor: int | None = None
    drift_available_minor: int | None = None


class AspireBudgetMapping(BaseModel):
    accounts: dict[str, AspireAccountMapping] = Field(default_factory=dict)
    categories: dict[str, AspireCategoryMapping] = Field(default_factory=dict)


class GetAspireMappingResponse(BaseModel):
    mapping_status: MappingStatus
    mapping: AspireBudgetMapping

    aspire_hidden_accounts: list[str] = Field(default_factory=list)
    aspire_hidden_categories: list[str] = Field(default_factory=list)
    aspire_special_labels: dict[str, str] = Field(default_factory=dict)
    aspire_status_symbols: dict[str, str] = Field(default_factory=dict)

    # Proxy-parity summary for step 6 diagnostics.
    category_proxy_coverage_count: int = 0
    category_proxy_drift_count: int = 0


class SaveAspireMappingRequest(BaseModel):
    mapping: AspireBudgetMapping
    complete: bool = False


class AspireTransferExceptionRow(BaseModel):
    row_index: int
    transaction_date: str | None
    account_name: str | None
    category_name: str | None
    amount_minor: int
    memo: str | None


class TransferResolutionKind(BaseModel):
    kind: Literal["linked", "opening_balance", "balance_adjustment"]
    linked_row_index: int | None = None


class GetAspireTransfersResponse(BaseModel):
    auto_pairs: list[tuple[int, int]] = Field(default_factory=list)
    exceptions: list[AspireTransferExceptionRow] = Field(default_factory=list)
    saved_resolutions: dict[int, TransferResolutionKind] = Field(default_factory=dict)


class SaveTransferResolutionsRequest(BaseModel):
    resolutions: dict[int, TransferResolutionKind] = Field(
        default_factory=dict,
        description="Map from Aspire trx row_index to resolution.",
    )


NetWorthClassification = Literal["asset", "debt", "unknown"]
NetWorthDecisionKind = Literal[
    "duplicate_derive_from_ledger",
    "legacy_only",
    "track_forward",
]


class NetWorthHolding(BaseModel):
    ticker: str
    quantity: float
    # Current price per share (minor units). Used for starting NAV + market price seed.
    current_price_minor: int = 0

    # Optional cost basis: users often know total basis, not per-share.
    # If provided, importer derives avg_cost_minor = round(cost_basis_total_minor / quantity).
    cost_basis_total_minor: int | None = None

    # Back-compat: older wizard used avg_cost_minor as a numeric input and also (incorrectly)
    # as the current price seed. We still accept it and will treat it as price when
    # current_price_minor is missing.
    avg_cost_minor: int = 0


class NetWorthDestination(BaseModel):
    name: str = Field(min_length=1)
    institution_name: str | None = None
    account_class: Literal["cash", "credit", "accessible", "investment", "loan", "tangible"]
    account_type: Literal["asset", "liability"]
    starting_value_minor: int = Field(description="As-of value at cutover in signed minor units")

    # Investment-only
    statement_cash_minor: int | None = None
    holdings: list[NetWorthHolding] = Field(default_factory=list)
    is_self_directed: bool | None = None
    tax_classification: str | None = None

    # Loan-only
    interest_rate_apy: float | None = None
    original_principal_minor: int | None = None
    loan_mode: Literal["statement_principal", "split_payments"] | None = None

    # Tangible-only
    valuation_source: str | None = None
    note: str | None = None


class NetWorthDecision(BaseModel):
    decision: NetWorthDecisionKind
    classification: NetWorthClassification

    # For duplicates
    ledger_account_id: str | None = None

    # For track-forward
    cutover_date: date | None = None
    destinations: list[NetWorthDestination] = Field(default_factory=list)


class GetNetWorthDecisionsResponse(BaseModel):
    decisions: dict[str, NetWorthDecision] = Field(default_factory=dict)
    last_reported_by_category_minor: dict[str, int] = Field(default_factory=dict)


class SaveNetWorthDecisionsRequest(BaseModel):
    decisions: dict[str, NetWorthDecision] = Field(default_factory=dict)
    complete: bool = False


class SeriesPoint(BaseModel):
    date: str
    value_minor: int


class DuplicateDriftRow(BaseModel):
    net_worth_category: str
    ledger_account_id: str
    marks_compared: int
    median_abs_drift_minor: int
    p90_abs_drift_minor: int
    max_abs_drift_minor: int


class BudgetParityRow(BaseModel):
    category_id: str
    category_name: str
    expected_allocated_minor: int
    actual_allocated_minor: int
    diff_allocated_minor: int
    expected_activity_minor: int
    actual_activity_minor: int
    diff_activity_minor: int
    expected_available_minor: int
    actual_available_minor: int
    diff_available_minor: int


class BudgetParityResponse(BaseModel):
    month_start: date
    mismatches: int
    max_abs_diff_minor: int
    rows: list[BudgetParityRow] = Field(default_factory=list)


BudgetParitySemanticDifference = Literal["month_rollover_overspending"]


class MigrationPreviewResponse(BaseModel):
    legacy_net_worth_bucket: list[SeriesPoint] = Field(default_factory=list)
    dojo_net_worth_month_end: list[SeriesPoint] = Field(default_factory=list)
    duplicate_drift: list[DuplicateDriftRow] = Field(default_factory=list)
    budget_parity: BudgetParityResponse | None = None
    budget_parity_known_differences: list[BudgetParitySemanticDifference] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    can_apply: bool = False


ImportStatus = Literal["not_started", "in_progress", "completed", "failed"]


class ApplyAspireMigrationRequest(BaseModel):
    force: bool = False
    ack_budget_parity_mismatch: bool = False
    budget_parity_semantic_difference: BudgetParitySemanticDifference | None = None


class ApplyAspireMigrationResponse(BaseModel):
    import_status: ImportStatus
    accounts_created: int = 0
    category_groups_created: int = 0
    categories_created: int = 0
    transactions_imported: int = 0
    allocations_imported: int = 0
    legacy_marks_imported: int = 0

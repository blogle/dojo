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


class AspireCategoryMapping(BaseModel):
    dojo_name: str = Field(min_length=1)
    group_name: str = Field(min_length=1)
    is_active: bool = True


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
    kind: Literal["external", "opening_balance", "balance_adjustment"]
    category_id: str | None = None


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
    avg_cost_minor: int = 0


class NetWorthDestination(BaseModel):
    name: str = Field(min_length=1)
    account_class: Literal["investment", "loan", "tangible"]
    account_type: Literal["asset", "liability"]
    starting_value_minor: int = Field(description="As-of value at cutover in signed minor units")

    # Investment-only
    statement_cash_minor: int | None = None
    holdings: list[NetWorthHolding] = Field(default_factory=list)

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


class MigrationPreviewResponse(BaseModel):
    legacy_net_worth_bucket: list[SeriesPoint] = Field(default_factory=list)
    dojo_net_worth_month_end: list[SeriesPoint] = Field(default_factory=list)
    duplicate_drift: list[DuplicateDriftRow] = Field(default_factory=list)
    budget_parity: BudgetParityResponse | None = None
    blockers: list[str] = Field(default_factory=list)
    can_apply: bool = False


ImportStatus = Literal["not_started", "in_progress", "completed", "failed"]


class ApplyAspireMigrationRequest(BaseModel):
    force: bool = False


class ApplyAspireMigrationResponse(BaseModel):
    import_status: ImportStatus
    accounts_created: int = 0
    category_groups_created: int = 0
    categories_created: int = 0
    transactions_imported: int = 0
    allocations_imported: int = 0
    legacy_marks_imported: int = 0

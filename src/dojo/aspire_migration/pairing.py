"""Deterministic transfer pairing for Aspire ledger rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TransferLeg:
    row_index: int
    transaction_date: date
    account_name: str
    category_name: str | None
    amount_minor: int


@dataclass(frozen=True)
class TransferPairingResult:
    pairs: list[tuple[int, int]]
    exceptions: list[int]


def pair_transfer_legs(
    legs: list[TransferLeg],
    *,
    tolerance_days: int = 3,
    transfer_label: str | None = None,
) -> TransferPairingResult:
    """Pair opposite-sign legs across different accounts.

    Returns pairs as (outflow_row_index, inflow_row_index).

    Determinism:
    - Pairing is greedy over sorted outflow legs.
    - A pair is created only when the best candidate is unambiguous.
    """

    if tolerance_days < 0:
        raise ValueError("tolerance_days must be >= 0")

    by_abs: dict[int, list[TransferLeg]] = {}
    for leg in legs:
        by_abs.setdefault(abs(int(leg.amount_minor)), []).append(leg)

    used: set[int] = set()
    pairs: list[tuple[int, int]] = []

    for abs_amount in sorted(by_abs.keys()):
        group = by_abs[abs_amount]
        outflows = sorted(
            [l for l in group if l.amount_minor < 0],
            key=lambda l: (l.transaction_date, l.row_index),
        )
        inflows = sorted(
            [l for l in group if l.amount_minor > 0],
            key=lambda l: (l.transaction_date, l.row_index),
        )

        for out_leg in outflows:
            if out_leg.row_index in used:
                continue

            candidates: list[tuple[int, int, int, TransferLeg]] = []
            # (score, date_diff, row_index, inflow_leg)
            for in_leg in inflows:
                if in_leg.row_index in used:
                    continue
                if in_leg.account_name == out_leg.account_name:
                    continue

                date_diff = abs((in_leg.transaction_date - out_leg.transaction_date).days)
                if date_diff > tolerance_days:
                    continue

                score = 0
                if out_leg.category_name and out_leg.category_name == in_leg.account_name:
                    score += 2
                if in_leg.category_name and in_leg.category_name == out_leg.account_name:
                    score += 2
                if transfer_label and out_leg.category_name == transfer_label:
                    score += 1
                if transfer_label and in_leg.category_name == transfer_label:
                    score += 1

                # Require at least one strong signal.
                if score < 2:
                    continue

                candidates.append((score, date_diff, in_leg.row_index, in_leg))

            if not candidates:
                continue

            candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
            best = candidates[0]

            # Unambiguous best: no other candidate ties on (score, date_diff).
            if len(candidates) > 1 and candidates[1][0] == best[0] and candidates[1][1] == best[1]:
                continue

            in_leg = best[3]
            used.add(out_leg.row_index)
            used.add(in_leg.row_index)
            pairs.append((out_leg.row_index, in_leg.row_index))

    exceptions = sorted([leg.row_index for leg in legs if leg.row_index not in used])
    pairs.sort()
    return TransferPairingResult(pairs=pairs, exceptions=exceptions)

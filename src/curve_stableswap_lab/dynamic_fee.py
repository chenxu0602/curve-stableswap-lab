"""
Dynamic fee utilities for Curve StableSwap NG-style simulations.

This module models the off-peg dynamic fee formula used by StableSwap NG.
It is intended for research, characterization tests, and notebooks.
It is not production pricing code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


FEE_DENOMINATOR = 10**10


class DynamicFeeError(ValueError):
    """Raised when dynamic fee inputs are invalid."""


def dynamic_fee(
    xpi: int,
    xpj: int,
    base_fee: int,
    offpeg_fee_multiplier: int,
    *,
    fee_denominator: int = FEE_DENOMINATOR,
) -> int:
    """
    Compute StableSwap NG-style dynamic fee.

    Parameters
    ----------
    xpi:
        Normalized xp balance for coin i or average xp around the swap.
    xpj:
        Normalized xp balance for coin j or average xp around the swap.
    base_fee:
        Base fee in Curve fee precision.
        Example: 4_000_000 means 0.04% when denominator is 1e10.
    offpeg_fee_multiplier:
        Off-peg fee multiplier in Curve fee precision.
        If <= fee_denominator, dynamic fee is disabled and base_fee is returned.
        Example: 20_000_000_000 means 2x.
    fee_denominator:
        Fee precision denominator. Default: 1e10.

    Returns
    -------
    int
        Effective dynamic fee in the same precision as base_fee.

    Formula
    -------
    If offpeg_fee_multiplier <= fee_denominator:

        dynamic_fee = base_fee

    Otherwise:

        dynamic_fee =
            offpeg_fee_multiplier * base_fee
            /
            (
                (offpeg_fee_multiplier - fee_denominator)
                * 4 * xpi * xpj / (xpi + xpj)^2
                + fee_denominator
            )

    Intuition
    ---------
    - balanced pool: 4*xpi*xpj/(xpi+xpj)^2 = 1, so fee = base_fee
    - imbalanced pool: term < 1, denominator smaller, fee > base_fee
    - extreme imbalance: term -> 0, fee approaches base_fee * multiplier / denominator
    """

    xpi = int(xpi)
    xpj = int(xpj)
    base_fee = int(base_fee)
    offpeg_fee_multiplier = int(offpeg_fee_multiplier)
    fee_denominator = int(fee_denominator)

    if xpi <= 0:
        raise DynamicFeeError("xpi must be positive")
    if xpj <= 0:
        raise DynamicFeeError("xpj must be positive")
    if base_fee < 0:
        raise DynamicFeeError("base_fee must be non-negative")
    if offpeg_fee_multiplier <= 0:
        raise DynamicFeeError("offpeg_fee_multiplier must be positive")
    if fee_denominator <= 0:
        raise DynamicFeeError("fee_denominator must be positive")

    if offpeg_fee_multiplier <= fee_denominator:
        return base_fee

    xps2 = (xpi + xpj) ** 2

    balance_factor = (4 * xpi * xpj) // xps2

    # The integer expression above is too coarse for 1e18-scale balances
    # because 4*xpi*xpj/(xpi+xpj)^2 is in [0, 1]. If evaluated directly with
    # integer division, almost all imbalanced states collapse to 0.
    #
    # StableSwap NG avoids this by multiplying before division:
    #
    # denominator =
    #   (multiplier - denominator) * 4 * xpi * xpj / xps2
    #   + denominator
    #
    # Keep the same ordering here.
    denominator = (
        ((offpeg_fee_multiplier - fee_denominator) * 4 * xpi * xpj) // xps2
        + fee_denominator
    )

    if denominator <= 0:
        raise DynamicFeeError("dynamic fee denominator must be positive")

    return (offpeg_fee_multiplier * base_fee) // denominator


def balance_factor_scaled(
    xpi: int,
    xpj: int,
    *,
    scale: int = 10**18,
) -> int:
    """
    Return scaled balance factor:

        4 * xpi * xpj / (xpi + xpj)^2

    A balanced pair returns approximately `scale`.
    Extreme imbalance approaches zero.

    This is useful for plotting and diagnostics.
    """

    xpi = int(xpi)
    xpj = int(xpj)
    scale = int(scale)

    if xpi <= 0:
        raise DynamicFeeError("xpi must be positive")
    if xpj <= 0:
        raise DynamicFeeError("xpj must be positive")
    if scale <= 0:
        raise DynamicFeeError("scale must be positive")

    return (4 * xpi * xpj * scale) // ((xpi + xpj) ** 2)


def imbalance_ratio(
    xpi: int,
    xpj: int,
    *,
    scale: int = 10**18,
) -> int:
    """
    Return a scaled imbalance ratio in [0, scale].

    0 means perfectly balanced.
    Values closer to scale mean more imbalanced.

        imbalance = abs(xpi - xpj) / (xpi + xpj)
    """

    xpi = int(xpi)
    xpj = int(xpj)
    scale = int(scale)

    if xpi <= 0:
        raise DynamicFeeError("xpi must be positive")
    if xpj <= 0:
        raise DynamicFeeError("xpj must be positive")
    if scale <= 0:
        raise DynamicFeeError("scale must be positive")

    return (abs(xpi - xpj) * scale) // (xpi + xpj)


@dataclass(frozen=True)
class DynamicFeePoint:
    """
    One dynamic-fee observation for scenario generation and plotting.
    """

    xpi: int
    xpj: int
    base_fee: int
    offpeg_fee_multiplier: int
    effective_fee: int
    balance_factor: int
    imbalance: int


def dynamic_fee_point(
    xpi: int,
    xpj: int,
    base_fee: int,
    offpeg_fee_multiplier: int,
) -> DynamicFeePoint:
    """
    Return a structured dynamic-fee observation.
    """

    return DynamicFeePoint(
        xpi=int(xpi),
        xpj=int(xpj),
        base_fee=int(base_fee),
        offpeg_fee_multiplier=int(offpeg_fee_multiplier),
        effective_fee=dynamic_fee(xpi, xpj, base_fee, offpeg_fee_multiplier),
        balance_factor=balance_factor_scaled(xpi, xpj),
        imbalance=imbalance_ratio(xpi, xpj),
    )


def dynamic_fee_curve(
    ratios: Sequence[float],
    *,
    total_xp: int = 2 * 10**18,
    base_fee: int = 4_000_000,
    offpeg_fee_multiplier: int = 20_000_000_000,
) -> list[DynamicFeePoint]:
    """
    Generate dynamic-fee observations over a range of balance ratios.

    Parameters
    ----------
    ratios:
        Fractions for xpi / (xpi + xpj), usually between 0 and 1.
        Values exactly 0 or 1 are skipped because balances must be positive.
    total_xp:
        xpi + xpj.
    base_fee:
        Base fee in Curve precision.
    offpeg_fee_multiplier:
        Off-peg fee multiplier in Curve precision.

    Returns
    -------
    list[DynamicFeePoint]
    """

    if total_xp <= 0:
        raise DynamicFeeError("total_xp must be positive")

    out: list[DynamicFeePoint] = []

    for ratio in ratios:
        r = float(ratio)

        if r <= 0.0 or r >= 1.0:
            continue

        xpi = int(total_xp * r)
        xpj = int(total_xp) - xpi

        if xpi <= 0 or xpj <= 0:
            continue

        out.append(
            dynamic_fee_point(
                xpi,
                xpj,
                base_fee,
                offpeg_fee_multiplier,
            )
        )

    return out


def fee_to_bps(fee: int, *, fee_denominator: int = FEE_DENOMINATOR) -> float:
    """
    Convert Curve fee precision to basis points.

    Example:
    - 4_000_000 / 1e10 = 0.0004 = 4 bps
    """

    fee = int(fee)
    fee_denominator = int(fee_denominator)

    if fee_denominator <= 0:
        raise DynamicFeeError("fee_denominator must be positive")

    return fee / fee_denominator * 10_000
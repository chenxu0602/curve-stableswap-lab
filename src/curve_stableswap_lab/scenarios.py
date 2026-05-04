"""
Scenario generators for Curve StableSwap simulation notebooks.

These helpers turn the lower-level StableSwap math and dynamic-fee functions
into pandas DataFrames that are convenient for plotting and analysis.

The goal is not to build a production analytics system. The goal is to create
small, reproducible simulation datasets for security-oriented research notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd

from curve_stableswap_lab.dynamic_fee import (
    FEE_DENOMINATOR,
    dynamic_fee,
    fee_to_bps,
    imbalance_ratio,
)
from curve_stableswap_lab.stableswap_math import (
    A_PRECISION,
    PRECISION,
    StableSwapMathError,
    quote_dy,
)


class ScenarioError(ValueError):
    """Raised when a scenario receives invalid parameters."""


@dataclass(frozen=True)
class AmpSlippageScenario:
    amp: int
    trade_size: int
    trade_size_pct: float
    dy: int
    dy_over_dx: float
    slippage: float


@dataclass(frozen=True)
class DynamicFeeScenario:
    ratio: float
    xpi: int
    xpj: int
    imbalance: float
    multiplier: int
    multiplier_x: float
    effective_fee: int
    effective_fee_bps: float


@dataclass(frozen=True)
class QuoteStalenessScenario:
    direction: str
    rate_change: float
    quoted_dy: int
    executed_dy: int
    error: int
    error_pct_of_quote: float


def _validate_positive_int(name: str, value: int) -> int:
    value = int(value)
    if value <= 0:
        raise ScenarioError(f"{name} must be positive")
    return value


def _as_float_list(values: Iterable[float]) -> list[float]:
    out = [float(x) for x in values]
    if not out:
        raise ScenarioError("values must be non-empty")
    return out


def amp_slippage_grid(
    *,
    amps: Sequence[int] = (20 * A_PRECISION, 100 * A_PRECISION, 500 * A_PRECISION),
    trade_sizes: Sequence[int] | None = None,
    pool_balance: int = 10**18,
    n_coins: int = 2,
    i: int = 0,
    j: int = 1,
    rates: Sequence[int] | None = None,
    fee: int = 0,
) -> pd.DataFrame:
    """
    Generate a DataFrame showing how A changes near-peg slippage.

    Parameters
    ----------
    amps:
        Amplification values using Curve's A_PRECISION convention.
    trade_sizes:
        Raw input amounts. If omitted, a small default sweep is used.
    pool_balance:
        Initial raw balance per coin.
    n_coins:
        Number of coins in the balanced pool.
    i, j:
        Swap direction.
    rates:
        Rate multipliers. Defaults to 1e18 for each coin.
    fee:
        Optional fee in Curve fee precision.

    Returns
    -------
    pandas.DataFrame
        Columns:
        - amp
        - A
        - trade_size
        - trade_size_pct
        - dy
        - dy_over_dx
        - slippage
    """

    pool_balance = _validate_positive_int("pool_balance", pool_balance)

    if n_coins < 2:
        raise ScenarioError("n_coins must be at least 2")
    if i == j:
        raise ScenarioError("i and j must be different")
    if i < 0 or i >= n_coins or j < 0 or j >= n_coins:
        raise ScenarioError("i or j out of range")

    amps_list = [int(a) for a in amps]
    if not amps_list:
        raise ScenarioError("amps must be non-empty")
    if any(a <= 0 for a in amps_list):
        raise ScenarioError("amps must be positive")

    if trade_sizes is None:
        trade_sizes = (
            pool_balance // 10_000,  # 1 bp of pool
            pool_balance // 1_000,   # 10 bps
            pool_balance // 100,     # 1%
            pool_balance // 20,      # 5%
            pool_balance // 10,      # 10%
        )

    trade_sizes_list = [int(x) for x in trade_sizes]
    if not trade_sizes_list:
        raise ScenarioError("trade_sizes must be non-empty")
    if any(x <= 0 for x in trade_sizes_list):
        raise ScenarioError("trade_sizes must be positive")

    if rates is None:
        rates_list = [PRECISION for _ in range(n_coins)]
    else:
        rates_list = [int(r) for r in rates]

    if len(rates_list) != n_coins:
        raise ScenarioError("rates length must equal n_coins")
    if any(r <= 0 for r in rates_list):
        raise ScenarioError("rates must be positive")

    balances = [pool_balance for _ in range(n_coins)]
    rows: list[dict[str, object]] = []

    for amp in amps_list:
        for dx in trade_sizes_list:
            try:
                dy = quote_dy(
                    i,
                    j,
                    dx,
                    balances,
                    rates_list,
                    amp,
                    fee=fee,
                )
            except StableSwapMathError as exc:
                raise ScenarioError(f"quote failed for amp={amp}, dx={dx}: {exc}") from exc

            dy_over_dx = dy / dx
            slippage = 1.0 - dy_over_dx

            rows.append(
                {
                    "amp": amp,
                    "A": amp / A_PRECISION,
                    "trade_size": dx,
                    "trade_size_pct": dx / pool_balance,
                    "dy": dy,
                    "dy_over_dx": dy_over_dx,
                    "slippage": slippage,
                    "slippage_bps": slippage * 10_000,
                    "fee": fee,
                }
            )

    return pd.DataFrame(rows)


def dynamic_fee_imbalance_grid(
    *,
    ratios: Sequence[float] | None = None,
    multipliers: Sequence[int] = (
        FEE_DENOMINATOR,
        2 * FEE_DENOMINATOR,
        5 * FEE_DENOMINATOR,
        10 * FEE_DENOMINATOR,
    ),
    total_xp: int = 2 * 10**18,
    base_fee: int = 4_000_000,
) -> pd.DataFrame:
    """
    Generate a DataFrame showing how dynamic fee changes with imbalance.

    Parameters
    ----------
    ratios:
        Values for xpi / (xpi + xpj). Values must be between 0 and 1.
        If omitted, a symmetric sweep from 5% to 95% is used.
    multipliers:
        Off-peg fee multipliers in Curve fee precision.
    total_xp:
        xpi + xpj.
    base_fee:
        Base fee in Curve fee precision.

    Returns
    -------
    pandas.DataFrame
        Columns:
        - ratio
        - xpi
        - xpj
        - imbalance
        - multiplier
        - multiplier_x
        - effective_fee
        - effective_fee_bps
    """

    total_xp = _validate_positive_int("total_xp", total_xp)
    base_fee = int(base_fee)

    if base_fee < 0:
        raise ScenarioError("base_fee must be non-negative")

    if ratios is None:
        ratios_list = [x / 100 for x in range(5, 96, 5)]
    else:
        ratios_list = _as_float_list(ratios)

    multipliers_list = [int(m) for m in multipliers]
    if not multipliers_list:
        raise ScenarioError("multipliers must be non-empty")
    if any(m <= 0 for m in multipliers_list):
        raise ScenarioError("multipliers must be positive")

    rows: list[dict[str, object]] = []

    for ratio in ratios_list:
        if ratio <= 0.0 or ratio >= 1.0:
            continue

        xpi = int(total_xp * ratio)
        xpj = total_xp - xpi

        if xpi <= 0 or xpj <= 0:
            continue

        imbalance_scaled = imbalance_ratio(xpi, xpj)

        for multiplier in multipliers_list:
            effective_fee = dynamic_fee(
                xpi,
                xpj,
                base_fee,
                multiplier,
            )

            rows.append(
                {
                    "ratio": ratio,
                    "xpi": xpi,
                    "xpj": xpj,
                    "imbalance": imbalance_scaled / PRECISION,
                    "imbalance_scaled": imbalance_scaled,
                    "multiplier": multiplier,
                    "multiplier_x": multiplier / FEE_DENOMINATOR,
                    "base_fee": base_fee,
                    "base_fee_bps": fee_to_bps(base_fee),
                    "effective_fee": effective_fee,
                    "effective_fee_bps": fee_to_bps(effective_fee),
                }
            )

    return pd.DataFrame(rows)


def quote_staleness_rate_change_grid(
    *,
    rate_changes: Sequence[float] | None = None,
    amp: int = 100 * A_PRECISION,
    balances: Sequence[int] = (10**18, 10**18),
    base_rates: Sequence[int] = (PRECISION, PRECISION),
    dx: int = 10**15,
    fee: int = 0,
) -> pd.DataFrame:
    """
    Generate quote/execution staleness scenarios under rate changes.

    This models a common integration issue:

    1. Quote is computed using old rates.
    2. Execution happens after one token's rate changes.
    3. The quote becomes stale.

    Two directions are modeled:

    - output_rate_changes:
        swap coin0 -> coin1, rate[1] changes between quote and execution.

    - input_rate_changes:
        swap coin1 -> coin0, rate[1] changes between quote and execution.

    Parameters
    ----------
    rate_changes:
        Multiplicative changes to token1's rate.
        Example: 1.05 means token1 rate increases by 5%.
    amp:
        Amplification value using A_PRECISION.
    balances:
        Raw balances.
    base_rates:
        Initial rates.
    dx:
        Raw input amount.
    fee:
        Optional fee in Curve fee precision.

    Returns
    -------
    pandas.DataFrame
        Columns:
        - direction
        - rate_change
        - quoted_dy
        - executed_dy
        - error
        - error_pct_of_quote
    """

    if rate_changes is None:
        rate_changes_list = [
            0.90,
            0.95,
            0.99,
            1.00,
            1.01,
            1.05,
            1.10,
        ]
    else:
        rate_changes_list = _as_float_list(rate_changes)

    amp = _validate_positive_int("amp", amp)
    dx = _validate_positive_int("dx", dx)

    balances_list = [int(x) for x in balances]
    base_rates_list = [int(x) for x in base_rates]

    if len(balances_list) != 2 or len(base_rates_list) != 2:
        raise ScenarioError("quote_staleness_rate_change_grid currently expects 2 coins")
    if any(x <= 0 for x in balances_list):
        raise ScenarioError("balances must be positive")
    if any(r <= 0 for r in base_rates_list):
        raise ScenarioError("base_rates must be positive")

    rows: list[dict[str, object]] = []

    for rate_change in rate_changes_list:
        if rate_change <= 0:
            raise ScenarioError("rate_changes must be positive")

        new_rate_1 = int(base_rates_list[1] * rate_change)
        new_rates = [base_rates_list[0], new_rate_1]

        # Case 1: token1 is output. Quote uses old output rate.
        quoted_output = quote_dy(
            0,
            1,
            dx,
            balances_list,
            base_rates_list,
            amp,
            fee=fee,
        )
        executed_output = quote_dy(
            0,
            1,
            dx,
            balances_list,
            new_rates,
            amp,
            fee=fee,
        )

        rows.append(
            _quote_staleness_row(
                direction="output_rate_changes",
                rate_change=rate_change,
                quoted_dy=quoted_output,
                executed_dy=executed_output,
            )
        )

        # Case 2: token1 is input. Quote uses old input rate.
        quoted_input = quote_dy(
            1,
            0,
            dx,
            balances_list,
            base_rates_list,
            amp,
            fee=fee,
        )
        executed_input = quote_dy(
            1,
            0,
            dx,
            balances_list,
            new_rates,
            amp,
            fee=fee,
        )

        rows.append(
            _quote_staleness_row(
                direction="input_rate_changes",
                rate_change=rate_change,
                quoted_dy=quoted_input,
                executed_dy=executed_input,
            )
        )

    return pd.DataFrame(rows)


def _quote_staleness_row(
    *,
    direction: str,
    rate_change: float,
    quoted_dy: int,
    executed_dy: int,
) -> dict[str, object]:
    error = quoted_dy - executed_dy

    if quoted_dy == 0:
        error_pct_of_quote = 0.0
    else:
        error_pct_of_quote = error / quoted_dy

    return {
        "direction": direction,
        "rate_change": rate_change,
        "quoted_dy": quoted_dy,
        "executed_dy": executed_dy,
        "error": error,
        "error_pct_of_quote": error_pct_of_quote,
        "abs_error": abs(error),
        "abs_error_pct_of_quote": abs(error_pct_of_quote),
    }


def summarize_by_group(
    df: pd.DataFrame,
    *,
    group_col: str,
    value_col: str,
) -> pd.DataFrame:
    """
    Small helper for notebook summaries.

    Returns count, min, max, mean for a selected value column grouped by group_col.
    """

    if group_col not in df.columns:
        raise ScenarioError(f"group_col not found: {group_col}")
    if value_col not in df.columns:
        raise ScenarioError(f"value_col not found: {value_col}")

    return (
        df.groupby(group_col)[value_col]
        .agg(["count", "min", "max", "mean"])
        .reset_index()
    )
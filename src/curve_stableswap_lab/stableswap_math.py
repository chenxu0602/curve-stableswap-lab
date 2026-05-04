"""
Minimal Python implementation of Curve StableSwap math.

This module is intended for research, testing, and simulation notebooks.
It is not production pricing code and does not attempt to implement the
entire Curve StableSwap / StableSwap NG system.

The core goal is to mirror the integer-style math used by StableSwap's
`get_D`, `get_y`, and `get_y_D` functions closely enough for small
characterization tests and simulation artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


A_PRECISION = 100
PRECISION = 10**18
MAX_ITERATIONS = 255


class StableSwapMathError(ValueError):
    """Raised when StableSwap math receives invalid inputs or does not converge."""


def _validate_xp(xp: Sequence[int]) -> list[int]:
    if len(xp) == 0:
        raise StableSwapMathError("xp must contain at least one coin")

    out = [int(x) for x in xp]

    for idx, x in enumerate(out):
        if x < 0:
            raise StableSwapMathError(f"xp[{idx}] must be non-negative")

    return out


def get_D(xp: Sequence[int], amp: int, *, max_iterations: int = MAX_ITERATIONS) -> int:
    """
    Compute the StableSwap invariant D.

    Parameters
    ----------
    xp:
        Normalized balances in value-space.
    amp:
        Amplification coefficient using Curve's A_PRECISION convention.
        For example, A = 20 is usually passed as 20 * A_PRECISION.
    max_iterations:
        Newton iteration cap.

    Returns
    -------
    int
        StableSwap invariant D.

    Notes
    -----
    Mirrors the canonical integer iteration:

        D_P = D
        for x in xp:
            D_P = D_P * D / x
        D_P /= n**n

        D = (
            (Ann * S / A_PRECISION + D_P * n) * D
            /
            ((Ann - A_PRECISION) * D / A_PRECISION + (n + 1) * D_P)
        )

    where Ann = amp * n.
    """

    xp_list = _validate_xp(xp)
    amp = int(amp)

    if amp <= 0:
        raise StableSwapMathError("amp must be positive")

    n_coins = len(xp_list)
    S = sum(xp_list)

    if S == 0:
        return 0

    D = S
    Ann = amp * n_coins

    for _ in range(max_iterations):
        D_P = D

        for x in xp_list:
            if x == 0:
                raise StableSwapMathError("xp contains zero while total sum is non-zero")
            D_P = (D_P * D) // x

        D_P //= n_coins**n_coins

        D_prev = D

        numerator = ((Ann * S) // A_PRECISION + D_P * n_coins) * D
        denominator = (
            ((Ann - A_PRECISION) * D) // A_PRECISION
            + (n_coins + 1) * D_P
        )

        if denominator == 0:
            raise StableSwapMathError("zero denominator in get_D")

        D = numerator // denominator

        if abs(D - D_prev) <= 1:
            return D

    raise StableSwapMathError("get_D did not converge")


def get_y(
    i: int,
    j: int,
    x: int,
    xp: Sequence[int],
    amp: int,
    D: int | None = None,
    *,
    max_iterations: int = MAX_ITERATIONS,
) -> int:
    """
    Calculate the new balance y of coin j after setting coin i balance to x.

    This is the core StableSwap swap equation solver.

    Parameters
    ----------
    i:
        Input coin index.
    j:
        Output coin index.
    x:
        New normalized balance of coin i after input.
    xp:
        Current normalized balances.
    amp:
        Amplification coefficient using Curve's A_PRECISION convention.
    D:
        Optional invariant value. If omitted, it is computed from xp.
    max_iterations:
        Newton iteration cap.

    Returns
    -------
    int
        New normalized balance of coin j.
    """

    xp_list = _validate_xp(xp)
    amp = int(amp)
    x = int(x)

    n_coins = len(xp_list)

    if i == j:
        raise StableSwapMathError("i and j must be different")
    if i < 0 or i >= n_coins:
        raise StableSwapMathError("i out of range")
    if j < 0 or j >= n_coins:
        raise StableSwapMathError("j out of range")
    if x <= 0:
        raise StableSwapMathError("x must be positive")
    if amp <= 0:
        raise StableSwapMathError("amp must be positive")

    if D is None:
        D = get_D(xp_list, amp, max_iterations=max_iterations)
    else:
        D = int(D)

    S_ = 0
    c = D
    Ann = amp * n_coins

    for idx in range(n_coins):
        if idx == i:
            _x = x
        elif idx == j:
            continue
        else:
            _x = xp_list[idx]

        if _x <= 0:
            raise StableSwapMathError("non-positive balance in get_y")

        S_ += _x
        c = (c * D) // (_x * n_coins)

    if Ann == 0:
        raise StableSwapMathError("zero Ann in get_y")

    c = (c * D * A_PRECISION) // (Ann * n_coins)
    b = S_ + (D * A_PRECISION) // Ann

    y = D

    for _ in range(max_iterations):
        y_prev = y

        denominator = 2 * y + b - D
        if denominator == 0:
            raise StableSwapMathError("zero denominator in get_y")

        y = (y * y + c) // denominator

        if abs(y - y_prev) <= 1:
            return y

    raise StableSwapMathError("get_y did not converge")


def get_y_D(
    amp: int,
    i: int,
    xp: Sequence[int],
    D: int,
    *,
    max_iterations: int = MAX_ITERATIONS,
) -> int:
    """
    Calculate the new balance y of coin i given a reduced target invariant D.

    This is used for one-coin withdrawal style calculations.

    Parameters
    ----------
    amp:
        Amplification coefficient using Curve's A_PRECISION convention.
    i:
        Coin index to solve for.
    xp:
        Current normalized balances.
    D:
        Target invariant.
    max_iterations:
        Newton iteration cap.

    Returns
    -------
    int
        New normalized balance of coin i.
    """

    xp_list = _validate_xp(xp)
    amp = int(amp)
    D = int(D)

    n_coins = len(xp_list)

    if i < 0 or i >= n_coins:
        raise StableSwapMathError("i out of range")
    if amp <= 0:
        raise StableSwapMathError("amp must be positive")
    if D <= 0:
        raise StableSwapMathError("D must be positive")

    S_ = 0
    c = D
    Ann = amp * n_coins

    for idx in range(n_coins):
        if idx == i:
            continue

        _x = xp_list[idx]
        if _x <= 0:
            raise StableSwapMathError("non-positive balance in get_y_D")

        S_ += _x
        c = (c * D) // (_x * n_coins)

    c = (c * D * A_PRECISION) // (Ann * n_coins)
    b = S_ + (D * A_PRECISION) // Ann

    y = D

    for _ in range(max_iterations):
        y_prev = y

        denominator = 2 * y + b - D
        if denominator == 0:
            raise StableSwapMathError("zero denominator in get_y_D")

        y = (y * y + c) // denominator

        if abs(y - y_prev) <= 1:
            return y

    raise StableSwapMathError("get_y_D did not converge")


def xp_from_balances(balances: Sequence[int], rates: Sequence[int]) -> list[int]:
    """
    Convert raw balances into normalized xp balances.

    xp[i] = balances[i] * rates[i] // PRECISION
    """

    if len(balances) != len(rates):
        raise StableSwapMathError("balances and rates must have the same length")

    xp: list[int] = []

    for idx, (balance, rate) in enumerate(zip(balances, rates, strict=True)):
        balance = int(balance)
        rate = int(rate)

        if balance < 0:
            raise StableSwapMathError(f"balance[{idx}] must be non-negative")
        if rate <= 0:
            raise StableSwapMathError(f"rate[{idx}] must be positive")

        xp.append((balance * rate) // PRECISION)

    return xp


def quote_dy_xp(
    i: int,
    j: int,
    dx_xp: int,
    xp: Sequence[int],
    amp: int,
    *,
    fee: int = 0,
    fee_denominator: int = 10**10,
) -> int:
    """
    Quote output amount in xp units.

    This function works entirely in normalized xp space.

    Parameters
    ----------
    dx_xp:
        Input amount already converted into xp units.
    fee:
        Fee in Curve-style precision. If fee=0, no fee is applied.

    Returns
    -------
    int
        Output amount in xp units after fee.
    """

    xp_list = _validate_xp(xp)
    dx_xp = int(dx_xp)

    if dx_xp <= 0:
        raise StableSwapMathError("dx_xp must be positive")
    if fee < 0:
        raise StableSwapMathError("fee must be non-negative")
    if fee_denominator <= 0:
        raise StableSwapMathError("fee_denominator must be positive")

    D = get_D(xp_list, amp)
    x = xp_list[i] + dx_xp
    y = get_y(i, j, x, xp_list, amp, D)

    # Curve implementations often subtract 1 as a rounding guard.
    dy = xp_list[j] - y - 1

    if dy < 0:
        raise StableSwapMathError("negative dy")

    if fee > 0:
        dy_fee = (dy * fee) // fee_denominator
        dy -= dy_fee

    return dy


def quote_dy(
    i: int,
    j: int,
    dx: int,
    balances: Sequence[int],
    rates: Sequence[int],
    amp: int,
    *,
    fee: int = 0,
    fee_denominator: int = 10**10,
) -> int:
    """
    Quote output amount in raw token units.

    This converts balances into xp, converts dx into xp using rates[i],
    solves StableSwap in xp space, then converts dy back into raw units
    using rates[j].
    """

    if len(balances) != len(rates):
        raise StableSwapMathError("balances and rates must have the same length")

    dx = int(dx)
    if dx <= 0:
        raise StableSwapMathError("dx must be positive")

    rates_list = [int(r) for r in rates]
    if rates_list[i] <= 0 or rates_list[j] <= 0:
        raise StableSwapMathError("rates must be positive")

    xp = xp_from_balances(balances, rates_list)
    dx_xp = (dx * rates_list[i]) // PRECISION

    dy_xp = quote_dy_xp(
        i,
        j,
        dx_xp,
        xp,
        amp,
        fee=fee,
        fee_denominator=fee_denominator,
    )

    return (dy_xp * PRECISION) // rates_list[j]


@dataclass(frozen=True)
class SwapQuote:
    """
    Structured swap quote result for simulation notebooks.
    """

    i: int
    j: int
    dx: int
    dy: int
    amp: int
    balances: tuple[int, ...]
    rates: tuple[int, ...]
    xp: tuple[int, ...]
    D: int


def quote_swap(
    i: int,
    j: int,
    dx: int,
    balances: Sequence[int],
    rates: Sequence[int],
    amp: int,
    *,
    fee: int = 0,
    fee_denominator: int = 10**10,
) -> SwapQuote:
    """
    Return a structured quote for simulation notebooks.
    """

    xp = xp_from_balances(balances, rates)
    dy = quote_dy(
        i,
        j,
        dx,
        balances,
        rates,
        amp,
        fee=fee,
        fee_denominator=fee_denominator,
    )

    return SwapQuote(
        i=i,
        j=j,
        dx=int(dx),
        dy=int(dy),
        amp=int(amp),
        balances=tuple(int(x) for x in balances),
        rates=tuple(int(x) for x in rates),
        xp=tuple(xp),
        D=get_D(xp, amp),
    )
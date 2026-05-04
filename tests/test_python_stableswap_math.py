import pytest

from curve_stableswap_lab.stableswap_math import (
    A_PRECISION,
    PRECISION,
    StableSwapMathError,
    get_D,
    get_y,
    get_y_D,
    quote_dy,
    quote_dy_xp,
    quote_swap,
    xp_from_balances,
)


def test_get_D_zero_balances_returns_zero():
    assert get_D([0, 0, 0], 100 * A_PRECISION) == 0


def test_get_D_balanced_pool_is_close_to_sum():
    xp = [10**18, 10**18, 10**18]
    D = get_D(xp, 100 * A_PRECISION)

    assert abs(D - sum(xp)) <= 1


def test_get_D_is_symmetric_under_coin_permutation():
    amp = 100 * A_PRECISION

    xp1 = [10**18, 2 * 10**18, 3 * 10**18]
    xp2 = [3 * 10**18, 10**18, 2 * 10**18]
    xp3 = [2 * 10**18, 3 * 10**18, 10**18]

    assert get_D(xp1, amp) == get_D(xp2, amp)
    assert get_D(xp2, amp) == get_D(xp3, amp)


def test_get_D_increases_when_balances_increase():
    amp = 100 * A_PRECISION

    D1 = get_D([10**18, 10**18, 10**18], amp)
    D2 = get_D([2 * 10**18, 2 * 10**18, 2 * 10**18], amp)

    assert D2 > D1
    assert abs(D2 - 2 * D1) <= 2


def test_get_D_extreme_imbalance_converges():
    amp = 1000

    D = get_D([10**23, 10**18], amp)

    assert D == 9010395375710532394006


def test_get_D_rejects_negative_balance():
    with pytest.raises(StableSwapMathError):
        get_D([10**18, -1], 100 * A_PRECISION)


def test_get_D_rejects_zero_balance_when_sum_nonzero():
    with pytest.raises(StableSwapMathError):
        get_D([10**18, 0], 100 * A_PRECISION)


def test_get_y_preserves_invariant_within_rounding():
    amp = 100 * A_PRECISION
    xp = [10**18, 10**18, 10**18]
    D0 = get_D(xp, amp)

    dx = 10**15
    x_new = xp[0] + dx
    y = get_y(0, 1, x_new, xp, amp, D0)

    xp_after = xp.copy()
    xp_after[0] = x_new
    xp_after[1] = y

    D1 = get_D(xp_after, amp)

    assert abs(D1 - D0) <= 1


@pytest.mark.parametrize("amp_small, amp_large", [(20 * A_PRECISION, 500 * A_PRECISION)])
def test_larger_A_reduces_near_peg_slippage(amp_small, amp_large):
    xp = [10**18, 10**18, 10**18]
    dx = 10**15

    y_small_a = get_y(0, 1, xp[0] + dx, xp, amp_small)
    y_large_a = get_y(0, 1, xp[0] + dx, xp, amp_large)

    dy_small_a = xp[1] - y_small_a
    dy_large_a = xp[1] - y_large_a

    slippage_small = dx - dy_small_a
    slippage_large = dx - dy_large_a

    assert dy_large_a >= dy_small_a
    assert slippage_large <= slippage_small


def test_get_y_rejects_same_coin():
    with pytest.raises(StableSwapMathError):
        get_y(0, 0, 2 * 10**18, [10**18, 10**18], 100 * A_PRECISION)


def test_get_y_rejects_out_of_range_index():
    with pytest.raises(StableSwapMathError):
        get_y(0, 2, 2 * 10**18, [10**18, 10**18], 100 * A_PRECISION)


def test_get_y_D_reduces_selected_coin_balance_when_D_reduced():
    amp = 100 * A_PRECISION
    xp = [10**18, 10**18, 10**18]

    D0 = get_D(xp, amp)
    D1 = D0 * 9 // 10

    y = get_y_D(amp, 1, xp, D1)

    assert y < xp[1]


def test_get_y_D_preserves_target_D_within_rounding():
    amp = 100 * A_PRECISION
    xp = [10**18, 10**18, 10**18]

    D0 = get_D(xp, amp)
    target_D = D0 * 9 // 10

    y = get_y_D(amp, 1, xp, target_D)

    xp_after = xp.copy()
    xp_after[1] = y

    D_after = get_D(xp_after, amp)

    assert abs(D_after - target_D) <= 1


def test_xp_from_balances_uses_rates():
    balances = [10**18, 10**6]
    rates = [10**18, 10**30]

    xp = xp_from_balances(balances, rates)

    assert xp == [10**18, 10**18]


def test_xp_from_balances_rejects_length_mismatch():
    with pytest.raises(StableSwapMathError):
        xp_from_balances([10**18], [10**18, 10**18])


def test_xp_from_balances_rejects_zero_rate():
    with pytest.raises(StableSwapMathError):
        xp_from_balances([10**18], [0])


def test_quote_dy_xp_returns_positive_output_near_peg():
    amp = 100 * A_PRECISION
    xp = [10**18, 10**18, 10**18]

    dy = quote_dy_xp(
        0,
        1,
        10**15,
        xp,
        amp,
        fee=0,
    )

    assert dy > 0
    assert dy <= 10**15


def test_quote_dy_xp_fee_reduces_output():
    amp = 100 * A_PRECISION
    xp = [10**18, 10**18, 10**18]
    dx_xp = 10**15

    dy_no_fee = quote_dy_xp(0, 1, dx_xp, xp, amp, fee=0)
    dy_with_fee = quote_dy_xp(0, 1, dx_xp, xp, amp, fee=4_000_000)

    assert dy_with_fee < dy_no_fee


def test_quote_dy_raw_units_with_equal_rates():
    amp = 100 * A_PRECISION
    balances = [10**18, 10**18]
    rates = [10**18, 10**18]
    dx = 10**15

    dy = quote_dy(0, 1, dx, balances, rates, amp, fee=0)

    assert dy > 0
    assert dy <= dx


def test_quote_dy_raw_units_with_different_output_rate():
    amp = 100 * A_PRECISION

    # coin 1 has rate 2e18, so one raw unit of coin1 corresponds to
    # twice the normalized value. For the same xp output, raw dy should be smaller.
    balances = [10**18, 5 * 10**17]
    rates = [10**18, 2 * 10**18]
    dx = 10**15

    dy = quote_dy(0, 1, dx, balances, rates, amp, fee=0)

    assert dy > 0
    assert dy < dx


def test_quote_swap_returns_structured_result():
    amp = 100 * A_PRECISION
    balances = [10**18, 10**18]
    rates = [10**18, 10**18]
    dx = 10**15

    quote = quote_swap(0, 1, dx, balances, rates, amp)

    assert quote.i == 0
    assert quote.j == 1
    assert quote.dx == dx
    assert quote.dy > 0
    assert quote.amp == amp
    assert quote.balances == tuple(balances)
    assert quote.rates == tuple(rates)
    assert quote.xp == tuple(balances)
    assert quote.D == get_D(balances, amp)


def test_quote_dy_rejects_invalid_dx():
    with pytest.raises(StableSwapMathError):
        quote_dy(
            0,
            1,
            0,
            [10**18, 10**18],
            [10**18, 10**18],
            100 * A_PRECISION,
        )


def test_quote_dy_rejects_zero_rate():
    with pytest.raises(StableSwapMathError):
        quote_dy(
            0,
            1,
            10**15,
            [10**18, 10**18],
            [10**18, 0],
            100 * A_PRECISION,
        )
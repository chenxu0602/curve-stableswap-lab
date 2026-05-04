# tests/test_stableswap_math.py

import pytest


def test_get_D_zero_if_all_zero(math_harness):
    assert math_harness.get_D([0, 0, 0], 100 * 100) == 0


def test_get_D_balanced(math_harness):
    xp = [10**18, 10**18, 10**18]
    amp = 100 * 100

    D = math_harness.get_D(xp, amp)

    assert abs(D - 3 * 10**18) <= 3


def test_get_D_symmetric(math_harness):
    amp = 100 * 100
    xp1 = [10**18, 2 * 10**18, 3 * 10**18]
    xp2 = [3 * 10**18, 2 * 10**18, 10**18]

    d1 = math_harness.get_D(xp1, amp)
    d2 = math_harness.get_D(xp2, amp)

    assert abs(d1 - d2) <= 1


def test_get_D_monotonic_when_one_balance_increases(math_harness):
    amp = 100 * 100
    xp_low = [10**18, 10**18, 10**18]
    xp_high = [10**18, 12 * 10**17, 10**18]

    d_low = math_harness.get_D(xp_low, amp)
    d_high = math_harness.get_D(xp_high, amp)

    assert d_high > d_low


def test_get_y_output_balance_decreases(math_harness):
    amp = 100 * 100
    xp = [10**18, 10**18, 10**18]

    dx = 10**16
    x_new = xp[0] + dx

    y_new = math_harness.get_y(0, 1, x_new, xp, amp)

    assert y_new < xp[1]


def test_get_y_implies_positive_dy(math_harness):
    amp = 100 * 100
    xp = [10**18, 10**18, 10**18]

    dx = 10**16
    x_new = xp[0] + dx
    y_new = math_harness.get_y(0, 1, x_new, xp, amp)

    dy = xp[1] - y_new

    assert dy > 0
    assert dy < dx


def test_larger_dx_gives_larger_dy(math_harness):
    amp = 100 * 100
    xp = [10**18, 10**18, 10**18]

    dx_small = 10**15
    dx_large = 10**16

    y_small = math_harness.get_y(0, 1, xp[0] + dx_small, xp, amp)
    y_large = math_harness.get_y(0, 1, xp[0] + dx_large, xp, amp)

    dy_small = xp[1] - y_small
    dy_large = xp[1] - y_large

    assert dy_large > dy_small


def test_get_y_preserves_D_within_rounding(math_harness):
    amp = 100 * 100
    xp = [10**18, 10**18, 10**18]
    dx = 10**16

    d_before = math_harness.get_D(xp, amp)
    y_new = math_harness.get_y(0, 1, xp[0] + dx, xp, amp)
    xp_after = [xp[0] + dx, y_new, xp[2]]
    d_after = math_harness.get_D(xp_after, amp)

    assert abs(d_after - d_before) <= 1



@pytest.mark.parametrize("amp_small, amp_large", [(20 * 100, 500 * 100)])
def test_larger_A_reduces_near_peg_slippage(math_harness, amp_small, amp_large):
    xp = [10**18, 10**18, 10**18]
    dx = 10**15

    y_small_a = math_harness.get_y(0, 1, xp[0] + dx, xp, amp_small)
    y_large_a = math_harness.get_y(0, 1, xp[0] + dx, xp, amp_large)

    dy_small_a = xp[1] - y_small_a
    dy_large_a = xp[1] - y_large_a

    slippage_small = dx - dy_small_a
    slippage_large = dx - dy_large_a

    assert dy_large_a >= dy_small_a
    assert slippage_large <= slippage_small


def test_get_y_D_smaller_target_D_means_smaller_remaining_balance(math_harness):
    amp = 100 * 100
    xp = [10**18, 10**18, 10**18]

    d_full = math_harness.get_D(xp, amp)
    d_reduced = d_full - 2 * 10**16

    y_full = math_harness.get_y_D(1, xp, d_full, amp)
    y_reduced = math_harness.get_y_D(1, xp, d_reduced, amp)

    assert abs(y_full - xp[1]) <= 1
    assert y_reduced < y_full


def test_dynamic_fee_balanced_equals_base_fee(math_harness):
    fee = 4_000_000
    offpeg_multiplier = 20_000_000_000
    xpi = 10**18
    xpj = 10**18

    dynamic_fee = math_harness.dynamic_fee(xpi, xpj, fee, offpeg_multiplier)

    assert dynamic_fee == fee


def test_dynamic_fee_rises_when_pool_is_imbalanced(math_harness):
    fee = 4_000_000
    offpeg_multiplier = 20_000_000_000

    balanced_fee = math_harness.dynamic_fee(10**18, 10**18, fee, offpeg_multiplier)
    imbalanced_fee = math_harness.dynamic_fee(2 * 10**18, 5 * 10**17, fee, offpeg_multiplier)

    assert imbalanced_fee > balanced_fee


def test_dynamic_fee_without_multiplier_falls_back_to_base_fee(math_harness):
    fee = 4_000_000
    xpi = 2 * 10**18
    xpj = 5 * 10**17

    assert math_harness.dynamic_fee(xpi, xpj, fee, 10**10) == fee

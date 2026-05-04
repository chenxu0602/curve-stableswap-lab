from pathlib import Path

import pytest
import boa


@pytest.fixture(scope="module")
def admin_fee_harness():
    return boa.load(str(Path("contracts/AdminFeeHarness.vy")))


def test_admin_fee_converted_from_xp_to_raw_units(admin_fee_harness):
    rate_j = 2 * 10**18
    dy_fee_xp = 10**18
    admin_fee = 5 * 10**9

    admin_raw = admin_fee_harness.admin_fee_raw_from_dy_fee_xp(dy_fee_xp, rate_j, admin_fee)

    assert admin_raw == 25 * 10**16


def test_admin_fee_equals_half_of_raw_fee_when_rate_is_1(admin_fee_harness):
    rate_j = 10**18
    dy_fee_xp = 8 * 10**17
    admin_fee = 5 * 10**9

    admin_raw = admin_fee_harness.admin_fee_raw_from_dy_fee_xp(dy_fee_xp, rate_j, admin_fee)

    assert admin_raw == 4 * 10**17


def test_admin_fee_raw_amount_shrinks_when_output_rate_is_higher(admin_fee_harness):
    dy_fee_xp = 10**18
    admin_fee = 5 * 10**9

    raw_at_par = admin_fee_harness.admin_fee_raw_from_dy_fee_xp(dy_fee_xp, 10**18, admin_fee)
    raw_at_double_rate = admin_fee_harness.admin_fee_raw_from_dy_fee_xp(dy_fee_xp, 2 * 10**18, admin_fee)

    assert raw_at_double_rate < raw_at_par
    assert raw_at_double_rate == raw_at_par // 2


def test_raw_xp_roundtrip_is_rate_consistent(admin_fee_harness):
    raw_amount = 3 * 10**17
    rate = 15 * 10**17

    xp_amount = admin_fee_harness.raw_to_xp(raw_amount, rate)
    roundtrip_raw = admin_fee_harness.xp_to_raw(xp_amount, rate)

    assert xp_amount == 45 * 10**16
    assert roundtrip_raw == raw_amount

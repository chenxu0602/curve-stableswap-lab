import pytest

from curve_stableswap_lab.dynamic_fee import (
    FEE_DENOMINATOR,
    DynamicFeeError,
    balance_factor_scaled,
    dynamic_fee,
    dynamic_fee_curve,
    dynamic_fee_point,
    fee_to_bps,
    imbalance_ratio,
)


BASE_FEE = 4_000_000
TWO_X_MULTIPLIER = 2 * FEE_DENOMINATOR
FIVE_X_MULTIPLIER = 5 * FEE_DENOMINATOR


def test_dynamic_fee_balanced_equals_base_fee():
    xpi = 10**18
    xpj = 10**18

    fee = dynamic_fee(xpi, xpj, BASE_FEE, TWO_X_MULTIPLIER)

    assert fee == BASE_FEE


def test_dynamic_fee_without_multiplier_falls_back_to_base_fee_even_when_imbalanced():
    xpi = 2 * 10**18
    xpj = 5 * 10**17

    fee = dynamic_fee(xpi, xpj, BASE_FEE, FEE_DENOMINATOR)

    assert fee == BASE_FEE


def test_dynamic_fee_below_denominator_falls_back_to_base_fee():
    xpi = 2 * 10**18
    xpj = 5 * 10**17

    fee = dynamic_fee(xpi, xpj, BASE_FEE, FEE_DENOMINATOR - 1)

    assert fee == BASE_FEE


def test_dynamic_fee_imbalanced_is_greater_than_base_fee():
    xpi = 2 * 10**18
    xpj = 5 * 10**17

    fee = dynamic_fee(xpi, xpj, BASE_FEE, TWO_X_MULTIPLIER)

    assert fee > BASE_FEE


def test_dynamic_fee_more_imbalanced_is_higher():
    fee_mild = dynamic_fee(
        12 * 10**17,
        8 * 10**17,
        BASE_FEE,
        TWO_X_MULTIPLIER,
    )
    fee_extreme = dynamic_fee(
        19 * 10**17,
        1 * 10**17,
        BASE_FEE,
        TWO_X_MULTIPLIER,
    )

    assert fee_extreme > fee_mild
    assert fee_mild >= BASE_FEE


def test_dynamic_fee_higher_multiplier_increases_fee_when_imbalanced():
    xpi = 2 * 10**18
    xpj = 5 * 10**17

    fee_2x = dynamic_fee(xpi, xpj, BASE_FEE, TWO_X_MULTIPLIER)
    fee_5x = dynamic_fee(xpi, xpj, BASE_FEE, FIVE_X_MULTIPLIER)

    assert fee_5x > fee_2x
    assert fee_2x > BASE_FEE


def test_dynamic_fee_approaches_multiplier_cap_under_extreme_imbalance():
    xpi = 10**24
    xpj = 1

    fee = dynamic_fee(xpi, xpj, BASE_FEE, TWO_X_MULTIPLIER)

    # Extreme imbalance makes the balance factor approach zero, so the fee
    # approaches BASE_FEE * multiplier / denominator.
    expected_cap = BASE_FEE * TWO_X_MULTIPLIER // FEE_DENOMINATOR

    assert fee <= expected_cap
    assert expected_cap - fee <= 1


def test_balance_factor_scaled_is_one_at_balance():
    factor = balance_factor_scaled(10**18, 10**18)

    assert factor == 10**18


def test_balance_factor_scaled_decreases_with_imbalance():
    balanced = balance_factor_scaled(10**18, 10**18)
    mild = balance_factor_scaled(12 * 10**17, 8 * 10**17)
    extreme = balance_factor_scaled(19 * 10**17, 1 * 10**17)

    assert balanced > mild > extreme


def test_imbalance_ratio_is_zero_at_balance():
    assert imbalance_ratio(10**18, 10**18) == 0


def test_imbalance_ratio_increases_with_imbalance():
    mild = imbalance_ratio(12 * 10**17, 8 * 10**17)
    extreme = imbalance_ratio(19 * 10**17, 1 * 10**17)

    assert extreme > mild > 0


def test_dynamic_fee_point_contains_expected_fields():
    point = dynamic_fee_point(
        2 * 10**18,
        5 * 10**17,
        BASE_FEE,
        TWO_X_MULTIPLIER,
    )

    assert point.xpi == 2 * 10**18
    assert point.xpj == 5 * 10**17
    assert point.base_fee == BASE_FEE
    assert point.offpeg_fee_multiplier == TWO_X_MULTIPLIER
    assert point.effective_fee > BASE_FEE
    assert point.balance_factor > 0
    assert point.imbalance > 0


def test_dynamic_fee_curve_skips_zero_and_one_ratios():
    points = dynamic_fee_curve(
        [0.0, 0.25, 0.5, 0.75, 1.0],
        total_xp=2 * 10**18,
        base_fee=BASE_FEE,
        offpeg_fee_multiplier=TWO_X_MULTIPLIER,
    )

    assert len(points) == 3
    assert points[0].xpi == 5 * 10**17
    assert points[1].xpi == 10**18
    assert points[2].xpi == 15 * 10**17


def test_dynamic_fee_curve_has_base_fee_at_midpoint():
    points = dynamic_fee_curve(
        [0.25, 0.5, 0.75],
        total_xp=2 * 10**18,
        base_fee=BASE_FEE,
        offpeg_fee_multiplier=TWO_X_MULTIPLIER,
    )

    midpoint = points[1]

    assert midpoint.xpi == midpoint.xpj
    assert midpoint.effective_fee == BASE_FEE


def test_fee_to_bps_converts_curve_fee_precision():
    assert fee_to_bps(4_000_000) == pytest.approx(4.0)
    assert fee_to_bps(10_000_000) == pytest.approx(10.0)


@pytest.mark.parametrize(
    "xpi,xpj,base_fee,multiplier,error",
    [
        (0, 10**18, BASE_FEE, TWO_X_MULTIPLIER, "xpi"),
        (10**18, 0, BASE_FEE, TWO_X_MULTIPLIER, "xpj"),
        (10**18, 10**18, -1, TWO_X_MULTIPLIER, "base_fee"),
        (10**18, 10**18, BASE_FEE, 0, "offpeg"),
    ],
)
def test_dynamic_fee_rejects_invalid_inputs(xpi, xpj, base_fee, multiplier, error):
    with pytest.raises(DynamicFeeError, match=error):
        dynamic_fee(xpi, xpj, base_fee, multiplier)


def test_balance_factor_rejects_invalid_inputs():
    with pytest.raises(DynamicFeeError):
        balance_factor_scaled(0, 10**18)

    with pytest.raises(DynamicFeeError):
        balance_factor_scaled(10**18, 0)


def test_imbalance_ratio_rejects_invalid_inputs():
    with pytest.raises(DynamicFeeError):
        imbalance_ratio(0, 10**18)

    with pytest.raises(DynamicFeeError):
        imbalance_ratio(10**18, 0)


def test_dynamic_fee_curve_rejects_invalid_total_xp():
    with pytest.raises(DynamicFeeError):
        dynamic_fee_curve([0.5], total_xp=0)


def test_fee_to_bps_rejects_invalid_denominator():
    with pytest.raises(DynamicFeeError):
        fee_to_bps(BASE_FEE, fee_denominator=0)
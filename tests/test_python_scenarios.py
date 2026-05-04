import pandas as pd
import pytest

from curve_stableswap_lab.scenarios import (
    ScenarioError,
    amp_slippage_grid,
    dynamic_fee_imbalance_grid,
    quote_staleness_rate_change_grid,
    summarize_by_group,
)
from curve_stableswap_lab.stableswap_math import A_PRECISION, PRECISION


def test_amp_slippage_grid_returns_expected_columns():
    df = amp_slippage_grid(
        amps=[20 * A_PRECISION, 100 * A_PRECISION],
        trade_sizes=[10**14, 10**15],
        pool_balance=10**18,
        n_coins=2,
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4

    expected_columns = {
        "amp",
        "A",
        "trade_size",
        "trade_size_pct",
        "dy",
        "dy_over_dx",
        "slippage",
        "slippage_bps",
        "fee",
    }

    assert expected_columns.issubset(set(df.columns))


def test_amp_slippage_grid_higher_A_reduces_slippage_for_same_trade_size():
    dx = 10**15

    df = amp_slippage_grid(
        amps=[20 * A_PRECISION, 500 * A_PRECISION],
        trade_sizes=[dx],
        pool_balance=10**18,
        n_coins=2,
    )

    low_a = df[df["amp"] == 20 * A_PRECISION].iloc[0]
    high_a = df[df["amp"] == 500 * A_PRECISION].iloc[0]

    assert high_a["dy"] >= low_a["dy"]
    assert high_a["slippage"] <= low_a["slippage"]


def test_amp_slippage_grid_larger_trade_has_more_slippage():
    df = amp_slippage_grid(
        amps=[100 * A_PRECISION],
        trade_sizes=[10**14, 10**16],
        pool_balance=10**18,
        n_coins=2,
    )

    small_trade = df[df["trade_size"] == 10**14].iloc[0]
    large_trade = df[df["trade_size"] == 10**16].iloc[0]

    assert large_trade["slippage"] >= small_trade["slippage"]


def test_amp_slippage_grid_rejects_invalid_inputs():
    with pytest.raises(ScenarioError):
        amp_slippage_grid(pool_balance=0)

    with pytest.raises(ScenarioError):
        amp_slippage_grid(n_coins=1)

    with pytest.raises(ScenarioError):
        amp_slippage_grid(i=0, j=0)

    with pytest.raises(ScenarioError):
        amp_slippage_grid(amps=[])

    with pytest.raises(ScenarioError):
        amp_slippage_grid(trade_sizes=[])

    with pytest.raises(ScenarioError):
        amp_slippage_grid(rates=[PRECISION])


def test_dynamic_fee_imbalance_grid_returns_expected_columns():
    df = dynamic_fee_imbalance_grid(
        ratios=[0.25, 0.50, 0.75],
        multipliers=[10**10, 2 * 10**10],
        total_xp=2 * 10**18,
        base_fee=4_000_000,
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6

    expected_columns = {
        "ratio",
        "xpi",
        "xpj",
        "imbalance",
        "imbalance_scaled",
        "multiplier",
        "multiplier_x",
        "base_fee",
        "base_fee_bps",
        "effective_fee",
        "effective_fee_bps",
    }

    assert expected_columns.issubset(set(df.columns))


def test_dynamic_fee_imbalance_grid_midpoint_base_fee():
    base_fee = 4_000_000

    df = dynamic_fee_imbalance_grid(
        ratios=[0.5],
        multipliers=[10**10, 2 * 10**10, 5 * 10**10],
        total_xp=2 * 10**18,
        base_fee=base_fee,
    )

    assert set(df["effective_fee"]) == {base_fee}
    assert set(df["imbalance"]) == {0.0}


def test_dynamic_fee_imbalance_grid_fee_higher_when_more_imbalanced():
    base_fee = 4_000_000
    multiplier = 2 * 10**10

    df = dynamic_fee_imbalance_grid(
        ratios=[0.50, 0.75, 0.95],
        multipliers=[multiplier],
        total_xp=2 * 10**18,
        base_fee=base_fee,
    )

    balanced_fee = df[df["ratio"] == 0.50].iloc[0]["effective_fee"]
    mild_fee = df[df["ratio"] == 0.75].iloc[0]["effective_fee"]
    extreme_fee = df[df["ratio"] == 0.95].iloc[0]["effective_fee"]

    assert balanced_fee == base_fee
    assert mild_fee > balanced_fee
    assert extreme_fee > mild_fee


def test_dynamic_fee_imbalance_grid_rejects_invalid_inputs():
    with pytest.raises(ScenarioError):
        dynamic_fee_imbalance_grid(total_xp=0)

    with pytest.raises(ScenarioError):
        dynamic_fee_imbalance_grid(base_fee=-1)

    with pytest.raises(ScenarioError):
        dynamic_fee_imbalance_grid(ratios=[])

    with pytest.raises(ScenarioError):
        dynamic_fee_imbalance_grid(multipliers=[])

    with pytest.raises(ScenarioError):
        dynamic_fee_imbalance_grid(multipliers=[0])


def test_quote_staleness_rate_change_grid_returns_expected_columns():
    df = quote_staleness_rate_change_grid(
        rate_changes=[0.95, 1.00, 1.05],
        amp=100 * A_PRECISION,
        balances=[10**18, 10**18],
        base_rates=[PRECISION, PRECISION],
        dx=10**15,
        fee=0,
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6

    expected_columns = {
        "direction",
        "rate_change",
        "quoted_dy",
        "executed_dy",
        "error",
        "error_pct_of_quote",
        "abs_error",
        "abs_error_pct_of_quote",
    }

    assert expected_columns.issubset(set(df.columns))


def test_quote_staleness_rate_change_grid_no_error_when_rate_unchanged():
    df = quote_staleness_rate_change_grid(
        rate_changes=[1.00],
        amp=100 * A_PRECISION,
        balances=[10**18, 10**18],
        base_rates=[PRECISION, PRECISION],
        dx=10**15,
        fee=0,
    )

    assert len(df) == 2
    assert set(df["error"]) == {0}
    assert set(df["abs_error"]) == {0}


def test_quote_staleness_rate_change_grid_rate_change_creates_error():
    df = quote_staleness_rate_change_grid(
        rate_changes=[0.95, 1.05],
        amp=100 * A_PRECISION,
        balances=[10**18, 10**18],
        base_rates=[PRECISION, PRECISION],
        dx=10**15,
        fee=0,
    )

    assert (df["abs_error"] > 0).all()
    assert (df["abs_error_pct_of_quote"] > 0).all()


def test_quote_staleness_error_direction_differs_for_input_and_output_rate_change():
    df = quote_staleness_rate_change_grid(
        rate_changes=[1.05],
        amp=100 * A_PRECISION,
        balances=[10**18, 10**18],
        base_rates=[PRECISION, PRECISION],
        dx=10**15,
        fee=0,
    )

    output_case = df[df["direction"] == "output_rate_changes"].iloc[0]
    input_case = df[df["direction"] == "input_rate_changes"].iloc[0]

    assert output_case["error"] != 0
    assert input_case["error"] != 0

    # When token1's rate increases:
    # - if token1 is output, raw executed dy tends to be lower than stale quote
    # - if token1 is input, raw executed dy tends to be higher than stale quote
    assert output_case["error"] > 0
    assert input_case["error"] < 0


def test_quote_staleness_rate_change_grid_rejects_invalid_inputs():
    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(rate_changes=[])

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(rate_changes=[0])

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(amp=0)

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(dx=0)

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(balances=[10**18, 10**18, 10**18])

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(base_rates=[PRECISION, PRECISION, PRECISION])

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(balances=[10**18, 0])

    with pytest.raises(ScenarioError):
        quote_staleness_rate_change_grid(base_rates=[PRECISION, 0])


def test_summarize_by_group_returns_grouped_statistics():
    df = dynamic_fee_imbalance_grid(
        ratios=[0.25, 0.50, 0.75],
        multipliers=[10**10, 2 * 10**10],
        total_xp=2 * 10**18,
        base_fee=4_000_000,
    )

    summary = summarize_by_group(
        df,
        group_col="multiplier_x",
        value_col="effective_fee_bps",
    )

    assert isinstance(summary, pd.DataFrame)
    assert set(summary.columns) == {"multiplier_x", "count", "min", "max", "mean"}
    assert len(summary) == 2
    assert set(summary["count"]) == {3}


def test_summarize_by_group_rejects_missing_columns():
    df = dynamic_fee_imbalance_grid(
        ratios=[0.5],
        multipliers=[10**10],
    )

    with pytest.raises(ScenarioError):
        summarize_by_group(df, group_col="missing", value_col="effective_fee")

    with pytest.raises(ScenarioError):
        summarize_by_group(df, group_col="ratio", value_col="missing")
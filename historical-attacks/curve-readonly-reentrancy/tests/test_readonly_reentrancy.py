from pathlib import Path

import boa
import pytest


ROOT = Path("historical-attacks/curve-readonly-reentrancy")
PRECISION = 10**18


@pytest.fixture
def alice():
    return boa.env.generate_address()


def deploy_pool(lp_holder):
    return boa.load(
        str(ROOT / "contracts" / "VulnerableLPOraclePool.vy"),
        PRECISION,  # initial assets
        PRECISION,  # initial LP supply
        lp_holder,
    )


def deploy_victim(pool):
    return boa.load(
        str(ROOT / "contracts" / "OracleConsumerVictim.vy"),
        pool.address,
    )


def deploy_attacker(pool, victim):
    return boa.load(
        str(ROOT / "contracts" / "ReadOnlyReentrancyAttacker.vy"),
        pool.address,
        victim.address,
    )


def test_readonly_reentrancy_overvalues_lp_collateral_during_callback(alice):
    # ---------------------------------------------------------------------
    # Setup:
    # Pool starts at virtual price = 1.0.
    #
    # asset_balance = 1e18
    # total_supply  = 1e18
    # get_virtual_price() = 1e18
    # ---------------------------------------------------------------------

    pool = deploy_pool(alice)
    victim = deploy_victim(pool)
    attacker = deploy_attacker(pool, victim)

    assert pool.get_virtual_price() == PRECISION

    # Give attacker-contract LP balance in the toy pool.
    #
    # This is a test helper. In a production-like setup the attacker would
    # acquire LP tokens normally.
    pool.set_lp_balance_for_testing(attacker.address, PRECISION)

    # Attacker deposits 1 LP as collateral into the victim.
    #
    # The victim is intentionally simplified: it tracks collateral units
    # without modeling a real LP token transfer. The goal is to isolate
    # oracle-consumption behavior.
    attacker.prepare_collateral(PRECISION)

    normal_max_borrow = victim.max_borrow(attacker.address)

    # Victim uses 50% LTV:
    #
    # collateral_value = 1e18 LP * 1.0 virtual price = 1e18
    # max_borrow       = 50% * 1e18 = 0.5e18
    assert normal_max_borrow == 5 * 10**17
    assert victim.debt(attacker.address) == 0

    # ---------------------------------------------------------------------
    # Attack:
    #
    # remove_liquidity_with_callback(0.2e18):
    #
    # 1. pool reduces total_supply first:
    #      total_supply = 0.8e18
    #      asset_balance still = 1.0e18
    #
    # 2. callback fires before asset_balance is reduced:
    #      get_virtual_price = 1.0e18 / 0.8e18 = 1.25e18
    #
    # 3. attacker borrows using inflated collateral valuation:
    #      collateral_value = 1e18 LP * 1.25 = 1.25e18
    #      max_borrow = 50% * 1.25e18 = 0.625e18
    #
    # 4. pool finalizes asset_balance:
    #      asset_balance = 0.8e18
    #      total_supply  = 0.8e18
    #      virtual_price = 1.0e18 again
    # ---------------------------------------------------------------------

    inflated_borrow_amount = 625 * 10**15  # 0.625e18

    attacker.attack(
        2 * 10**17,          # burn amount = 0.2 LP
        inflated_borrow_amount,
    )

    # During callback the victim accepted the inflated borrow amount.
    assert victim.debt(attacker.address) == inflated_borrow_amount

    # After the pool finalizes, virtual price is coherent again.
    assert pool.get_virtual_price() == PRECISION

    # Under the final coherent price, the attacker should only be allowed
    # to borrow 0.5e18, but already borrowed 0.625e18.
    post_attack_max_borrow = victim.max_borrow(attacker.address)

    assert post_attack_max_borrow == normal_max_borrow
    assert victim.debt(attacker.address) > post_attack_max_borrow


def test_same_borrow_amount_reverts_without_inflated_virtual_price(alice):
    pool = deploy_pool(alice)
    victim = deploy_victim(pool)
    attacker = deploy_attacker(pool, victim)

    pool.set_lp_balance_for_testing(attacker.address, PRECISION)
    attacker.prepare_collateral(PRECISION)

    normal_max_borrow = victim.max_borrow(attacker.address)
    assert normal_max_borrow == 5 * 10**17

    # 0.625e18 is only accepted during the inflated callback state.
    # Under normal virtual price it should revert.
    with boa.reverts():
        attacker.borrow_directly(625 * 10**15)

    assert victim.debt(attacker.address) == 0


def test_safe_borrow_amount_succeeds_without_reentrancy(alice):
    pool = deploy_pool(alice)
    victim = deploy_victim(pool)
    attacker = deploy_attacker(pool, victim)

    pool.set_lp_balance_for_testing(attacker.address, PRECISION)
    attacker.prepare_collateral(PRECISION)

    normal_max_borrow = victim.max_borrow(attacker.address)
    assert normal_max_borrow == 5 * 10**17

    attacker.borrow_directly(normal_max_borrow)

    assert victim.debt(attacker.address) == normal_max_borrow
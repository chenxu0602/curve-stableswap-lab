from pathlib import Path

import boa
import pytest


ROOT = Path("historical-attacks/curve-readonly-reentrancy")
PRECISION = 10**18


@pytest.fixture
def alice():
    return boa.env.generate_address()


def deploy_safe_pool(lp_holder):
    return boa.load(
        str(ROOT / "contracts" / "SafeLPOraclePool.vy"),
        PRECISION,  # initial assets
        PRECISION,  # initial LP supply
        lp_holder,
    )


def deploy_recorder(pool):
    return boa.load(
        str(ROOT / "contracts" / "ReadOnlyPriceRecorder.vy"),
        pool.address,
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


def test_safe_ordering_does_not_inflate_virtual_price_during_callback(alice):
    pool = deploy_safe_pool(alice)
    recorder = deploy_recorder(pool)

    normal_price_before = pool.get_virtual_price()
    assert normal_price_before == PRECISION

    with boa.env.prank(alice):
        pool.remove_liquidity_with_callback(2 * 10**17, recorder.address)

    observed_during_callback = recorder.observed_price()
    normal_price_after = pool.get_virtual_price()

    assert observed_during_callback == normal_price_before
    assert normal_price_after == normal_price_before
    assert observed_during_callback == PRECISION


def test_safe_ordering_prevents_inflated_borrow_during_callback(alice):
    pool = deploy_safe_pool(alice)
    victim = deploy_victim(pool)
    attacker = deploy_attacker(pool, victim)

    assert pool.get_virtual_price() == PRECISION

    # Give attacker-contract LP balance in the toy pool.
    pool.set_lp_balance_for_testing(attacker.address, PRECISION)

    # Attacker deposits 1 LP as collateral into the victim.
    attacker.prepare_collateral(PRECISION)

    normal_max_borrow = victim.max_borrow(attacker.address)
    assert normal_max_borrow == 5 * 10**17
    assert victim.debt(attacker.address) == 0

    # In the vulnerable pool, this amount was accepted during the inflated
    # callback state:
    #
    # inflated virtual price = 1.25e18
    # inflated max borrow    = 0.625e18
    #
    # In the safe pool, callback observes coherent virtual price = 1.0e18,
    # so the same borrow attempt must fail.
    inflated_borrow_amount = 625 * 10**15

    with boa.reverts():
        attacker.attack(
            2 * 10**17,  # burn amount = 0.2 LP
            inflated_borrow_amount,
        )

    assert victim.debt(attacker.address) == 0
    assert pool.get_virtual_price() == PRECISION


def test_safe_ordering_still_allows_normal_borrow_limit(alice):
    pool = deploy_safe_pool(alice)
    victim = deploy_victim(pool)
    attacker = deploy_attacker(pool, victim)

    pool.set_lp_balance_for_testing(attacker.address, PRECISION)
    attacker.prepare_collateral(PRECISION)

    normal_max_borrow = victim.max_borrow(attacker.address)
    assert normal_max_borrow == 5 * 10**17

    attacker.borrow_directly(normal_max_borrow)

    assert victim.debt(attacker.address) == normal_max_borrow
    assert victim.debt(attacker.address) <= victim.max_borrow(attacker.address)
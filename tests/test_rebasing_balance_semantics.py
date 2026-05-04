from pathlib import Path

import boa


def deploy_token(name: str, symbol: str):
    return boa.load(str(Path("contracts/ERC20Mock.vy")), name, symbol, 18)


def deploy_harness(coin0, coin1, asset_types):
    return boa.load(
        str(Path("contracts/RebasingBalanceHarness.vy")),
        [coin0.address, coin1.address],
        asset_types,
    )


def test_plain_pool_balances_use_stored_balance_not_actual_surplus(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    harness.set_admin_balance(0, 10**17)

    coin0.mint(alice, 2 * 10**17)
    with boa.env.prank(alice):
        coin0.transfer(harness.address, 2 * 10**17)

    assert harness.actual_balance(0) == 12 * 10**17
    assert harness.stored_balances(0) == 10**18
    assert harness.balances() == [9 * 10**17, 0]


def test_rebasing_pool_balances_gulp_actual_balance_minus_admin():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [2, 0])

    coin0.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    harness.set_admin_balance(0, 10**17)
    coin0.rebase(harness.address, 2 * 10**17)

    assert harness.has_rebasing_asset() is True
    assert harness.actual_balance(0) == 12 * 10**17
    assert harness.stored_balances(0) == 10**18
    assert harness.balances() == [11 * 10**17, 0]


def test_plain_transfer_out_only_decrements_cached_stored_balance(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    coin0.mint(harness.address, 2 * 10**17)

    harness.transfer_out(0, 3 * 10**17, alice)

    assert coin0.balanceOf(alice) == 3 * 10**17
    assert harness.actual_balance(0) == 9 * 10**17
    assert harness.stored_balances(0) == 7 * 10**17


def test_rebasing_transfer_out_rewrites_stored_balance_from_actual(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [2, 0])

    coin0.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    coin0.rebase(harness.address, 2 * 10**17)

    harness.transfer_out(0, 3 * 10**17, alice)

    assert coin0.balanceOf(alice) == 3 * 10**17
    assert harness.actual_balance(0) == 9 * 10**17
    assert harness.stored_balances(0) == 9 * 10**17


def test_plain_proportional_exit_ignores_uninternalized_donation(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(harness.address, 10**18)
    coin1.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    harness.sync_stored_balance(1)
    harness.set_total_supply(2 * 10**18)

    coin0.mint(harness.address, 2 * 10**17)

    assert harness.actual_balance(0) == 12 * 10**17
    assert harness.stored_balances(0) == 10**18
    assert harness.preview_remove_liquidity(10**18) == [5 * 10**17, 5 * 10**17]


def test_rebasing_proportional_exit_gulps_rebased_balance():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [2, 0])

    coin0.mint(harness.address, 10**18)
    coin1.mint(harness.address, 10**18)
    harness.sync_stored_balance(0)
    harness.sync_stored_balance(1)
    harness.set_total_supply(2 * 10**18)

    coin0.rebase(harness.address, 2 * 10**17)

    assert harness.actual_balance(0) == 12 * 10**17
    assert harness.stored_balances(0) == 10**18
    assert harness.preview_remove_liquidity(10**18) == [6 * 10**17, 5 * 10**17]

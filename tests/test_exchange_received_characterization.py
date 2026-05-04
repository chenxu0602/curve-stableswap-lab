from pathlib import Path

import boa
import pytest


def deploy_token(name: str, symbol: str):
    return boa.load(
        str(Path("contracts/ERC20Mock.vy")),
        name,
        symbol,
        18,
    )


def deploy_harness(coin0, coin1, asset_types):
    return boa.load(
        str(Path("contracts/OptimisticTransferHarness.vy")),
        [coin0.address, coin1.address],
        asset_types,
    )


def test_exchange_received_consumes_prior_transfer_for_plain_assets(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(alice, 10**18)
    with boa.env.prank(alice):
        coin0.transfer(harness.address, 10**18)

    assert harness.preview_exchange_received(0) == 10**18
    assert harness.exchange_received(0) == 10**18
    assert harness.stored_balances(0) == 10**18


def test_exchange_received_characterizes_historical_surplus_as_current_input(alice, bob):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(bob, 7 * 10**17)
    with boa.env.prank(bob):
        coin0.transfer(harness.address, 7 * 10**17)

    coin0.mint(alice, 3 * 10**17)
    with boa.env.prank(alice):
        coin0.transfer(harness.address, 3 * 10**17)

    assert harness.preview_exchange_received(0) == 10**18
    assert harness.exchange_received(0) == 10**18
    assert harness.stored_balances(0) == 10**18


def test_exchange_received_merges_post_sync_donation_with_current_caller_input(alice, bob):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [0, 0])

    coin0.mint(bob, 5 * 10**17)
    with boa.env.prank(bob):
        coin0.transfer(harness.address, 5 * 10**17)
    harness.sync_stored_balance(0)

    coin0.mint(bob, 2 * 10**17)
    with boa.env.prank(bob):
        coin0.transfer(harness.address, 2 * 10**17)

    coin0.mint(alice, 3 * 10**17)
    with boa.env.prank(alice):
        coin0.transfer(harness.address, 3 * 10**17)

    assert harness.preview_exchange_received(0) == 5 * 10**17
    assert harness.exchange_received(0) == 5 * 10**17
    assert harness.stored_balances(0) == 10**18


def test_exchange_received_reverts_when_pool_contains_rebasing_asset(alice):
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [2, 0])

    coin0.mint(alice, 10**18)
    with boa.env.prank(alice):
        coin0.transfer(harness.address, 10**18)

    assert harness.has_rebasing_asset() is True
    with boa.reverts("rebasing asset"):
        harness.preview_exchange_received(0)
    with boa.reverts("rebasing asset"):
        harness.exchange_received(0)


def test_exchange_received_rebasing_drift_cannot_be_consumed_as_swap_input():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_harness(coin0, coin1, [2, 0])

    coin0.mint(harness.address, 5 * 10**17)
    harness.sync_stored_balance(0)
    coin0.rebase(harness.address, 2 * 10**17)

    assert coin0.balanceOf(harness.address) == 7 * 10**17
    assert harness.stored_balances(0) == 5 * 10**17

    with boa.reverts("rebasing asset"):
        harness.exchange_received(0)

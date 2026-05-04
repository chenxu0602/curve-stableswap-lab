from pathlib import Path

import boa


def deploy_token(name: str, symbol: str):
    return boa.load(str(Path("contracts/ERC20Mock.vy")), name, symbol, 18)


def deploy_harness():
    return boa.load(str(Path("contracts/MetaZapDustHarness.vy")))


def test_flush_full_balance_transfers_preexisting_dust_to_current_caller(alice, bob):
    token = deploy_token("Token", "TKN")
    harness = deploy_harness()

    token.mint(harness.address, 4 * 10**17)
    token.mint(alice, 6 * 10**17)
    with boa.env.prank(alice):
        token.transfer(harness.address, 6 * 10**17)

    assert harness.leftover(token.address) == 10**18
    paid = harness.flush_full_balance(token.address, bob)

    assert paid == 10**18
    assert token.balanceOf(bob) == 10**18
    assert harness.leftover(token.address) == 0


def test_flush_full_balance_characterizes_historical_balance_contamination(alice, bob):
    token = deploy_token("Token", "TKN")
    harness = deploy_harness()

    token.mint(harness.address, 2 * 10**17)
    paid_first = harness.flush_full_balance(token.address, alice)

    token.mint(harness.address, 3 * 10**17)
    paid_second = harness.flush_full_balance(token.address, bob)

    assert paid_first == 2 * 10**17
    assert paid_second == 3 * 10**17
    assert token.balanceOf(alice) == 2 * 10**17
    assert token.balanceOf(bob) == 3 * 10**17

from pathlib import Path

import boa


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def deploy_token(name: str, symbol: str):
    return boa.load(str(Path("contracts/ERC20Mock.vy")), name, symbol, 18)


def deploy_oracle(rate: int):
    return boa.load(str(Path("contracts/RateOracleMock.vy")), rate)


def deploy_vault(asset, name: str = "Vault Share", symbol: str = "vSHARE"):
    return boa.load(
        str(Path("contracts/ERC4626Mock.vy")),
        asset.address,
        name,
        symbol,
        18,
    )


def deploy_harness(balances, asset_types, rate_oracles, call_amount, scale_factor, amp=100 * 100, fee=4_000_000, offpeg=20_000_000_000):
    dummy0 = ZERO_ADDRESS if rate_oracles[0] is None else rate_oracles[0].address
    dummy1 = ZERO_ADDRESS if rate_oracles[1] is None else rate_oracles[1].address
    return boa.load(
        str(Path("contracts/QuoteExecutionHarness.vy")),
        balances,
        [10**18, 10**18],
        asset_types,
        [dummy0, dummy1],
        call_amount,
        scale_factor,
        amp,
        fee,
        offpeg,
    )


def test_oracle_quote_matches_execution_under_unchanged_state():
    oracle = deploy_oracle(10**18)
    harness = deploy_harness(
        [10**18, 10**18],
        [0, 1],
        [None, oracle],
        [0, 0],
        [0, 0],
    )

    quoted_dy = harness.get_dy(0, 1, 10**17)
    executed_dy = harness.exchange(0, 1, 10**17)

    assert executed_dy == quoted_dy


def test_oracle_quote_becomes_stale_after_rate_update():
    oracle = deploy_oracle(10**18)
    harness = deploy_harness(
        [10**18, 10**18],
        [0, 1],
        [None, oracle],
        [0, 0],
        [0, 0],
    )

    quoted_dy = harness.get_dy(0, 1, 10**17)
    oracle.set_rate(12 * 10**17)
    executed_dy = harness.exchange(0, 1, 10**17)

    assert executed_dy < quoted_dy


def test_erc4626_quote_matches_execution_without_intervening_donation(alice):
    underlying = deploy_token("Underlying", "UND")
    vault = deploy_vault(underlying)
    harness = deploy_harness(
        [10**18, 10**18],
        [0, 3],
        [None, vault],
        [0, 10**18],
        [0, 1],
    )

    underlying.mint(alice, 10**19)
    with boa.env.prank(alice):
        underlying.approve(vault.address, 10**19)
        vault.deposit(10**19, alice)

    quoted_dy = harness.get_dy(0, 1, 10**17)
    executed_dy = harness.exchange(0, 1, 10**17)

    assert executed_dy == quoted_dy


def test_erc4626_quote_becomes_stale_after_vault_donation(alice):
    underlying = deploy_token("Underlying", "UND")
    vault = deploy_vault(underlying)
    harness = deploy_harness(
        [10**18, 10**18],
        [0, 3],
        [None, vault],
        [0, 10**18],
        [0, 1],
    )

    underlying.mint(alice, 10**19)
    with boa.env.prank(alice):
        underlying.approve(vault.address, 10**19)
        vault.deposit(10**19, alice)

    quoted_dy = harness.get_dy(0, 1, 10**17)
    underlying.mint(vault.address, 5 * 10**18)
    executed_dy = harness.exchange(0, 1, 10**17)

    assert executed_dy < quoted_dy

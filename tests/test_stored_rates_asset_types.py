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


def deploy_rates_harness(coins, asset_types, rate_multipliers, rate_oracles, call_amount, scale_factor):
    return boa.load(
        str(Path("contracts/StoredRatesHarness.vy")),
        [coin.address for coin in coins],
        asset_types,
        rate_multipliers,
        rate_oracles,
        call_amount,
        scale_factor,
    )


def test_stored_rates_plain_assets_use_rate_multipliers_only():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    harness = deploy_rates_harness(
        [coin0, coin1],
        [0, 0],
        [10**18, 2 * 10**18],
        [ZERO_ADDRESS, ZERO_ADDRESS],
        [0, 0],
        [0, 0],
    )

    assert harness.stored_rates() == [10**18, 2 * 10**18]
    assert harness.xp_from_balances([3 * 10**18, 5 * 10**17]) == [3 * 10**18, 10**18]


def test_oracle_asset_updates_stored_rates_and_xp():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    oracle = deploy_oracle(105 * 10**16)
    harness = deploy_rates_harness(
        [coin0, coin1],
        [0, 1],
        [10**18, 10**18],
        [ZERO_ADDRESS, oracle.address],
        [0, 0],
        [0, 0],
    )

    assert harness.stored_rates() == [10**18, 105 * 10**16]
    assert harness.xp_from_balances([2 * 10**18, 3 * 10**18]) == [2 * 10**18, 315 * 10**16]

    oracle.set_rate(11 * 10**17)

    assert harness.stored_rates() == [10**18, 11 * 10**17]
    assert harness.xp_from_balances([2 * 10**18, 3 * 10**18]) == [2 * 10**18, 33 * 10**17]


def test_wrong_scale_oracle_is_characterized_as_unsafe_configuration():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    oracle = deploy_oracle(2_000_000)
    harness = deploy_rates_harness(
        [coin0, coin1],
        [0, 1],
        [10**18, 10**18],
        [ZERO_ADDRESS, oracle.address],
        [0, 0],
        [0, 0],
    )

    assert harness.stored_rates() == [10**18, 2_000_000]
    assert harness.xp_from_balances([10**18, 10**18]) == [10**18, 2_000_000]


def test_reverted_oracle_call_reverts_stored_rates():
    coin0 = deploy_token("Token0", "TK0")
    coin1 = deploy_token("Token1", "TK1")
    oracle = deploy_oracle(10**18)
    oracle.set_should_revert(True)
    harness = deploy_rates_harness(
        [coin0, coin1],
        [0, 1],
        [10**18, 10**18],
        [ZERO_ADDRESS, oracle.address],
        [0, 0],
        [0, 0],
    )

    with boa.reverts("oracle revert"):
        harness.stored_rates()


def test_erc4626_donation_increases_stored_rate_and_xp(alice):
    plain = deploy_token("Token0", "TK0")
    underlying = deploy_token("Underlying", "UND")
    vault = deploy_vault(underlying)
    harness = deploy_rates_harness(
        [plain, vault],
        [0, 3],
        [10**18, 10**18],
        [ZERO_ADDRESS, ZERO_ADDRESS],
        [0, 10**18],
        [0, 1],
    )

    underlying.mint(alice, 10**19)
    with boa.env.prank(alice):
        underlying.approve(vault.address, 10**19)
        vault.deposit(10**19, alice)

    assert vault.convertToAssets(10**18) == 10**18
    assert harness.stored_rates() == [10**18, 10**18]
    assert harness.xp_from_balances([0, 10**19]) == [0, 10**19]

    underlying.mint(vault.address, 5 * 10**18)

    assert vault.convertToAssets(10**18) == 15 * 10**17
    assert harness.stored_rates() == [10**18, 15 * 10**17]
    assert harness.xp_from_balances([0, 10**19]) == [0, 15 * 10**18]

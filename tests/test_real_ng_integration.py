from pathlib import Path
import os

import boa
from eth_utils import function_signature_to_4byte_selector


NG_ROOT = Path(
    os.getenv(
        "STABLESWAP_NG_ROOT",
        "/Users/chenxu/Work/protocol-security-lab/evm-playground/curve/stableswap-ng",
    )
)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ORACLE_METHOD_ID = function_signature_to_4byte_selector("exchangeRate()")
OFFPEG_FEE_MULTIPLIER = 20_000_000_000


def load_partial(*parts: str):
    return boa.load_partial(str(NG_ROOT.joinpath(*parts)))


def deploy_factory(owner, fee_receiver):
    gauge_impl = load_partial("contracts", "main", "LiquidityGauge.vy").deploy_as_blueprint()
    amm_impl = load_partial("contracts", "main", "CurveStableSwapNG.vy").deploy_as_blueprint()
    views_impl = load_partial("contracts", "main", "CurveStableSwapNGViews.vy").deploy()
    math_impl = load_partial("contracts", "main", "CurveStableSwapNGMath.vy").deploy()
    factory = load_partial("contracts", "main", "CurveStableSwapFactoryNG.vy").deploy(fee_receiver, owner)

    with boa.env.prank(owner):
        factory.set_gauge_implementation(gauge_impl.address)
        factory.set_views_implementation(views_impl.address)
        factory.set_math_implementation(math_impl.address)
        factory.set_pool_implementations(0, amm_impl.address)

    return factory, load_partial("contracts", "main", "CurveStableSwapNG.vy")


def deploy_plain_token(name: str, symbol: str, decimals: int = 18):
    return load_partial("contracts", "mocks", "ERC20.vy").deploy(name, symbol, decimals)


def deploy_oracle_token(name: str, symbol: str, rate: int):
    return load_partial("contracts", "mocks", "ERC20Oracle.vy").deploy(name, symbol, 18, rate)


def deploy_rebasing_token(name: str, symbol: str, decimals: int = 18, is_up: bool = True):
    return load_partial("contracts", "mocks", "ERC20RebasingConditional.vy").deploy(name, symbol, decimals, is_up)


def deploy_vault(name: str, symbol: str, decimals: int, asset):
    return boa.load(
        str(Path("contracts/ERC4626Mock.vy")),
        asset.address,
        name,
        symbol,
        decimals,
    )


def mint_for_testing(token, target, amount: int):
    token._mint_for_testing(target, amount)


def deploy_pool(factory, pool_partial, coins, asset_types, method_ids, oracles, A=1000, fee=3_000_000):
    with boa.env.prank(boa.env.generate_address()):
        pool_address = factory.deploy_plain_pool(
            "test",
            "test",
            [coin.address for coin in coins],
            A,
            fee,
            OFFPEG_FEE_MULTIPLIER,
            866,
            0,
            asset_types,
            method_ids,
            oracles,
        )

    return pool_partial.at(pool_address)


def add_liquidity(pool, provider, coins, amounts):
    for coin in coins:
        coin.approve(pool.address, 2**256 - 1, sender=provider)
    with boa.env.prank(provider):
        pool.add_liquidity(amounts, 0, provider)


def test_real_ng_exchange_received_plain_path(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    coin0 = deploy_plain_token("Token0", "TK0")
    coin1 = deploy_plain_token("Token1", "TK1")
    pool = deploy_pool(
        factory,
        pool_partial,
        [coin0, coin1],
        [0, 0],
        [b"", b""],
        [ZERO_ADDRESS, ZERO_ADDRESS],
    )

    liquidity = 10**21
    mint_for_testing(coin0, alice, liquidity)
    mint_for_testing(coin1, alice, liquidity)
    add_liquidity(pool, alice, [coin0, coin1], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(coin0, bob, amount_in)
    with boa.env.prank(bob):
        coin0.transfer(pool.address, amount_in)
        quoted = pool.get_dy(0, 1, amount_in)
        out = pool.exchange_received(0, 1, amount_in, 0, bob)

    assert out == quoted
    assert coin1.balanceOf(bob) == out


def test_real_ng_exchange_plain_quote_matches_execution(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    coin0 = deploy_plain_token("Token0", "TK0")
    coin1 = deploy_plain_token("Token1", "TK1")
    pool = deploy_pool(
        factory,
        pool_partial,
        [coin0, coin1],
        [0, 0],
        [b"", b""],
        [ZERO_ADDRESS, ZERO_ADDRESS],
    )

    liquidity = 10**21
    mint_for_testing(coin0, alice, liquidity)
    mint_for_testing(coin1, alice, liquidity)
    add_liquidity(pool, alice, [coin0, coin1], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(coin0, bob, amount_in)
    coin0.approve(pool.address, 2**256 - 1, sender=bob)

    quoted = pool.get_dy(0, 1, amount_in)
    with boa.env.prank(bob):
        executed = pool.exchange(0, 1, amount_in, 0, bob)

    assert executed == quoted


def test_real_ng_exchange_received_rebasing_reverts(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    rebasing = deploy_rebasing_token("Rebasing", "RBSN")
    plain = deploy_plain_token("Token1", "TK1")
    pool = deploy_pool(
        factory,
        pool_partial,
        [rebasing, plain],
        [2, 0],
        [b"", b""],
        [ZERO_ADDRESS, ZERO_ADDRESS],
        A=500,
        fee=4_000_000,
    )

    liquidity = 10**21
    mint_for_testing(rebasing, alice, liquidity)
    mint_for_testing(plain, alice, liquidity)
    add_liquidity(pool, alice, [rebasing, plain], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(rebasing, bob, amount_in)
    with boa.env.prank(bob):
        rebasing.transfer(pool.address, amount_in)
        with boa.reverts():
            pool.exchange_received(0, 1, amount_in, 0, bob)


def test_real_ng_exchange_oracle_quote_matches_execution_without_rate_change(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    plain = deploy_plain_token("Token0", "TK0")
    oracle_token = deploy_oracle_token("Oracle", "ORC", 10**18)
    pool = deploy_pool(
        factory,
        pool_partial,
        [plain, oracle_token],
        [0, 1],
        [b"", ORACLE_METHOD_ID],
        [ZERO_ADDRESS, oracle_token.address],
    )

    liquidity = 10**21
    mint_for_testing(plain, alice, liquidity)
    mint_for_testing(oracle_token, alice, liquidity)
    add_liquidity(pool, alice, [plain, oracle_token], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(plain, bob, amount_in)
    plain.approve(pool.address, 2**256 - 1, sender=bob)

    quoted = pool.get_dy(0, 1, amount_in)
    with boa.env.prank(bob):
        executed = pool.exchange(0, 1, amount_in, 0, bob)

    assert executed == quoted


def test_real_ng_oracle_quote_becomes_stale_after_rate_update(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    plain = deploy_plain_token("Token0", "TK0")
    oracle_token = deploy_oracle_token("Oracle", "ORC", 10**18)
    pool = deploy_pool(
        factory,
        pool_partial,
        [plain, oracle_token],
        [0, 1],
        [b"", ORACLE_METHOD_ID],
        [ZERO_ADDRESS, oracle_token.address],
    )

    liquidity = 10**21
    mint_for_testing(plain, alice, liquidity)
    mint_for_testing(oracle_token, alice, liquidity)
    add_liquidity(pool, alice, [plain, oracle_token], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(plain, bob, amount_in)
    plain.approve(pool.address, 2**256 - 1, sender=bob)

    quoted = pool.get_dy(0, 1, amount_in)
    oracle_token.set_exchange_rate(12 * 10**17)
    with boa.env.prank(bob):
        executed = pool.exchange(0, 1, amount_in, 0, bob)

    assert executed < quoted


def test_real_ng_oracle_input_quote_becomes_stale_after_rate_update(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    plain = deploy_plain_token("Token0", "TK0")
    oracle_token = deploy_oracle_token("Oracle", "ORC", 10**18)
    pool = deploy_pool(
        factory,
        pool_partial,
        [plain, oracle_token],
        [0, 1],
        [b"", ORACLE_METHOD_ID],
        [ZERO_ADDRESS, oracle_token.address],
    )

    liquidity = 10**21
    mint_for_testing(plain, alice, liquidity)
    mint_for_testing(oracle_token, alice, liquidity)
    add_liquidity(pool, alice, [plain, oracle_token], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(oracle_token, bob, amount_in)
    oracle_token.approve(pool.address, 2**256 - 1, sender=bob)

    quoted = pool.get_dy(1, 0, amount_in)
    oracle_token.set_exchange_rate(12 * 10**17)
    with boa.env.prank(bob):
        executed = pool.exchange(1, 0, amount_in, 0, bob)

    assert executed != quoted


def test_real_ng_erc4626_quote_becomes_stale_after_vault_donation(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    plain = deploy_plain_token("Token0", "TK0")
    underlying = deploy_plain_token("Asset", "AST")
    vault = deploy_vault("Vault", "VLT", 18, underlying)
    pool = deploy_pool(
        factory,
        pool_partial,
        [plain, vault],
        [0, 3],
        [b"", b""],
        [ZERO_ADDRESS, ZERO_ADDRESS],
    )

    liquidity = 10**21
    mint_for_testing(plain, alice, liquidity)
    mint_for_testing(underlying, alice, liquidity)
    underlying.approve(vault.address, 2**256 - 1, sender=alice)
    with boa.env.prank(alice):
        vault.deposit(liquidity, alice)
    add_liquidity(pool, alice, [plain, vault], [liquidity, liquidity])

    amount_in = 10**18
    mint_for_testing(plain, bob, amount_in)
    plain.approve(pool.address, 2**256 - 1, sender=bob)

    quoted = pool.get_dy(0, 1, amount_in)
    mint_for_testing(underlying, alice, 5 * 10**18)
    with boa.env.prank(alice):
        underlying.transfer(vault.address, 5 * 10**18)
    with boa.env.prank(bob):
        executed = pool.exchange(0, 1, amount_in, 0, bob)

    assert executed < quoted


def test_real_ng_erc4626_input_quote_becomes_stale_after_vault_donation(alice, bob):
    factory_owner = boa.env.generate_address()
    fee_receiver = boa.env.generate_address()
    factory, pool_partial = deploy_factory(factory_owner, fee_receiver)

    plain = deploy_plain_token("Token0", "TK0")
    underlying = deploy_plain_token("Asset", "AST")
    vault = deploy_vault("Vault", "VLT", 18, underlying)
    pool = deploy_pool(
        factory,
        pool_partial,
        [plain, vault],
        [0, 3],
        [b"", b""],
        [ZERO_ADDRESS, ZERO_ADDRESS],
    )

    liquidity = 10**21
    mint_for_testing(plain, alice, liquidity)
    mint_for_testing(underlying, alice, liquidity)
    underlying.approve(vault.address, 2**256 - 1, sender=alice)
    with boa.env.prank(alice):
        vault.deposit(liquidity, alice)
    add_liquidity(pool, alice, [plain, vault], [liquidity, liquidity])

    amount_in = 10**18
    vault.approve(pool.address, 2**256 - 1, sender=bob)
    mint_for_testing(underlying, bob, amount_in)
    underlying.approve(vault.address, 2**256 - 1, sender=bob)
    with boa.env.prank(bob):
        vault.deposit(amount_in, bob)

    quoted = pool.get_dy(1, 0, amount_in)
    mint_for_testing(underlying, alice, 5 * 10**18)
    with boa.env.prank(alice):
        underlying.transfer(vault.address, 5 * 10**18)
    with boa.env.prank(bob):
        executed = pool.exchange(1, 0, amount_in, 0, bob)

    assert executed != quoted

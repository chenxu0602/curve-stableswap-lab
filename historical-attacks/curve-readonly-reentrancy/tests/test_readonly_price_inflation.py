from pathlib import Path

import boa


ROOT = Path("historical-attacks/curve-readonly-reentrancy")


def test_virtual_price_is_inflated_during_callback(alice):
    pool = boa.load(
        str(ROOT / "contracts" / "VulnerableLPOraclePool.vy"),
        10**18,
        10**18,
        alice,
    )
    recorder = boa.load(
        str(ROOT / "contracts" / "ReadOnlyPriceRecorder.vy"),
        pool.address,
    )

    normal_price_before = pool.get_virtual_price()
    assert normal_price_before == 10**18

    with boa.env.prank(alice):
        pool.remove_liquidity_with_callback(2 * 10**17, recorder.address)

    observed_during_callback = recorder.observed_price()
    normal_price_after = pool.get_virtual_price()

    assert observed_during_callback > normal_price_before
    assert observed_during_callback == 125 * 10**16
    assert normal_price_after == 10**18

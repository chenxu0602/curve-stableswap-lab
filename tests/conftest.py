from pathlib import Path

import boa
import pytest


@pytest.fixture(scope="module", autouse=True)
def boa_setup():
    with boa.swap_env(boa.Env()):
        boa.env.enable_fast_mode()
        yield


@pytest.fixture(scope="module")
def math_harness():
    return boa.load(str(Path("contracts/StableSwapMathHarness.vy")))


@pytest.fixture
def alice():
    return boa.env.generate_address()


@pytest.fixture
def bob():
    return boa.env.generate_address()


@pytest.fixture
def amp():
    return 2000


@pytest.fixture
def xp_balanced_3():
    return [10**18, 10**18, 10**18]


@pytest.fixture
def xp_imbalanced_3():
    return [2 * 10**18, 10**18, 10**18]
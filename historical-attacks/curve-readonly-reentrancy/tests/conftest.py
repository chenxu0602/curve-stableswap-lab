import pytest, boa

@pytest.fixture
def alice():
    return boa.env.generate_address()
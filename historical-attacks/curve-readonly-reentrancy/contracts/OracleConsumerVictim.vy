# pragma version ^0.4.0

interface Pool:
    def get_virtual_price() -> uint256: view

PRECISION: constant(uint256) = 10**18
LTV: constant(uint256) = 5 * 10**17  # 50%

pool: public(address)
collateral_lp: public(HashMap[address, uint256])
debt: public(HashMap[address, uint256])

@deploy
def __init__(_pool: address):
    self.pool = _pool

@external
def deposit_lp(_amount: uint256):
    # Toy model: no real LP token transfer.
    # We only track collateral units to isolate oracle mechanism.
    self.collateral_lp[msg.sender] += _amount


@view
@internal
def _max_borrow(_user: address) -> uint256:
    vp: uint256 = staticcall Pool(self.pool).get_virtual_price()
    collateral_value: uint256 = self.collateral_lp[_user] * vp // PRECISION
    return collateral_value * LTV // PRECISION

@view
@external
def max_borrow(_user: address) -> uint256:
    return self._max_borrow(_user)

@external
def borrow(_amount: uint256):
    assert self.debt[msg.sender] + _amount <= self._max_borrow(msg.sender)
    self.debt[msg.sender] += _amount
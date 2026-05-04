# pragma version ^0.4.0

interface Pool:
    def get_virtual_price() -> uint256: view

pool: public(address)
observed_price: public(uint256)

@deploy
def __init__(_pool: address):
    self.pool = _pool

@external
def on_callback():
    self.observed_price = staticcall Pool(self.pool).get_virtual_price()
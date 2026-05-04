# pragma version ^0.4.0

interface Callback:
    def on_callback(): nonpayable

PRECISION: constant(uint256) = 10**18

asset_balance: public(uint256)
total_supply: public(uint256)
balanceOf: public(HashMap[address, uint256])

@deploy
def __init__(_initial_assets: uint256, _initial_supply: uint256, _lp_holder: address):
    self.asset_balance = _initial_assets
    self.total_supply = _initial_supply
    self.balanceOf[_lp_holder] = _initial_supply

@view
@external
def get_virtual_price() -> uint256:
    return self.asset_balance * PRECISION // self.total_supply

@external
def remove_liquidity_with_callback(_burn_amount: uint256, _callback: address):
    assert self.balanceOf[msg.sender] >= _burn_amount
    assert _burn_amount > 0

    # Vulnerable ordering:
    # supply is reduced first, while asset_balance is still old.
    self.balanceOf[msg.sender] -= _burn_amount
    self.total_supply -= _burn_amount

    # External callback while virtual price is inflated.
    extcall Callback(_callback).on_callback()

    # Finalize asset accounting after callback.
    self.asset_balance -= _burn_amount


@external
def set_lp_balance_for_testing(_user: address, _amount: uint256):
    self.balanceOf[_user] = _amount


@external
def mint_lp_for_testing(_user: address, _amount: uint256):
    self.balanceOf[_user] += _amount
    self.total_supply += _amount
    self.asset_balance += _amount
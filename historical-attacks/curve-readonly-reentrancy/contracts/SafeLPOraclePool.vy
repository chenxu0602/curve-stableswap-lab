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
    return (self.asset_balance * PRECISION) // self.total_supply

@external
def set_lp_balance_for_testing(_user: address, _amount: uint256):
    # Toy reproduction helper.
    # This is not intended to model production LP minting.
    self.balanceOf[_user] = _amount

@external
def remove_liquidity_with_callback(_burn_amount: uint256, _callback: address):
    assert self.balanceOf[msg.sender] >= _burn_amount
    assert _burn_amount > 0

    # Safe ordering:
    # finalize both sides of accounting before making the external callback.
    #
    # Before:
    #   asset_balance = 1.0e18
    #   total_supply  = 1.0e18
    #   virtual_price = 1.0e18
    #
    # After accounting:
    #   asset_balance = 0.8e18
    #   total_supply  = 0.8e18
    #   virtual_price = 1.0e18
    #
    # The callback can still read get_virtual_price(), but it no longer sees
    # old assets divided by reduced supply.
    self.balanceOf[msg.sender] -= _burn_amount
    self.asset_balance -= _burn_amount
    self.total_supply -= _burn_amount

    extcall Callback(_callback).on_callback()
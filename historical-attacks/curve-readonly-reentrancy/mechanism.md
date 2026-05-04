# Mechanism: Read-only Reentrancy and LP Oracle Manipulation

## 1. Summary

Read-only reentrancy is a pattern where an attacker does not necessarily reenter a mutating function of the same protocol.

Instead, the attacker causes another protocol to read a view function during an inconsistent intermediate state.

In Curve-style systems, this is especially important when external protocols use pool-derived values as oracle inputs, such as:

- `get_virtual_price()`
- LP token valuation
- invariant-derived pool value
- total asset value per LP token

The core risk is not simply "reentrancy." The core risk is:

> an external protocol treats a transient accounting state as a stable oracle value.

## 2. Normal LP valuation model

A simplified Curve-like LP valuation can be represented as:

```text
virtual_price = total_pool_value / total_lp_supply
```

In a real Curve-style pool, the value may be derived from the invariant `D`, normalized balances, rates, fees, and LP supply.

For this toy reproduction, the simplified model is enough:

```text
get_virtual_price() = pool_balance * 1e18 / total_supply
```

This is intentionally simplified to isolate the mechanism.

## 3. Expected invariant

External consumers usually expect `get_virtual_price()` to be read only from a consistent pool state.

A consistent state should satisfy:

```text
pool assets and LP supply describe the same accounting moment
```

For example:

```text
total_pool_value = 1,000
total_lp_supply = 1,000
virtual_price = 1.0
```

If an LP removes liquidity, both pool assets and LP supply should eventually decline in a coherent way.

## 4. Intermediate-state problem

A vulnerable liquidity-removal path may temporarily update one side of the accounting before the other.

For example:

```text
Step 1: reduce total_lp_supply
Step 2: external callback
Step 3: transfer assets / finalize balances
```

During step 2, the pool may expose:

```text
pool_balance = old balance
total_lp_supply = reduced supply
```

So:

```text
virtual_price = old_pool_balance / reduced_total_supply
```

This can temporarily inflate the LP price.

Example:

```text
Before:
pool_balance = 1,000
total_supply = 1,000
virtual_price = 1.0

Intermediate:
pool_balance = 1,000
total_supply = 800
virtual_price = 1.25

Final:
pool_balance = 800
total_supply = 800
virtual_price = 1.0
```

The final state is coherent, but the intermediate read is inflated.

## 5. Attack path

The minimal attack path is:

```text
1. Attacker holds LP tokens.
2. Attacker calls pool.remove_liquidity_with_callback().
3. Pool enters an intermediate state where virtual price is inflated.
4. Pool calls attacker callback.
5. During callback, attacker calls an external victim protocol.
6. Victim reads pool.get_virtual_price().
7. Victim overvalues attacker's LP collateral.
8. Attacker borrows more than should be allowed.
9. Pool finalizes liquidity removal.
```

The pool's final state may look normal.

The victim protocol has already made a decision using the distorted intermediate price.

## 6. Why the function being `view` does not make it safe

A `view` function guarantees that the function itself does not mutate state.

It does not guarantee that:

- the state being read is globally consistent
- the value is safe as an oracle
- the value cannot be manipulated within a transaction
- external integrations can safely consume it during another protocol's execution

So the dangerous assumption is:

```text
view == oracle-safe
```

That assumption is false.

## 7. Why this is an integration risk

The AMM may expose a value that is meaningful under normal conditions.

The vulnerability often emerges when another protocol uses that value as:

- collateral price
- borrowing limit input
- liquidation threshold input
- vault share valuation
- mint/redeem price
- risk-engine input

The consumer protocol should ask:

```text
Can this value be read during a transient state?
Can the value be manipulated within the same transaction?
Does the value depend on current pool balances or LP supply?
Does the value need a delay, TWAP, cache, or reentrancy-aware guard?
```

## 8. Toy reproduction design

### Pool

The pool will implement:

```text
pool_balance
total_supply
lp_balance[user]
get_virtual_price()
remove_liquidity_with_callback()
```

The vulnerable path intentionally creates this sequence:

```text
total_supply is reduced
external callback is made
pool_balance is reduced after callback
```

This creates a temporary inflated virtual price.

### Victim

The victim will implement:

```text
deposit_lp()
borrow()
```

The borrow function values collateral using:

```text
collateral_value = lp_amount * pool.get_virtual_price() / 1e18
```

If the price is inflated during callback, the attacker can borrow too much.

### Attacker

The attacker will:

```text
call remove_liquidity_with_callback()
receive callback
call victim.borrow()
```

The expected test assertion is:

```text
borrowed_during_callback > borrowed_under_normal_price
```

or:

```text
victim accepts collateral valuation that is higher than the normal post-finalization valuation
```

## 9. Security properties to test

The toy reproduction should test:

### Baseline

Outside the callback:

```text
get_virtual_price() == normal value
```

### Intermediate manipulation

During callback:

```text
get_virtual_price() > normal value
```

### Victim impact

During callback:

```text
victim overvalues LP collateral
```

### Final pool state

After the liquidity removal completes:

```text
get_virtual_price() returns to normal or coherent value
```

This is important because the final state alone may not reveal the attack.

## 10. Review checklist for real protocols

When reviewing protocols that consume Curve-like LP prices:

- Does the protocol call `get_virtual_price()` directly?
- Does it use the value in collateral, minting, redemption, or liquidation logic?
- Is the value consumed inside the same transaction as another external call?
- Can an attacker trigger pool state transitions before the read?
- Is the value cached or time-delayed?
- Is there a reentrancy guard on the consumer?
- Does the protocol rely on an oracle that is independent of immediate pool accounting state?
- Does it assume `view` implies manipulation resistance?

## 11. Main lesson

The main lesson is:

> A view function can be safe as a read-only helper but unsafe as an oracle if it can observe inconsistent intermediate state.

For AMM integrations, oracle safety requires more than mathematical correctness.

It requires state-consistency assumptions to be valid at the exact moment the value is consumed.
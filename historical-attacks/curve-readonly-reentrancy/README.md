# Curve Read-only Reentrancy / Curvy Puppet-style LP Oracle Manipulation

This directory contains a focused historical-attack mechanism study for Curve-style read-only reentrancy and LP oracle manipulation.

The goal is not to reproduce a production incident line-by-line. The goal is to isolate the core mechanism:

> a protocol reads a Curve-like pool's view function during an inconsistent intermediate state and uses that value as an oracle.

This is a toy reproduction and security research artifact.

## Core idea

A Curve-style pool may expose a view function such as:

- `get_virtual_price()`
- LP token price
- invariant-derived pool value
- collateral valuation helper

External protocols may treat that value as an oracle.

The danger appears when the value can be read during a transient accounting state, for example during a liquidity removal path before all accounting has fully settled.

If a callback or external interaction happens in the middle of that state transition, an attacker may cause another protocol to read a temporarily distorted LP valuation.

## Why this matters

Read-only reentrancy is subtle because the reentered function may be a `view` function.

The pool may not be directly losing funds during the reentrant read.

Instead, the problem appears in an external integration:

1. Pool enters a partially updated state.
2. Attacker reenters another protocol.
3. The other protocol reads the pool's view function.
4. The other protocol accepts a manipulated valuation.
5. The attacker extracts value from the integrating protocol.

The vulnerable component is often not only the AMM itself, but the assumption made by the consumer of the AMM's view output.

## Minimal reproduction target

The toy reproduction will model three contracts:

### `VulnerableLPOraclePool.vy`

A simplified Curve-like pool that exposes:

- LP balances
- total LP supply
- pooled asset balance
- `get_virtual_price()`
- a liquidity-removal path with an external callback before accounting is fully consistent

### `OracleConsumerVictim.vy`

A simplified external protocol that:

- accepts LP tokens as collateral
- calls `pool.get_virtual_price()`
- values collateral based on the returned LP price
- allows borrowing against that valuation

### `ReadOnlyReentrancyAttacker.vy`

A contract that:

- triggers the vulnerable pool path
- receives a callback during the intermediate state
- calls the victim while `get_virtual_price()` is distorted
- demonstrates excessive borrowing or collateral overvaluation

## Intended security lesson

The main lesson is:

> View functions are not automatically safe oracle sources if they can be read during inconsistent state transitions.

External integrations should not assume that a pool view value is safe merely because:

- the function is marked `view`
- the function does not mutate state
- the AMM itself appears nonreentrant
- the value usually behaves correctly outside intermediate execution states

## What this reproduction will not prove

This artifact does not prove:

- a live vulnerability in current Curve deployments
- exploitability of every Curve-like pool
- exploitability of every `get_virtual_price()` integration
- correctness of all historical incident details
- absence of mitigations in production protocols

It only demonstrates the mechanism class.

## Planned files

```text
historical-attacks/curve-readonly-reentrancy/
├── README.md
├── mechanism.md
├── threat-model.md
├── contracts/
│   ├── VulnerableLPOraclePool.vy
│   ├── OracleConsumerVictim.vy
│   └── ReadOnlyReentrancyAttacker.vy
└── tests/
    └── test_readonly_reentrancy.py
```

## Relation to the main Curve StableSwap lab

This case study extends the main `curve-stableswap-lab` theme:

```text
balances -> stored_rates -> xp -> D / y -> LP supply / virtual price
```

The main lab focuses on StableSwap NG accounting semantics.

This historical case study focuses on how a derived pool value can become dangerous when an external protocol reads it at the wrong time.

## Status

Planned / in progress.

Initial target:

- build a minimal toy reproduction
- write one passing pytest demonstrating inflated LP valuation during callback
- document the integration risk pattern

## Current reproduction

Local tests:

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
```
# 4 passed

## Current reproduction

Local tests:

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
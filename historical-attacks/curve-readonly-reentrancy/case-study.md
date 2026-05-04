# Curve Read-only Reentrancy / LP Oracle Manipulation Case Study

## 1. Historical background

This case study covers the Curve LP oracle manipulation / read-only reentrancy vulnerability class and the later real-world incidents that followed from unsafe integrations.

The key historical lesson is not that Curve's StableSwap math was wrong. The lesson is that external protocols can become vulnerable when they treat a Curve LP valuation view as an immediately safe oracle input.

- ChainSecurity disclosure and postmortem
  - In April 2022, ChainSecurity informed Curve and affected projects about a read-only reentrancy issue affecting some Curve pools.
  - ChainSecurity later published a postmortem explaining that `get_virtual_price()` could be manipulated during liquidity removal if an external consumer read it while the pool was in a transient accounting state.
  - The key observation was that external consumers could read a temporarily inconsistent state where pool balances and LP `totalSupply()` did not describe the same accounting moment.

- dForce 2023 exploit
  - On February 9, 2023, dForce was exploited for roughly $3.6M–$3.7M across Arbitrum and Optimism after using Curve LP valuation in a collateral / lending path.
  - The attacker manipulated Curve LP valuation during liquidity removal, then caused dForce to consume the inflated value inside its own credit logic.
  - This is the closest historical anchor for the toy reproduction in this lab.

- Related incidents: Midas and Conic
  - Midas Capital was exploited in January 2023 after using a Curve LP token as collateral.
  - Conic Finance was exploited in July 2023 through a related Curve-LP-oracle / read-only-reentrancy-style pricing path in `CurveLPOracleV2`.
  - These incidents are related examples of the broader integration risk, but this toy model is not a line-by-line reproduction of either exploit.

- Non-example: Curve/Vyper 2023 compiler incident
  - The July 2023 Curve/Vyper incident is not the same vulnerability class.
  - That event was ultimately traced to a Vyper compiler bug affecting reentrancy protection, not the external-consumer read-only reentrancy oracle issue modeled here.

## 2. Vulnerability class

This is not the usual "drain the same contract by reentering its write path" pattern.

Instead:

- the source contract enters a transiently inconsistent accounting state;
- an external callback gains control during that window;
- the attacker causes a different consumer contract to read a view function such as `get_virtual_price()`;
- the consumer trusts that read as if it were a coherent oracle value.

The core bug class is therefore:

- not classic drain-the-same-contract reentrancy;
- not a direct failure of StableSwap invariant math;
- but a transaction-local oracle manipulation caused by reading transient state.

In Curve-style LP pricing, the danger appears when:

- the pool updates one side of accounting first, such as LP `totalSupply()`;
- an external callback happens before the underlying asset balances are fully settled;
- a victim protocol reads LP price during that gap.

## 3. Minimal reproduction

The lab reproduction uses four simplified contracts:

- `VulnerableLPOraclePool`
  - exposes a `get_virtual_price()`-style view;
  - performs liquidity exit in an unsafe order;
  - triggers an external callback before accounting becomes coherent again.

- `OracleConsumerVictim`
  - treats `pool.get_virtual_price()` as an input to collateral valuation;
  - uses that value in `max_borrow()` credit logic.

- `ReadOnlyReentrancyAttacker`
  - initiates liquidity removal;
  - receives the callback;
  - reenters the victim and borrows against the temporarily inflated LP value.

- `SafeLPOraclePool`
  - exposes the same general interface;
  - finalizes coherent accounting before callback;
  - prevents the same transient oracle distortion.

This is a toy reproduction of the vulnerability class, not a byte-for-byte recreation of any one historical exploit.

## 4. Vulnerable ordering

The vulnerable ordering is:

```text
reduce total_supply -> callback -> reduce asset_balance
```

That ordering is dangerous because `get_virtual_price()` is typically some form of:

```text
virtual_price ~= total_asset_value / total_supply
```

If `total_supply` is reduced first while the asset side has not yet been reduced, the ratio is temporarily overstated.

Example:

```text
Before:
asset_balance = 1.0
total_supply  = 1.0
virtual_price = 1.0

During callback:
asset_balance = 1.0
total_supply  = 0.8
virtual_price = 1.25

After finalization:
asset_balance = 0.8
total_supply  = 0.8
virtual_price = 1.0
```

The final state is coherent again, but the victim has already consumed the inflated intermediate value.

## 5. Attack flow

The minimal attack flow is:

```text
pool.remove_liquidity_with_callback()
  -> attacker.on_callback()
      -> victim.borrow()
          -> victim.max_borrow()
              -> pool.get_virtual_price()
```

Expanded:

1. The attacker builds a position that will be valued using the LP oracle.
2. The attacker starts liquidity removal from the vulnerable pool.
3. The pool reduces LP supply first.
4. Before asset balances are fully settled, the pool triggers the attacker's callback.
5. Inside the callback, the attacker calls `victim.borrow()`.
6. The victim computes credit through `victim.max_borrow()`.
7. `victim.max_borrow()` reads `pool.get_virtual_price()`.
8. Because the pool is mid-exit, the oracle value is temporarily inflated.
9. The victim overestimates collateral value and lends too much.
10. Control returns and the pool finishes settlement, restoring normal pricing after the damage is done.

The important detail is that the source pool itself may complete normally. The exploit lands in the external consumer that trusted the temporary read.

## 6. Why `view` does not mean oracle-safe

A `view` function guarantees only that the function itself does not mutate state.

It does not guarantee that:

- the state being read is globally coherent;
- the value is manipulation-resistant within the same transaction;
- the value is safe for collateral, borrowing, minting, redemption, or liquidation logic;
- the value cannot be distorted by an attacker-controlled call sequence.

So the dangerous assumption is:

```text
view function == oracle-safe value
```

That assumption is false.

In this vulnerability class, the read-only function does not need to write state. It only needs to read a state that is temporarily inconsistent.

## 7. Safe ordering mitigation

The clean mitigation is:

```text
finalize coherent accounting before callback
```

In practice that means:

- do not expose a state where LP supply and asset balances disagree across an external call boundary;
- avoid sending ETH or callback-capable tokens before the accounting snapshot used by pricing views is finalized;
- if a callback is unavoidable, make sure any public pricing view either:
  - reads from already-coherent post-settlement state; or
  - reverts while the contract is inside the critical section.

For integrators consuming Curve LP prices, additional mitigations include:

- do not treat `get_virtual_price()` as a standalone safe oracle;
- avoid using a single in-transaction LP price read for borrow, mint, liquidation, or collateral decisions;
- use delayed, cached, bounded, or independently validated pricing;
- apply conservative collateral haircuts;
- gate sensitive valuation paths with reentrancy-aware controls;
- verify that wrappers and oracle adapters protect every variant, not only a previously audited path.

## 8. Test evidence

The local lab reproduction currently reports:

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

The tests demonstrate:

- vulnerable ordering can inflate a `get_virtual_price()`-style read;
- an external consumer can overvalue LP collateral during callback;
- the attacker can borrow more than allowed under the final coherent pool state;
- the same inflated borrow amount reverts outside the transient price distortion;
- safe ordering removes the exploit window;
- safe ordering still allows normal borrowing behavior.

The most important assertion is not merely that the pool price changes.

The important assertion is:

```text
an external protocol makes a value-transfer decision based on the transient value
```

## 9. Review checklist

For protocols consuming Curve LP prices:

- Does the protocol use `get_virtual_price()` directly in borrow, liquidation, mint, redemption, vault, or collateral logic?
- Is the LP oracle read trusted as if it were manipulation-resistant within the same transaction?
- Can attacker-controlled execution reach the consumer during pool exit, withdrawal, zap, callback, or token-transfer paths?
- Does the valuation path depend on a read that can observe temporary imbalance between balances and LP `totalSupply()`?
- Is the protocol using Curve LP as collateral without additional oracle hardening?
- Does the system assume LP price is monotonic and therefore safe as a lower bound?
- Are ETH pools, callback-capable tokens, or other external-call settlement paths involved?
- If the protocol wraps Curve LP pricing, does the wrapper protect against read-only reentrancy at every variant, not just the audited older version?
- Are reverse paths like liquidation, health-factor checks, redeem previews, or vault share minting protected, not only direct borrow paths?
- Does the protocol have tests where the oracle is read during another protocol's intermediate state?

## 10. Limitations

This case study has deliberate limits:

- it is a toy reproduction, not a production exploit recreation;
- it focuses on the vulnerability class, not exact historical bytecode;
- it simplifies surrounding protocol logic so the read-only reentrancy dependency is easier to see;
- it does not prove every Curve integration is vulnerable;
- it does not model all Curve pool variants;
- it does not model unrelated Curve incidents such as the 2023 Vyper compiler bug.

The value of the case study is conceptual clarity:

- why the transient state exists;
- how an external consumer can be tricked by a view;
- why "view-only" does not mean "safe oracle read";
- and why external integrations must reason about the exact execution moment at which oracle-like values are consumed.
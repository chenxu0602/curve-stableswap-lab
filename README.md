# Curve StableSwap Lab

Security-oriented research lab for Curve StableSwap and StableSwap NG.

This repository studies Curve-style AMM accounting from an auditing perspective: invariant math, normalized balances, rate providers, ERC4626 conversion, rebasing tokens, quote/execution freshness, admin-fee unit accounting, zap temporary custody, and LP-oracle integration risk.

This is not a full protocol audit. It is a focused research and characterization artifact.

## Core mental model

```text
balances -> stored_rates -> xp -> D / y -> LP supply / virtual price
```

The main review question is not only whether StableSwap math is correct, but whether the pool applies the correct economic interpretation before values reach the invariant solver.

## Why this repo exists

StableSwap NG keeps the classic StableSwap invariant family, but expands the semantic boundary around the math.

The important review surfaces are no longer only `get_D`, `get_y`, and `get_y_D`. They also include:

- asset type correctness
- rate-provider precision and direction
- ERC4626 share-price behavior
- rebasing-token balance drift
- quote/execution freshness
- optimistic-transfer settlement via `exchange_received`
- admin-fee unit conversion
- zap temporary custody and historical balance contamination
- LP virtual-price consumption by external protocols

The goal of this repo is to isolate those mechanisms with small, explainable tests, notes, historical attack reproductions, and focused simulation notebooks.

## Current coverage

- StableSwap invariant math:
  - `get_D`
  - `get_y`
  - `get_y_D`
- Dynamic fee behavior
- Stored-rate and asset-type semantics
- Oracle-rate token behavior
- ERC4626 donation / share-price behavior
- Rebasing vs plain asset accounting
- `exchange_received` optimistic-transfer semantics
- Quote/execution differential behavior
- Admin-fee raw-unit conversion
- MetaZap-style temporary custody characterization
- Selected real StableSwap NG integration tests
- Curve read-only reentrancy / LP oracle manipulation toy reproduction
- Python simulation package for:
  - amplification vs slippage
  - dynamic fee vs imbalance
  - quote staleness under rate changes

## Repository structure

```text
.
├── contracts/              # Vyper harnesses and mocks
├── tests/                  # Boa / pytest characterization tests and Python simulation tests
├── notes/                  # Review notes, final review, invariants, test plan
├── notebooks/              # Simulation notebooks
├── outputs/                # Generated figures and tables
├── src/                    # Python simulation package
├── historical-attacks/     # Curve-related historical attack reproductions
├── METHODOLOGY.md
├── LIMITATIONS.md
└── ROADMAP.md
```

## Run tests

```bash
uv sync

uv run pytest tests -q
# 109 passed

uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

## Key notes

- [`notes/curve-review-notes.md`](notes/curve-review-notes.md)
- [`notes/final-review.md`](notes/final-review.md)
- [`notes/invariants.md`](notes/invariants.md)
- [`notes/test-plan.md`](notes/test-plan.md)
- [`notes/function-notes.md`](notes/function-notes.md)

## Simulation notebooks

- [`notebooks/01_amp_slippage_surface.ipynb`](notebooks/01_amp_slippage_surface.ipynb)
  - Shows how amplification `A` changes near-peg slippage.
- [`notebooks/02_dynamic_fee_imbalance.ipynb`](notebooks/02_dynamic_fee_imbalance.ipynb)
  - Shows how StableSwap NG-style dynamic fees increase with imbalance.
- [`notebooks/03_quote_staleness_rate_change.ipynb`](notebooks/03_quote_staleness_rate_change.ipynb)
  - Shows how rate changes can make quote and execution values diverge.

## Historical attack case study

- [`historical-attacks/curve-readonly-reentrancy/`](historical-attacks/curve-readonly-reentrancy/)
  - Toy reproduction of Curve read-only reentrancy / LP oracle manipulation.
  - Demonstrates how a transiently inflated `get_virtual_price()` can cause an external consumer to overvalue LP collateral.
  - Includes a safe-ordering mitigation comparison.

Run:

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

## Main takeaway

StableSwap NG is still mostly legacy StableSwap math, but the highest-value review surface has shifted from invariant algebra toward accounting semantics, configuration semantics, and integration semantics.

The solver can be correct while the economic interpretation of the inputs is wrong.

That makes this path especially important:

```text
token behavior -> asset type -> stored_rates -> xp -> D/y -> LP accounting
```

For external integrations, a second path is equally important:

```text
pool state transition -> virtual price / LP price -> downstream collateral or oracle consumer
```

## Review map

| Layer | Main question |
|---|---|
| Math kernel | Do `get_D`, `get_y`, and `get_y_D` preserve expected StableSwap behavior? |
| Normalization | Do `stored_rates` and `xp` represent the intended economic value? |
| Token semantics | Are plain, oracle-rate, ERC4626, and rebasing assets classified correctly? |
| Settlement | Do transfers, admin fees, and stored balances reconcile in the same unit system? |
| Integration | Do views, zaps, routers, and collateral consumers understand quote freshness and temporary custody semantics? |
| LP oracle usage | Can `get_virtual_price()` or similar pool views be consumed during an inconsistent state? |

## Test themes

### StableSwap math

The math tests characterize basic invariant behavior:

- zero-balance `D`
- balanced-pool `D ≈ sum(xp)`
- symmetry
- monotonicity
- `get_y` preserving `D` within rounding
- larger `A` reducing near-peg slippage
- `get_y_D` behavior under reduced target `D`

### Dynamic fee

The dynamic-fee tests characterize off-peg fee amplification:

- balanced pool returns base fee
- disabled multiplier returns base fee even when imbalanced
- imbalanced pool produces higher fee
- higher off-peg multiplier increases fee under imbalance

### Asset types and stored rates

The stored-rate tests characterize how raw balances become normalized `xp`:

- plain assets use multiplier-only normalization
- oracle-rate assets depend on external rate precision and direction
- wrong-scale oracle rates produce internally consistent but economically wrong `xp`
- ERC4626 donation changes share price and therefore pool pricing

### Rebasing semantics

The rebasing tests characterize the difference between plain and rebasing-aware accounting:

- plain pools use cached `stored_balances`
- rebasing pools intentionally reintroduce live `balanceOf(pool)` at selected sync points
- proportional exit semantics differ between plain and rebasing modes

### `exchange_received`

The optimistic-transfer tests characterize `exchange_received` semantics:

- prior transfers are consumed as input
- historical surplus can be consumed by the current caller
- post-sync donation can merge with current caller input
- rebasing asset presence disables the path
- rebasing drift cannot be consumed as swap input

### Quote/execution freshness

The quote/execution tests characterize state freshness assumptions:

- direct quote and execution match under unchanged state
- oracle-rate updates can make quotes stale
- ERC4626 donation-driven share-price changes can make quotes stale
- stale-quote direction depends on which side carries changing rate semantics

### Admin fee accounting

The admin-fee tests characterize xp-space to raw-unit conversion:

- fees may be computed in normalized `xp` units
- `admin_balances[i]` must be recorded in raw direct-coin units
- higher output-token rate means fewer raw token units for the same `xp` fee

### MetaZap-style custody

The MetaZap-style tests characterize full-balance flush behavior:

- pre-existing dust can be transferred to the current receiver
- historical balance contamination should be understood before being treated as a vulnerability

### Read-only reentrancy / LP oracle manipulation

The historical attack tests characterize a Curve-style read-only reentrancy mechanism:

- vulnerable ordering can temporarily inflate a `get_virtual_price()`-style read
- an external consumer can overvalue LP collateral during callback
- the attacker can borrow more than allowed under the final coherent pool state
- the same inflated borrow amount reverts without the transient price distortion
- safe ordering removes the exploit window while preserving normal borrowing behavior

## Python simulation package

The Python package lives under:

```text
src/curve_stableswap_lab/
├── stableswap_math.py
├── dynamic_fee.py
├── scenarios.py
└── plotting.py
```

It provides reusable code for the notebooks:

- `stableswap_math.py`
  - integer-style `get_D`, `get_y`, `get_y_D`, `quote_dy`, and `xp_from_balances`
- `dynamic_fee.py`
  - StableSwap NG-style off-peg dynamic fee helpers
- `scenarios.py`
  - DataFrame scenario generators for notebook analysis
- `plotting.py`
  - optional plotting helpers

## Status

Research artifact in progress, close to completion.

Completed:

- local Vyper harness tests
- math and dynamic-fee characterization
- stored-rate and asset-type tests
- rebasing accounting tests
- `exchange_received` characterization
- quote/execution differential tests
- admin-fee unit conversion tests
- selected real StableSwap NG integration checks
- Curve read-only reentrancy / LP oracle manipulation toy reproduction
- safe-ordering mitigation comparison
- Python simulation package
- three focused simulation notebooks

Current local result:

```bash
uv run pytest tests -q
# 109 passed

uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

Planned before final repo closeout:

- final README / ROADMAP polish
- optional diagram cleanup
- final summary article or post
- optional `case-study.md` refinement if more historical references are added

Not planned for this repo:

- full Curve V2 / CryptoPool analysis
- full on-chain Curve analytics dashboard
- multi-pool arbitrage backtesting
- complete Curve ecosystem incident database
- unrelated non-Curve historical attacks

## Related files

- [`METHODOLOGY.md`](METHODOLOGY.md) — review approach and characterization methodology
- [`LIMITATIONS.md`](LIMITATIONS.md) — scope limits and non-audit disclaimer
- [`ROADMAP.md`](ROADMAP.md) — planned next steps
- [`notes/curve-review-notes.md`](notes/curve-review-notes.md) — public review note
- [`notes/final-review.md`](notes/final-review.md) — internal-style final review summary
- [`historical-attacks/curve-readonly-reentrancy/case-study.md`](historical-attacks/curve-readonly-reentrancy/case-study.md) — historical mechanism case study

## Disclaimer

This repository is not a full protocol audit and does not prove the absence of vulnerabilities.

It is a focused security research artifact intended to clarify selected StableSwap and StableSwap NG accounting boundaries, quote-freshness assumptions, and Curve LP oracle integration risks.
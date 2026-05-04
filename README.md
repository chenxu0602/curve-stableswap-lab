# Curve StableSwap Lab

Security-oriented research lab for Curve StableSwap and StableSwap NG.

This repository studies Curve-style AMM accounting from an auditing perspective: invariant math, normalized balances, rate providers, ERC4626 conversion, rebasing tokens, quote/execution freshness, admin-fee unit accounting, and zap temporary custody.

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

The goal of this repo is to isolate those mechanisms with small, explainable tests and notes.

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

## Repository structure

```text
.
├── contracts/              # Vyper harnesses and mocks
├── tests/                  # Boa / pytest characterization tests
├── notes/                  # Review notes, final review, invariants, test plan
├── notebooks/              # Planned simulation notebooks
├── outputs/                # Generated figures and tables
├── historical-attacks/     # Partially completed historical attack reproductions
├── METHODOLOGY.md
├── LIMITATIONS.md
└── ROADMAP.md
```

## Run tests

```bash
uv sync
uv run pytest tests -q
```

Current local result:

```text
47 passed
```

## Key notes

- [`notes/curve-review-notes.md`](notes/curve-review-notes.md)
- [`notes/final-review.md`](notes/final-review.md)
- [`notes/invariants.md`](notes/invariants.md)
- [`notes/test-plan.md`](notes/test-plan.md)
- [`notes/function-notes.md`](notes/function-notes.md)

## Main takeaway

StableSwap NG is still mostly legacy StableSwap math, but the highest-value review surface has shifted from invariant algebra toward accounting semantics and configuration semantics.

The solver can be correct while the economic interpretation of the inputs is wrong.

That makes this path especially important:

```text
token behavior -> asset type -> stored_rates -> xp -> D/y -> LP accounting
```

## Review map

| Layer | Main question |
|---|---|
| Math kernel | Do `get_D`, `get_y`, and `get_y_D` preserve expected StableSwap behavior? |
| Normalization | Do `stored_rates` and `xp` represent the intended economic value? |
| Token semantics | Are plain, oracle-rate, ERC4626, and rebasing assets classified correctly? |
| Settlement | Do transfers, admin fees, and stored balances reconcile in the same unit system? |
| Integration | Do views, zaps, and routers understand quote freshness and temporary custody semantics? |

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

## Status

Research artifact in progress.

Completed:

- local Vyper harness tests
- math and dynamic-fee characterization
- stored-rate and asset-type tests
- rebasing accounting tests
- `exchange_received` characterization
- quote/execution differential tests
- admin-fee unit conversion tests
- selected real StableSwap NG integration checks

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

Planned:

- factory negative tests
- metapool underlying quote vs nested execution
- `get_dx` / reverse-quote approximation under dynamic fee paths
- simulation notebooks
- Curve read-only reentrancy / LP oracle manipulation toy reproduction: initial version completed

## Related files

- [`METHODOLOGY.md`](METHODOLOGY.md) — review approach and characterization methodology
- [`LIMITATIONS.md`](LIMITATIONS.md) — scope limits and non-audit disclaimer
- [`ROADMAP.md`](ROADMAP.md) — planned next steps
- [`notes/curve-review-notes.md`](notes/curve-review-notes.md) — public review note
- [`notes/final-review.md`](notes/final-review.md) — internal-style final review summary

## Disclaimer

This repository is not a full protocol audit and does not prove the absence of vulnerabilities.

It is a focused security research artifact intended to clarify selected StableSwap and StableSwap NG accounting boundaries.
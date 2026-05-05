# Roadmap

This repository is intended to be a focused Curve StableSwap security research artifact, not a full Curve analytics platform.

The planned final shape is:

```text
StableSwap NG accounting review
+ read-only reentrancy / LP oracle manipulation case study
+ focused Python simulation notebooks
```

After those are complete, this repo should move into maintenance mode rather than expanding into a Curve encyclopedia.

## Phase 1 — StableSwap NG accounting lab

Status: complete

Completed:

- StableSwap math characterization
- Dynamic fee characterization
- Stored-rate / asset-type tests
- ERC4626 donation behavior
- Rebasing vs plain accounting
- `exchange_received`
- Admin fee unit conversion
- Quote/execution freshness
- MetaZap dust characterization
- Selected real StableSwap NG integration checks
- Review notes, final review, invariants, and test plan

Artifacts:

- `notes/curve-review-notes.md`
- `notes/final-review.md`
- `notes/invariants.md`
- `notes/test-plan.md`
- `notes/function-notes.md`
- `contracts/`
- `tests/`

## Phase 2 — Python simulation package

Status: complete

Completed:

- `src/curve_stableswap_lab/stableswap_math.py`
- `src/curve_stableswap_lab/dynamic_fee.py`
- `src/curve_stableswap_lab/scenarios.py`
- `src/curve_stableswap_lab/plotting.py`
- Python unit tests for simulation modules

Current local result:

```bash
uv run pytest tests -q
# 109 passed
```

Purpose:

- keep notebook logic reusable and testable
- avoid putting core math directly into notebooks
- support small, reproducible simulation artifacts

## Phase 3 — Simulation notebooks

Status: complete / final polish pending

Completed:

- `notebooks/01_amp_slippage_surface.ipynb`
  - visualizes how amplification `A` changes near-peg slippage
- `notebooks/02_dynamic_fee_imbalance.ipynb`
  - visualizes how off-peg dynamic fee responds to imbalance
- `notebooks/03_quote_staleness_rate_change.ipynb`
  - visualizes how rate changes can make quote and execution values diverge

Generated outputs:

- `outputs/figures/amp_slippage_surface.png`
- `outputs/figures/amp_output_efficiency.png`
- `outputs/figures/dynamic_fee_imbalance.png`
- `outputs/figures/dynamic_fee_vs_imbalance.png`
- `outputs/figures/quote_staleness_rate_change.png`
- `outputs/figures/quote_staleness_abs_error.png`
- `outputs/tables/amp_slippage_surface.csv`
- `outputs/tables/dynamic_fee_imbalance.csv`
- `outputs/tables/quote_staleness_rate_change.csv`

Goal:

- visualize how `A`, imbalance, dynamic fees, and rate changes affect quotes and LP/accounting behavior
- connect StableSwap math to audit-relevant assumptions
- keep the simulation scope narrow and security-oriented

## Phase 4 — Historical attack case study

Status: initial toy reproduction complete

Completed:

- Curve read-only reentrancy / LP oracle manipulation toy reproduction
- vulnerable virtual-price inflation test
- external consumer overvaluation test
- direct-borrow control tests
- safe-ordering mitigation tests
- case-study draft

Current local result:

```bash
uv run pytest historical-attacks/curve-readonly-reentrancy/tests -q
# 7 passed
```

Artifacts:

- `historical-attacks/curve-readonly-reentrancy/README.md`
- `historical-attacks/curve-readonly-reentrancy/mechanism.md`
- `historical-attacks/curve-readonly-reentrancy/threat-model.md`
- `historical-attacks/curve-readonly-reentrancy/case-study.md`
- `historical-attacks/curve-readonly-reentrancy/contracts/`
- `historical-attacks/curve-readonly-reentrancy/tests/`

Main lesson:

```text
A view function can be mathematically correct and read-only,
while still being unsafe as an oracle input during a transient accounting state.
```

## Phase 5 — Final repo polish

Status: pending

Planned:

- update README final status
- ensure all test counts are current
- clean `__pycache__` and notebook checkpoints
- verify generated figures and tables are either committed or intentionally ignored
- add a small diagram or Mermaid flow if useful
- write a short final summary article / post
- push final version and keep the repo pinned on GitHub profile

Potential final article:

```text
Curve StableSwap: When AMM Math Becomes an Accounting Security Problem
```

Core themes:

- StableSwap math is only one layer
- `stored_rates` and `xp` define the economic interpretation of balances
- dynamic fee depends on value-space comparability
- quote freshness matters for rate-dependent assets
- LP virtual price can become dangerous when consumed during transient state
- safe protocol design requires state-consistency reasoning, not only formula correctness

## Deferred / out of scope

These topics are intentionally deferred to avoid turning this repo into a large Curve analytics platform:

- full Curve V2 / CryptoPool analysis
- full on-chain Curve analytics dashboard
- multi-pool stablecoin arbitrage backtesting
- real depeg event reconstruction
- complete MetaZapNG production reproduction
- full Curve ecosystem incident database
- unrelated historical attacks outside Curve / StableSwap context

Potential future standalone artifacts:

- `erc4626-inflation-case-study`
- `compound-lending-review`
- `gmx-risk-engine-lab`
- `pancakeswap-amm-review`
- `defi-oracle-manipulation-lab`

## Final closeout criteria

This repo can be considered complete when:

- main test suite passes
- historical attack tests pass
- all three notebooks are present and readable
- key figures and tables are generated
- README and ROADMAP reflect current status
- historical case study has clear limitations
- the repo can serve as a pinned flagship artifact for DeFi financial-security review work
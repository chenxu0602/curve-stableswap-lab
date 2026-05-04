# Roadmap

## Phase 1 — StableSwap NG accounting lab

Status: mostly complete

- StableSwap math characterization
- Dynamic fee characterization
- Stored-rate / asset-type tests
- ERC4626 donation behavior
- Rebasing vs plain accounting
- `exchange_received`
- Admin fee unit conversion
- Quote/execution freshness
- MetaZap dust characterization

## Phase 2 — Simulation notebooks

Planned:

- `01_amp_slippage_surface.ipynb`
- `02_dynamic_fee_imbalance.ipynb`
- `03_quote_staleness_rate_change.ipynb`

Goal:
- visualize how `A`, imbalance, dynamic fees, and rate changes affect quotes and LP/accounting behavior

## Phase 3 — Real NG integration expansion

Planned:

- factory negative tests
- metapool underlying quote vs nested execution
- `get_dx` reverse-quote approximation
- deeper MetaZapNG nested path tests

## Phase 4 — Historical attack case study

Planned:

- Curve read-only reentrancy / LP oracle manipulation toy reproduction
- mechanism explanation
- minimal tests
- security lessons for external integrators
# Curve StableSwap Lab

Security-oriented research lab for Curve StableSwap and StableSwap NG.

This repository studies Curve-style AMM accounting from an auditing perspective: invariant math, normalized balances, rate providers, ERC4626 conversion, rebasing tokens, quote/execution freshness, admin-fee unit accounting, and zap temporary custody.

This is not a full protocol audit. It is a focused research and characterization artifact.

## Core mental model

```text
balances -> stored_rates -> xp -> D / y -> LP supply / virtual price
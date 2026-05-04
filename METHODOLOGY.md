
---

# METHODOLOGY.md

这个文件说明你的审计方法，不要太长。

```md
# Methodology

This lab uses small, explainable tests to characterize Curve StableSwap and StableSwap NG accounting behavior.

The review approach is:

1. Start from the StableSwap math kernel.
2. Identify how raw token balances become normalized `xp`.
3. Test semantic boundaries introduced by NG:
   - asset types
   - rate providers
   - ERC4626 conversion
   - rebasing balance drift
   - optimistic transfer settlement
4. Compare quotes with execution under unchanged and changed state.
5. Separate characterization from vulnerability claims.

## Characterization vs vulnerability

Not every surprising behavior is a vulnerability.

A behavior becomes security-relevant when it:
- transfers value unexpectedly
- breaks slippage protection
- dilutes LPs
- traps funds
- violates documented assumptions
- causes persistent quote/execution deception
- allows unsafe permissionless deployment configuration

## Test style

The repo uses:
- local Vyper harnesses
- Boa / Moccasin / pytest
- small deterministic scenario tests
- selected real StableSwap NG integration tests

The goal is not maximum test volume. The goal is high-signal tests that isolate one accounting boundary at a time.
# Limitations

This repository is not a full audit of Curve Finance or StableSwap NG.

It does not prove:
- full production deployment safety
- full factory governance safety
- exhaustive metapool safety
- exhaustive MetaZapNG safety
- full legacy Curve pool-family coverage
- full gauge / reward safety
- absence of vulnerabilities

The tests are designed to characterize selected mechanisms and accounting boundaries.

Some tests use simplified harnesses. Harness-level behavior is used to isolate mechanisms and should not be treated as proof of exploitability in production contracts unless confirmed against real protocol paths.
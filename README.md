<div align="center">

# secp256k1 GA Variants

### Genetic Algorithm Approaches to the Elliptic Curve Discrete Logarithm Problem

[![Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

</div>

---

Collection of genetic algorithm implementations targeting the discrete logarithm problem on the secp256k1 elliptic curve. Contains 81 scripts exploring different fitness functions, population strategies, mutation operators, and hybrid approaches combining GAs with algebraic and lattice-based methods.

## Repository Structure

```
secp256k1-ga-variants/
├── adaptive_hex/          # Hex-aware adaptive mutation with population scaling
├── attack_research/       # Algebraic attack implementations (Fermat, CRT, BSGS, endomorphism)
├── cascade_formulas/      # Multi-stage cascade attack combining GA with lattice methods
├── deathnote/             # Hash160-targeted adaptive search with mathematical feedback
├── ga_framework/          # Structured GA framework with multiple strategies
│   ├── ff1ga/             #   FF1GA: SAT-solver-inspired fitness with clause satisfaction
│   ├── group_theory/      #   Group-theoretic decomposition with Hebbian learning
│   ├── multi_curve/       #   Cross-curve GA exploiting multiple elliptic curves
│   ├── neural/            #   Neural-network-guided mutation and quantum-chaotic search
│   ├── single_target/     #   Single-target adaptive hex with DE and PCA
│   └── ultimate/          #   Combined multi-strategy attack demonstration
├── misc_variants/         # Correlation-based, PCA-guided, and pattern discovery variants
├── ultra_advanced/        # Differential evolution with PCA and mirror-key analysis
└── zero_resonance/        # Zero-byte pattern and sparse surface analysis
```

## Approach Summary

- **FF1GA Framework**: Treats ECDLP as a SAT-like problem with clause-based fitness, stagnation detection, brute-force fallback for small subproblems, and configurable iteration budgets
- **Adaptive Hex**: Population-based search with per-nibble mutation rates that adapt based on fitness landscape feedback and hex-position entropy
- **Neural-Guided GA**: Uses lightweight neural networks to learn mutation distributions from elite population members
- **Group Theory Hybrid**: Decomposes the search using algebraic subgroup structure and Hebbian weight updates
- **Multi-Curve**: Exploits geometric constraints across NIST P-224, P-256, P-384, P-521, and secp256k1
- **Cascade Formulas**: Chains partial results from algebraic attacks into GA seed populations

## Requirements

- Python 3.10+
- Core: `numpy`, `ecdsa` or `coincurve`, `pycryptodome`
- Optional: `gmpy2`, `cupy`, `matplotlib`, `scikit-learn`

## Author

**Andrew Dorman**
Independent Researcher -- Southlake, TX
GitHub: [ACD421](https://github.com/ACD421)

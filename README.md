# secp256k1 GA Variants

**Author:** Andrew Dorman ([Hollow Point Labs](https://github.com/ACD421))

Complete collection of genetic algorithm research iterations for Bitcoin key analysis. Each file represents a distinct research approach with unique parameters, algorithms, or mathematical insights. These are the raw research iterations -- every one matters.

## Structure

### `adaptive_hex/` -- Adaptive Hex GA Family

| File | Original | Description |
|------|----------|-------------|
| `murder_adaptive_hex.py` | murder.py | Adaptive hex-level genetic algorithm |
| `null_hypothesis_test.py` | null.py | Null hypothesis testing framework |
| `adaptive_hex_8k_pop.py` | 20k.py | Large population (8K+) adaptive hex search |
| `analysis_brain_ga.py` | arg.py | Analysis-driven brain GA variant |
| `speed_demon_ga.py` | bangbang.py | Speed-optimized GA with aggressive mutation |
| `ripemd160_20k_pop.py` | cosmos.py | RIPEMD-160 focused, 20K population |
| `high_pressure_demo.py` | jerry.py | High selection pressure demonstration |

### `ultra_advanced/` -- Ultra Advanced / Post-Analysis

| File | Original | Description |
|------|----------|-------------|
| `ultra_advanced_de_pca.py` | final.py | Differential Evolution + PCA hybrid |
| `postmortem_analysis.py` | thepower.py | Post-mortem analysis of near-miss patterns |
| `mirror_key_analysis.py` | overpower.py | Mirror key / complementary key analysis |
| `mirror_key_enhanced.py` | overpowered.py | Enhanced mirror key with additional constraints |

### `deathnote/` -- DeathNote Series

| File | Original | Description |
|------|----------|-------------|
| `deathnote_hash160_hunter.py` | DeathNote.py | Hash160 targeted hunter with adaptive learning |
| `math_adaptive_hash160.py` | death.py | Mathematically adaptive Hash160 approach |
| `deathnote_redux.py` | redeathnote.py | DeathNote rewritten with refined parameters |

### `cascade_formulas/` -- Cascade Formula Explorations

| File | Original | Description |
|------|----------|-------------|
| `cascade_backdoor_test.py` | bang.py | Cascade formula backdoor hypothesis test |
| `cascade_wild_formulas.py` | chunk.py | Wild formula generation and testing |
| `lattice_256bit_test.py` | chunker.py | 256-bit lattice reduction approach |
| `cascade_full_send.py` | chunky.py | Full cascade formula battery |
| `cascade_correct.py` | cry.py | Corrected cascade implementation |
| `cascade_multi_scale_field.py` | doll.py | Multi-scale field cascade analysis |
| `cascade_solid.py` | lockedin.py | Solidified cascade approach |
| `cascade_multi_scale_v3.py` | pi.py | Multi-scale cascade v3 with pi-based constants |

### `zero_resonance/` -- Zero Pattern / Resonance Analysis

| File | Original | Description |
|------|----------|-------------|
| `zero_resonance_attack.py` | 0.py | Zero-resonance attack vector exploration |
| `privkey_hash160_correlation.py` | 0s.py | Private key to Hash160 correlation mapping |
| `zero_pattern_test.py` | ffs.py | Zero bit pattern significance testing |
| `sparse_surface_backdoor.py` | suspectzero.py | Sparse surface backdoor hypothesis |
| `suspicious_zero.py` | suszero.py | Suspicious zero-pattern investigation |

### `misc_variants/` -- Miscellaneous Research Variants

| File | Original | Description |
|------|----------|-------------|
| `cascade_prediction_validator.py` | accu.py | Cascade formula prediction validation |
| `pubkey_cascade_attack.py` | boop.py | Public key cascade attack vector |
| `hash160_leak_analyzer.py` | break.py | Hash160 information leakage analysis |
| `privkey_recovery_crt.py` | buggy.py | Private key recovery via CRT |
| `consensus_center_pca.py` | bullseye.py | Consensus center finding with PCA |
| `privkey_recovery_xor.py` | butthole.py | XOR-based private key recovery |
| `chaos_fiber_exploit.py` | cream.py | Chaos theory + fiber bundle exploit |
| `ecc_pattern_discovery.py` | disc.py | ECC structural pattern discovery |
| `xor_pattern_address.py` | disc1.py | XOR pattern in address generation |
| `bit_flip_enumeration.py` | end.py | Systematic bit-flip enumeration |
| `near_miss_diagnostic.py` | fail.py | Near-miss diagnostic and learning |
| `correlation_sat_ga.py` | hope.py | SAT + GA correlation hybrid |
| `ecc_validation_suite.py` | sensational.py | ECC validation and verification suite |

## Dependencies

```bash
pip install gmpy2 coincurve numpy scipy scikit-learn
```

## License

MIT License. See [LICENSE](LICENSE) for details.

#!/usr/bin/env python3
"""
Single Target Adaptive Hex-Aware GA - NO DIVERSITY CONSTRAINTS
Only change: Elite pool accepts duplicates with same scores, rejects duplicate keys
"""

import time
import random
import math
import hashlib
import struct
from typing import List, Tuple, Callable, Optional, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import deque
import copy
import statistics

# Your existing imports
try:
    import numpy as np
    try:
        import coincurve
        CRYPTO_ENGINE = 'coincurve'
    except ImportError:
        from ecdsa import SECP256k1, SigningKey
        CRYPTO_ENGINE = 'ecdsa'

    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os

except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "ecdsa", "pycryptodome"])

    import numpy as np
    from ecdsa import SECP256k1, SigningKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os
    CRYPTO_ENGINE = 'ecdsa'

print(f"✅ Loaded with {CRYPTO_ENGINE} crypto engine")

# PUT YOUR TARGET HASH160 HERE (40 hex characters)
TARGET_HASH160 = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"  # ← CHANGE THIS TO YOUR TARGET

@dataclass
class SingleTargetConfig:
    """Configuration for single target adaptive hex GA"""
    K_POOL: int = 8000                    # Population size
    ELITE_SIZE: int = 400                 # Elite pool size
    MIN_ELITE_DIVERSITY: float = 8.0
    DIVERSITY_THRESHOLD: float = 12.0

    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MUTATION_INCREASE: float = 1.3
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 1.2

    STAGNATION_ROUNDS: int = 4
    DIVERSITY_INJECTION_RATE: float = 0.4

    # Adaptive hex learning parameters - UNCONSTRAINED
    INITIAL_ACTIVE_BYTES: int = 1         # Start with 1 active byte
    MAX_ACTIVE_BYTES: int = 32            # Full 32 bytes - NO LIMITS
    EXPANSION_THRESHOLD: float = 0.05     # Expand on ANY improvement (5%)
    CONTRACTION_THRESHOLD: float = 0.1    # Very conservative contraction
    RANGE_ADAPTATION_FREQ: int = 2        # Check every 2 rounds - faster adaptation
    AGGRESSIVE_EXPANSION: bool = True     # Force exploration of larger ranges

    # Position learning - UNBIASED
    POSITION_LEARNING_RATE: float = 0.08  # Slower learning to avoid lock-in
    POSITION_DECAY: float = 0.98          # Lighter decay
    GLOBAL_WEIGHT_DECAY: float = 0.998    # Lighter global decay
    MIN_POSITION_WEIGHT: float = 0.05     # Higher minimum
    MAX_POSITION_WEIGHT: float = 0.75     # Lower maximum

    # Single target specific
    MAX_ROUNDS: int = 100000                # More rounds for single target
    DETAILED_LOGGING: bool = True         # Show detailed learning progress

class AdaptiveHexManager:
    """Manages adaptive hex range expansion/contraction and position learning"""

    def __init__(self, config: SingleTargetConfig):
        self.config = config
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.max_tested_bytes = config.INITIAL_ACTIVE_BYTES

        # Position importance weights (learned adaptively)
        self.position_weights = np.ones(32, dtype=np.float32)
        self.position_usage_stats = np.zeros(32, dtype=np.float32)
        self.position_performance = np.zeros(32, dtype=np.float32)

        # Range performance tracking
        self.range_performance = {}  # byte_range -> [improvements]
        self.generation_count = 0

        # Learning history for analysis
        self.learning_history = []

        self.lock = threading.RLock()

        print(f"🧠 Adaptive Hex Manager initialized")
        print(f"🧠 Starting with {self.current_active_bytes} active bytes")
        print(f"🧠 Position learning rate: {config.POSITION_LEARNING_RATE}")

    def get_active_range(self) -> int:
        """Get current maximum value for active bytes"""
        if self.current_active_bytes <= 0:
            return 1
        elif self.current_active_bytes == 1:
            return 0xFF
        elif self.current_active_bytes == 2:
            return 0xFFFF
        elif self.current_active_bytes == 3:
            return 0xFFFFFF
        elif self.current_active_bytes == 4:
            return 0xFFFFFFFF
        else:
            return min((2 ** (self.current_active_bytes * 8)) - 1, 2**256 - 1)

    def generate_adaptive_key(self) -> bytes:
        """Generate key using current active range and learned position weights"""
        with self.lock:
            self.generation_count += 1

            max_value = self.get_active_range()

            # Choose generation strategy based on learned patterns
            if random.random() < 0.8:  # 80% focused on learned patterns
                key_value = self._generate_position_focused_key(max_value)
            else:  # 20% exploration
                key_value = self._generate_exploratory_key(max_value)

            return key_value.to_bytes(32, 'big')

    def _generate_position_focused_key(self, max_value: int) -> int:
        """Generate key focusing on learned positions - UNBIASED WITHIN RANGE"""
        key_bytes = [0] * 32

        # Fill bytes based on position weights - BUT USE FULL RANGE
        for byte_pos in range(min(self.current_active_bytes, 32)):
            weight = self.position_weights[byte_pos]

            # Higher weight = more likely to use this position, but FULL VALUE RANGE
            if random.random() < min(0.9, weight + 0.2):
                if random.random() < 0.4:  # REDUCED bias toward patterns
                    # Use random values across full byte range
                    key_bytes[byte_pos] = random.randint(0, 255)
                else:
                    # Still some pattern usage but less dominant
                    if random.random() < 0.5:
                        patterns = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF]
                        key_bytes[byte_pos] = random.choice(patterns)
                    else:
                        key_bytes[byte_pos] = random.randint(1, 255)

        # Convert to int (little endian for natural progression)
        key_value = 0
        for i, byte_val in enumerate(key_bytes[:self.current_active_bytes]):
            key_value += byte_val * (256 ** i)

        return max(1, min(key_value, max_value))

    def _generate_exploratory_key(self, max_value: int) -> int:
        """Generate exploratory key - FULL RANGE EXPLORATION"""
        # REMOVE BIAS - explore the full range more aggressively
        exploration_patterns = [
            lambda: random.randint(1, max_value),  # Pure random in full range
            lambda: random.randint(max_value // 2, max_value),  # Upper half
            lambda: random.randint(max_value // 4, max_value // 2),  # Middle ranges
            lambda: random.randint(1, max_value // 10),  # Small values (reduced weight)
            lambda: int(max_value * (random.random() ** 0.5)),  # Square root distribution
            lambda: int(max_value * random.random()),  # Linear distribution
        ]

        # Give equal weight to all patterns - NO BIAS toward small values
        pattern_func = random.choice(exploration_patterns)
        try:
            return max(1, min(pattern_func(), max_value))
        except:
            return random.randint(1, max_value)  # Fallback to full range

    def learn_from_mutation(self, old_key: bytes, new_key: bytes, improvement: float):
        """Learn which positions and ranges are effective"""
        if improvement <= 0:
            return

        with self.lock:
            # Learn position importance
            for byte_pos in range(min(self.current_active_bytes, 32)):
                if byte_pos < len(old_key) and byte_pos < len(new_key):
                    old_byte = old_key[byte_pos]
                    new_byte = new_key[byte_pos]

                    if old_byte != new_byte:
                        # This position contributed to improvement
                        learning_factor = improvement * self.config.POSITION_LEARNING_RATE
                        old_weight = self.position_weights[byte_pos]
                        new_weight = min(self.config.MAX_POSITION_WEIGHT, old_weight + learning_factor)
                        self.position_weights[byte_pos] = new_weight
                        self.position_performance[byte_pos] += improvement
                        self.position_usage_stats[byte_pos] += 1

                        if self.config.DETAILED_LOGGING and learning_factor > 0.01:
                            print(f"        🧠 Learned: position {byte_pos} weight "
                                  f"{old_weight:.3f} → {self.position_weights[byte_pos]:.3f} "
                                  f"(improvement: {improvement:.3f})")

            # Record learning event
            self.learning_history.append({
                'generation': self.generation_count,
                'improvement': improvement,
                'active_bytes': self.current_active_bytes,
                'position_weights': self.position_weights.copy(),
                'old_key_int': int.from_bytes(old_key, 'big'),
                'new_key_int': int.from_bytes(new_key, 'big')
            })

            # Decay unused positions gradually
            for byte_pos in range(32):
                if byte_pos >= self.current_active_bytes:
                    self.position_weights[byte_pos] *= self.config.POSITION_DECAY
                    self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                        self.position_weights[byte_pos])

    def apply_global_weight_decay(self):
        """Apply heavy weight decay per round to prevent lock-in"""
        with self.lock:
            for byte_pos in range(32):
                # Apply global decay to all positions
                self.position_weights[byte_pos] *= self.config.GLOBAL_WEIGHT_DECAY
                # Ensure minimum weight
                self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                    self.position_weights[byte_pos])

            if self.config.DETAILED_LOGGING and self.generation_count % 5000 == 0:
                avg_weight = np.mean(self.position_weights[:self.current_active_bytes])
                print(f"        🔄 Global weight decay applied, avg weight: {avg_weight:.3f}")

    def reset_position_weights(self):
        """Reset position weights when locked in local optimum"""
        with self.lock:
            # Reset to moderate values instead of 1.0 to encourage exploration
            self.position_weights = np.full(32, 0.3, dtype=np.float32)
            print(f"        🔄 Position weights reset to 0.3 for exploration")

    def analyze_population_ranges(self, population: List[bytes], scores: List[int]):
        """Analyze which key ranges are performing well"""
        if not population:
            return

        with self.lock:
            range_improvements = {}

            for key, score in zip(population, scores):
                if score >= 160:
                    continue

                # Find effective byte length
                effective_bytes = 1
                key_int = int.from_bytes(key, 'big')
                if key_int > 0:
                    effective_bytes = (key_int.bit_length() + 7) // 8

                effective_bytes = max(1, min(effective_bytes, 32))

                improvement = 160 - score  # Higher is better
                if effective_bytes not in range_improvements:
                    range_improvements[effective_bytes] = []
                range_improvements[effective_bytes].append(improvement)

            # Update range performance history
            for byte_range, improvements in range_improvements.items():
                if improvements:
                    avg_improvement = statistics.mean(improvements)
                    if byte_range not in self.range_performance:
                        self.range_performance[byte_range] = []
                    self.range_performance[byte_range].append(avg_improvement)

                    # Keep only recent history
                    if len(self.range_performance[byte_range]) > 10:
                        self.range_performance[byte_range] = self.range_performance[byte_range][-10:]

    def adapt_active_range(self, round_num: int, elite_scores: List[int]):
        """PURELY PERFORMANCE-DRIVEN adaptive range - NO ARTIFICIAL GUIDANCE"""
        if round_num % self.config.RANGE_ADAPTATION_FREQ != 0:
            return

        with self.lock:
            old_range = self.current_active_bytes

            # ONLY expand/contract based on ACTUAL performance data
            if len(self.range_performance) >= 2:
                current_avg_perf = 0
                if self.current_active_bytes in self.range_performance:
                    recent_perfs = self.range_performance[self.current_active_bytes]
                    current_avg_perf = statistics.mean(recent_perfs) if recent_perfs else 0

                # Check if larger ranges are performing better
                larger_ranges = [r for r in self.range_performance.keys()
                               if r > self.current_active_bytes]
                best_larger_perf = 0
                if larger_ranges:
                    larger_perfs = []
                    for r in larger_ranges:
                        if self.range_performance[r]:
                            larger_perfs.extend(self.range_performance[r])
                    if larger_perfs:
                        best_larger_perf = max(larger_perfs)  # Best, not average

                # Check if smaller ranges are performing better
                smaller_ranges = [r for r in self.range_performance.keys()
                                if r < self.current_active_bytes and r >= 1]
                best_smaller_perf = 0
                if smaller_ranges:
                    smaller_perfs = []
                    for r in smaller_ranges:
                        if self.range_performance[r]:
                            smaller_perfs.extend(self.range_performance[r])
                    if smaller_perfs:
                        best_smaller_perf = max(smaller_perfs)  # Best, not average

                # PURE PERFORMANCE DECISION - go where the best results are
                if (best_larger_perf > current_avg_perf and
                    best_larger_perf > best_smaller_perf and
                    self.current_active_bytes < self.config.MAX_ACTIVE_BYTES):
                    self.current_active_bytes = min(self.current_active_bytes + 1,
                                                  self.config.MAX_ACTIVE_BYTES)
                    print(f"    🔧 EXPANDING hex range: {old_range} → {self.current_active_bytes} bytes "
                          f"(better performance: {best_larger_perf:.1f} vs current: {current_avg_perf:.1f})")

                elif (best_smaller_perf > current_avg_perf and
                      best_smaller_perf > best_larger_perf and
                      self.current_active_bytes > 1):
                    self.current_active_bytes = max(1, self.current_active_bytes - 1)
                    print(f"    🔧 CONTRACTING hex range: {old_range} → {self.current_active_bytes} bytes "
                          f"(better performance: {best_smaller_perf:.1f} vs current: {current_avg_perf:.1f})")

            # NO FORCED EXPANSION - let performance guide everything

    def get_detailed_stats(self) -> dict:
        """Get comprehensive statistics for analysis"""
        with self.lock:
            active_positions = np.sum(self.position_weights[:self.current_active_bytes] > 0.5)
            highly_active_positions = np.sum(self.position_weights[:self.current_active_bytes] > 0.8)
            avg_position_weight = np.mean(self.position_weights[:self.current_active_bytes])

            # Top performing positions
            top_positions = []
            for i in range(min(self.current_active_bytes, 10)):
                if self.position_weights[i] > 0.3:
                    top_positions.append({
                        'position': i,
                        'weight': float(self.position_weights[i]),
                        'usage_count': float(self.position_usage_stats[i]),
                        'total_performance': float(self.position_performance[i])
                    })

            top_positions.sort(key=lambda x: x['weight'], reverse=True)

            return {
                'current_active_bytes': self.current_active_bytes,
                'max_value': f"0x{self.get_active_range():X}",
                'active_positions': int(active_positions),
                'highly_active_positions': int(highly_active_positions),
                'avg_position_weight': float(avg_position_weight),
                'generation_count': self.generation_count,
                'top_positions': top_positions[:5],
                'range_performance_summary': {
                    k: statistics.mean(v) if v else 0
                    for k, v in self.range_performance.items()
                },
                'learning_events': len(self.learning_history)
            }

class SingleTargetAtomics:
    """Atomics for single target testing"""
    def __init__(self, config: SingleTargetConfig):
        self.config = config
        self.global_best_score = Value('i', 160, lock=True)
        self.global_improvements = Value('L', 0, lock=True)
        self.global_evaluations = Value('L', 0, lock=True)
        self.best_key_bytes = Array('B', 32, lock=True)
        self.mutation_strength = Value('f', config.MUTATION_STRENGTH, lock=True)
        self.last_improvement_round = Value('i', 0, lock=True)
        self.start_time = Value('d', 0.0, lock=True)

    def atomic_increment_evals(self, count: int = 1) -> int:
        with self.global_evaluations.get_lock():
            old_val = self.global_evaluations.value
            self.global_evaluations.value = old_val + count
            return self.global_evaluations.value

    def try_update_global_best(self, new_score: int, new_key: bytes) -> bool:
        with self.global_best_score.get_lock():
            current_best = self.global_best_score.value
            if new_score < current_best:
                self.global_best_score.value = new_score
                with self.global_improvements.get_lock():
                    self.global_improvements.value += 1
                with self.best_key_bytes.get_lock():
                    for i, byte_val in enumerate(new_key[:32]):
                        self.best_key_bytes[i] = byte_val
                return True
        return False

    def get_best_key(self) -> bytes:
        with self.best_key_bytes.get_lock():
            return bytes(self.best_key_bytes[:32])

    def atomic_get_all_stats(self) -> dict:
        with self.global_best_score.get_lock():
            best_score = self.global_best_score.value
        with self.global_improvements.get_lock():
            improvements = self.global_improvements.value
        with self.global_evaluations.get_lock():
            evaluations = self.global_evaluations.value
        with self.mutation_strength.get_lock():
            mutation_strength = self.mutation_strength.value

        return {
            'best_score': best_score,
            'improvements': improvements,
            'evaluations': evaluations,
            'mutation_strength': mutation_strength
        }

    def atomic_update_mutation_strength(self, multiplier: float) -> float:
        with self.mutation_strength.get_lock():
            old_value = self.mutation_strength.value
            new_value = old_value * multiplier
            new_value = max(self.config.MUTATION_MIN, min(self.config.MUTATION_MAX, new_value))
            self.mutation_strength.value = new_value
            return new_value

class CryptoOps:
    """Crypto operations"""
    def __init__(self):
        self.engine = CRYPTO_ENGINE

    def scalar_mult_secp256k1(self, private_key: bytes) -> bytes:
        if len(private_key) != 32:
            raise ValueError("Private key must be 32 bytes")

        try:
            if self.engine == 'coincurve':
                privkey = coincurve.PrivateKey(private_key)
                return privkey.public_key.format(compressed=True)
            else:
                priv_int = int.from_bytes(private_key, 'big')
                if priv_int == 0 or priv_int >= SECP256k1.order:
                    priv_int = priv_int % (SECP256k1.order - 1) + 1
                    private_key = priv_int.to_bytes(32, 'big')

                sk = SigningKey.from_string(private_key, curve=SECP256k1)
                vk = sk.verifying_key
                point = vk.pubkey.point

                x = point.x()
                y = point.y()
                prefix = 0x02 if (y % 2 == 0) else 0x03
                x_bytes = x.to_bytes(32, 'big')
                return bytes([prefix]) + x_bytes
        except Exception:
            return b'\x02' + b'\x00' * 32

    def hash160(self, data: bytes) -> bytes:
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()

    def private_key_to_hash160(self, private_key: bytes) -> bytes:
        pubkey = self.scalar_mult_secp256k1(private_key)
        return self.hash160(pubkey)

def hamming_distance_160(h1: bytes, h2: bytes) -> int:
    if len(h1) != 20 or len(h2) != 20:
        return 160
    distance = 0
    for i in range(20):
        xor_byte = h1[i] ^ h2[i]
        distance += bin(xor_byte).count('1')
    return distance

def calculate_key_diversity_bits(key1: bytes, key2: bytes) -> float:
    if len(key1) != 32 or len(key2) != 32:
        return 0.0
    return float(sum(a != b for a, b in zip(key1, key2)))

def enhanced_fitness(hash160: bytes, target_hash: bytes) -> float:
    """Enhanced fitness with hex match weighting"""
    hd = hamming_distance_160(hash160, target_hash)
    hex_matches = sum(a == b for a, b in zip(hash160.hex(), target_hash.hex()))
    return hd - (hex_matches * 0.1)

class SingleTargetEngine:
    """Single target adaptive hex-aware GA engine"""

    def __init__(self, config: SingleTargetConfig):
        self.config = config
        self.crypto = CryptoOps()
        self.hex_manager = AdaptiveHexManager(config)
        self.atomics = SingleTargetAtomics(config)

        # Population storage
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.elite_scores = []

        self.target_hash = None

        print(f"🚀 Single Target Adaptive Hex Engine initialized")
        print(f"🚀 Population: {self.config.K_POOL}, Elite: {self.config.ELITE_SIZE}")
        print(f"🧠 Max rounds: {self.config.MAX_ROUNDS}")

    def score_key(self, private_key: bytes) -> int:
        try:
            self.atomics.atomic_increment_evals(1)
            hash160 = self.crypto.private_key_to_hash160(private_key)
            distance = enhanced_fitness(hash160, self.target_hash)
            distance_int = int(round(distance))
            improved = self.atomics.try_update_global_best(distance_int, private_key)

            if improved:
                key_int = int.from_bytes(private_key, 'big')
                print(f"      🎯 NEW GLOBAL BEST: {distance_int} bits (key: 0x{key_int:X})")

            return distance_int
        except Exception:
            return 160

    def adaptive_mutate_key(self, key: bytes, strength: float) -> bytes:
        """UNBIASED position-aware mutation across full active range"""
        try:
            active_bytes = self.hex_manager.current_active_bytes
            max_range = self.hex_manager.get_active_range()

            # Convert to working integer
            key_int = int.from_bytes(key, 'big')
            if key_int > max_range:
                key_int = key_int % max_range
            key_int = max(1, key_int)

            mutations = []

            # Position-weighted byte mutations - BUT UNBIASED VALUE DISTRIBUTION
            key_bytes = list(key)
            for byte_pos in range(min(active_bytes, 32)):
                position_weight = self.hex_manager.position_weights[byte_pos]
                mutation_prob = strength * position_weight * 0.6  # Reduced dominance

                if random.random() < mutation_prob:
                    old_byte = key_bytes[byte_pos]
                    if random.random() < 0.5:  # Equal chance for different mutation types
                        # Full range random byte
                        key_bytes[byte_pos] = random.randint(0, 255)
                    elif random.random() < 0.5:
                        # Small adjustments
                        delta = random.randint(-50, 50)  # Larger deltas
                        key_bytes[byte_pos] = max(0, min(255, old_byte + delta))
                    else:
                        # Pattern-based (reduced weight)
                        patterns = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF,
                                  0x7F, 0x3F, 0x1F, 0x0F]  # More patterns
                        key_bytes[byte_pos] = random.choice(patterns)

            mutations.append(bytes(key_bytes))

            # Integer-level mutations in FULL active range
            for i in range(4):  # More mutations
                if random.random() < strength:
                    # Scale delta by current range - MUCH LARGER DELTAS
                    delta_range = max(1000, int(max_range * strength * 0.1))  # 10% of range
                    delta = random.randint(-delta_range, delta_range)
                    new_int = max(1, min(key_int + delta, max_range))
                    mutations.append(new_int.to_bytes(32, 'big'))

            # Bit flips across FULL active range
            if random.random() < strength:
                max_bit = min(255, active_bytes * 8 - 1)
                # Try multiple bit flips
                for _ in range(random.randint(1, 3)):
                    bit_pos = random.randint(0, max_bit)
                    new_int = key_int ^ (1 << bit_pos)
                    new_int = max(1, min(new_int, max_range))
                    mutations.append(new_int.to_bytes(32, 'big'))

            # Mathematical operations with LARGER factors
            if random.random() < strength * 0.8:  # Increased probability
                operations = [
                    lambda x: min(x * random.randint(2, 10), max_range),  # Larger multipliers
                    lambda x: max(1, x // random.randint(2, 10)),       # Larger divisors
                    lambda x: max(1, min(x + random.randint(1000, 100000), max_range)),  # Large additions
                    lambda x: max(1, x - random.randint(1000, 100000)),  # Large subtractions
                    lambda x: max(1, min(x ^ random.randint(1, max_range // 100), max_range)),  # XOR
                ]
                op = random.choice(operations)
                try:
                    new_int = op(key_int)
                    mutations.append(new_int.to_bytes(32, 'big'))
                except:
                    pass

            return random.choice(mutations) if mutations else key

        except Exception:
            return key

    def evolve_individual(self, base_key: bytes) -> List[bytes]:
        """Generate candidates using adaptive hex approach"""
        candidates = []
        current_strength = self.atomics.atomic_get_all_stats()['mutation_strength']

        # Multiple adaptive mutations with varying strength
        for i in range(5):
            try:
                varying_strength = current_strength * (0.4 + i * 0.2)
                mutated = self.adaptive_mutate_key(base_key, varying_strength)
                candidates.append(mutated)
            except Exception:
                continue

        # Elite crossover with position awareness
        if len(self.elite_keys) >= 2:
            try:
                parent1, parent2 = random.sample(self.elite_keys, 2)
                child = bytearray(32)
                active_bytes = self.hex_manager.current_active_bytes

                for byte_pos in range(active_bytes):
                    weight = self.hex_manager.position_weights[byte_pos]
                    # Higher weight positions more likely to be inherited
                    if random.random() < weight:
                        child[byte_pos] = parent1[byte_pos] if random.random() < 0.5 else parent2[byte_pos]
                    else:
                        child[byte_pos] = base_key[byte_pos]

                candidates.append(bytes(child))
            except Exception:
                pass

        # Fresh adaptive generation
        try:
            fresh_key = self.hex_manager.generate_adaptive_key()
            candidates.append(fresh_key)
        except Exception:
            pass

        return candidates if candidates else [base_key]

    def update_elite_pool(self):
        """Update elite pool - no diversity constraints but reject duplicate keys"""
        if not self.population:
            return

        # Get all individuals with valid scores
        scored_individuals = list(zip(self.scores, self.population))
        scored_individuals.sort(key=lambda x: x[0])

        selected_elite = []
        used_keys = set()  # Track used keys to prevent duplicates

        for score, key in scored_individuals:
            if score >= 160:
                continue

            # Reject duplicate keys but allow same scores
            key_bytes = bytes(key)
            if key_bytes in used_keys:
                continue

            selected_elite.append((score, key))
            used_keys.add(key_bytes)

            if len(selected_elite) >= self.config.ELITE_SIZE:
                break

        self.elite_scores = [score for score, _ in selected_elite]
        self.elite_keys = [key for _, key in selected_elite]

    def inject_diversity(self):
        """Inject fresh adaptive diversity"""
        if not self.population:
            return

        num_to_replace = max(1, int(len(self.population) * self.config.DIVERSITY_INJECTION_RATE))

        # Replace worst performers with fresh adaptive keys
        scored_individuals = list(zip(self.scores, range(len(self.population))))
        scored_individuals.sort(key=lambda x: x[0], reverse=True)  # Worst first

        fresh_count = 0
        for score, idx in scored_individuals[:num_to_replace]:
            try:
                fresh_key = self.hex_manager.generate_adaptive_key()
                fresh_score = self.score_key(fresh_key)

                self.population[idx] = fresh_key
                self.scores[idx] = fresh_score
                fresh_count += 1
            except Exception:
                continue

        if self.config.DETAILED_LOGGING:
            print(f"    💉 Injected {fresh_count} fresh adaptive keys")

    def run_optimization(self, target_hash_hex: str) -> dict:
        """Run adaptive hex GA optimization against target"""

        # Parse target
        try:
            self.target_hash = bytes.fromhex(target_hash_hex.replace('0x', ''))
            if len(self.target_hash) != 20:
                raise ValueError(f"Target hash must be 40 hex characters (20 bytes)")
        except Exception as e:
            return {'error': f"Invalid target hash: {e}"}

        print(f"\n🎯 TARGET: {target_hash_hex}")
        print(f"🚀 Starting adaptive hex optimization...")

        with self.atomics.start_time.get_lock():
            self.atomics.start_time.value = time.time()

        # Initialize population with adaptive hex generation
        print(f"🧬 Initializing population of {self.config.K_POOL}...")
        for i in range(self.config.K_POOL):
            try:
                key = self.hex_manager.generate_adaptive_key()
                score = self.score_key(key)
                self.population.append(key)
                self.scores.append(score)

                # Show first few keys
                if i < 5:
                    key_int = int.from_bytes(key, 'big')
                    print(f"  Key {i}: 0x{key_int:X} → score={score}")

            except Exception:
                continue

        # Show initial hex manager stats
        hex_stats = self.hex_manager.get_detailed_stats()
        print(f"🧠 Initial adaptive state:")
        print(f"   Active bytes: {hex_stats['current_active_bytes']}")
        print(f"   Max value: {hex_stats['max_value']}")
        print(f"   Active positions: {hex_stats['active_positions']}")

        self.update_elite_pool()
        initial_stats = self.atomics.atomic_get_all_stats()
        print(f"🎯 Initial best: {initial_stats['best_score']} bits")
        print(f"📊 Initial elite mean: {statistics.mean(self.elite_scores) if self.elite_scores else 160:.1f} bits")

        # Main optimization loop
        for round_num in range(self.config.MAX_ROUNDS):
            try:
                round_start_stats = self.atomics.atomic_get_all_stats()
                round_start_time = time.time()

                print(f"\n🔄 Round {round_num + 1}/{self.config.MAX_ROUNDS}")

                # Evolve population
                new_population = []
                new_scores = []
                learning_events = 0

                for i in range(len(self.population)):
                    try:
                        base_key = self.population[i]
                        candidates = self.evolve_individual(base_key)

                        best_candidate = base_key
                        best_score = self.scores[i]

                        for candidate in candidates:
                            try:
                                score = self.score_key(candidate)
                                if score < best_score:
                                    improvement = (best_score - score) / 160.0
                                    # Learn from successful mutations
                                    self.hex_manager.learn_from_mutation(base_key, candidate, improvement)
                                    learning_events += 1
                                    best_candidate = candidate
                                    best_score = score
                            except Exception:
                                continue

                        new_population.append(best_candidate)
                        new_scores.append(best_score)
                    except Exception:
                        continue

                self.population = new_population
                self.scores = new_scores

                # Update elite pool and analyze ranges
                self.update_elite_pool()
                self.hex_manager.analyze_population_ranges(self.population, self.scores)

                # Adaptive range adjustment
                self.hex_manager.adapt_active_range(round_num, self.elite_scores)

                # Apply global weight decay every round to prevent lock-in
                self.hex_manager.apply_global_weight_decay()

                # Round statistics
                round_end_stats = self.atomics.atomic_get_all_stats()
                round_time = time.time() - round_start_time

                improved = round_end_stats['best_score'] < round_start_stats['best_score']
                if improved:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_DECAY)
                elif round_num % 5 == 0:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_INCREASE)

                # Show round results
                elite_mean = statistics.mean(self.elite_scores) if self.elite_scores else 160
                print(f"   Best: {round_end_stats['best_score']} bits (global)")
                print(f"   Elite: {elite_mean:.1f} bits avg ({len(self.elite_scores)} individuals)")
                print(f"   Learning events: {learning_events}")
                print(f"   Round time: {round_time:.1f}s")

                # Show adaptive hex stats every few rounds
                if round_num % 5 == 0 or improved:
                    hex_stats = self.hex_manager.get_detailed_stats()
                    print(f"   🧠 Adaptive state: {hex_stats['current_active_bytes']} bytes, "
                          f"{hex_stats['active_positions']} active positions")

                    if hex_stats['top_positions']:
                        print("   🧠 Top positions:", end="")
                        for pos_info in hex_stats['top_positions'][:3]:
                            print(f" pos{pos_info['position']}({pos_info['weight']:.2f})", end="")
                        print()

                # Show elite analysis every 10 rounds
                if round_num % 10 == 0:
                    print(f"\n🔬 ELITE ANALYSIS - Round {round_num}")
                    if self.elite_keys:
                        elite_data = []
                        for i, key in enumerate(self.elite_keys[:20]):
                            key_int = int.from_bytes(key, 'big')
                            try:
                                hash160 = self.crypto.private_key_to_hash160(key)
                                hamming_dist = hamming_distance_160(hash160, self.target_hash)
                                elite_data.append((i+1, key_int, hamming_dist))
                            except:
                                elite_data.append((i+1, key_int, 160))

                        print(f"   Top 20 Elite Keys:")
                        for rank, key_int, hamming_dist in elite_data[:10]:  # Show top 10
                            print(f"     #{rank}: 0x{key_int:X} (hamming: {hamming_dist} bits)")

                        key_sizes = [key_int.bit_length() for _, key_int, _ in elite_data]
                        hamming_scores = [hamming_dist for _, _, hamming_dist in elite_data]
                        print(f"   Key sizes (bits): min={min(key_sizes)}, max={max(key_sizes)}, avg={statistics.mean(key_sizes):.1f}")
                        print(f"   Hamming scores: min={min(hamming_scores)}, max={max(hamming_scores)}, avg={statistics.mean(hamming_scores):.1f}")

                # Diversity injection on stagnation
                if round_num % 8 == 0:
                    self.inject_diversity()

                # Heavy weight reset if locked in (no improvements for many rounds)
                if round_num % 20 == 0 and round_end_stats['best_score'] == round_start_stats['best_score']:
                    print(f"    🔄 Weight reset - no improvement for 20 rounds")
                    self.hex_manager.reset_position_weights()

                # Early termination for excellent results
                if round_end_stats['best_score'] <= 30:
                    print(f"\n🎉 EXCELLENT RESULT! Terminating early at round {round_num + 1}")
                    break

            except Exception as e:
                print(f"   ❌ Round {round_num + 1} error: {e}")
                continue

        # Collect final results
        try:
            with self.atomics.start_time.get_lock():
                total_time = time.time() - self.atomics.start_time.value

            final_stats = self.atomics.atomic_get_all_stats()
            final_hex_stats = self.hex_manager.get_detailed_stats()
            best_key = self.atomics.get_best_key()
            best_key_int = int.from_bytes(best_key, 'big')

            return {
                'target_hash': target_hash_hex,
                'best_score': final_stats['best_score'],
                'best_key_hex': best_key.hex(),
                'best_key_int': f"0x{best_key_int:X}",
                'total_evaluations': final_stats['evaluations'],
                'improvements': final_stats['improvements'],
                'total_time': total_time,
                'elite_mean': statistics.mean(self.elite_scores) if self.elite_scores else 160,
                'elite_count': len(self.elite_scores),
                'final_hex_stats': final_hex_stats,
                'rounds_completed': min(round_num + 1, self.config.MAX_ROUNDS),
                'evals_per_second': final_stats['evaluations'] / total_time if total_time > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}

def print_final_analysis(results: dict):
    """Print comprehensive analysis of results"""
    print("\n" + "="*100)
    print("🔬 ADAPTIVE HEX-AWARE GA ANALYSIS")
    print("="*100)

    if 'error' in results:
        print(f"❌ Analysis failed: {results['error']}")
        return

    print(f"🎯 Target:            {results['target_hash']}")
    print(f"🏆 Best Score:        {results['best_score']} bits")
    print(f"🔑 Best Key:          {results['best_key_int']}")
    print(f"⚡ Total Evals:       {results['total_evaluations']:,}")
    print(f"📈 Improvements:      {results['improvements']}")
    print(f"⏱️  Total Time:        {results['total_time']:.1f} seconds")
    print(f"🚀 Speed:             {results['evals_per_second']:,.0f} evals/second")
    print(f"🧬 Elite Mean:        {results['elite_mean']:.1f} bits ({results['elite_count']} individuals)")
    print(f"🔄 Rounds:            {results['rounds_completed']}")

    if 'final_hex_stats' in results:
        hex_stats = results['final_hex_stats']
        print(f"\n🧠 ADAPTIVE HEX LEARNING RESULTS:")
        print(f"   Final Active Bytes:     {hex_stats['current_active_bytes']}")
        print(f"   Final Max Value:        {hex_stats['max_value']}")
        print(f"   Active Positions:       {hex_stats['active_positions']}")
        print(f"   Highly Active Pos:      {hex_stats['highly_active_positions']}")
        print(f"   Avg Position Weight:    {hex_stats['avg_position_weight']:.3f}")
        print(f"   Total Learning Events:  {hex_stats['learning_events']}")

        if hex_stats['top_positions']:
            print(f"   🏆 Top Learned Positions:")
            for i, pos_info in enumerate(hex_stats['top_positions']):
                print(f"      #{i+1}: Position {pos_info['position']} "
                      f"(weight: {pos_info['weight']:.3f}, "
                      f"usage: {pos_info['usage_count']:.0f})")

        if hex_stats['range_performance_summary']:
            print(f"   📊 Range Performance:")
            for byte_range, avg_perf in sorted(hex_stats['range_performance_summary'].items()):
                print(f"      {byte_range} bytes: {avg_perf:.1f} avg improvement")

    # Performance analysis
    improvement_over_random = 80.0 - results['best_score']
    print(f"\n🔬 PERFORMANCE ANALYSIS:")
    print(f"   vs Random Baseline:     {improvement_over_random:.1f} bits better")

    if improvement_over_random > 15:
        print("   🚨 MAJOR PATTERN DETECTED - Significant algorithmic advantage!")
    elif improvement_over_random > 10:
        print("   ⚠️  STRONG PATTERN - Notable improvement over random search")
    elif improvement_over_random > 5:
        print("   📊 MODERATE PATTERN - Some improvement over random")
    else:
        print("   ✅ Results consistent with statistical noise")

    # Efficiency analysis
    if 'final_hex_stats' in results and results['final_hex_stats']['current_active_bytes'] <= 4:
        print(f"   🧠 EXCELLENT EFFICIENCY - Learned to use only "
              f"{results['final_hex_stats']['current_active_bytes']} bytes")

    print("="*100)

def run_single_target_test():
    """Run the single target test"""
    # Validate target
    if not TARGET_HASH160 or len(TARGET_HASH160.replace('0x', '')) != 40:
        print("❌ Please set a valid 40-character hex TARGET_HASH160 at the top of the script")
        return

    config = SingleTargetConfig()
    engine = SingleTargetEngine(config)

    print(f"🔥 SINGLE TARGET ADAPTIVE HEX TEST - NO DIVERSITY")
    print(f"🎯 Target: {TARGET_HASH160}")

    results = engine.run_optimization(TARGET_HASH160)
    print_final_analysis(results)

    return results

# Main execution
if __name__ == "__main__":
    print("🔥 SINGLE TARGET ADAPTIVE HEX-AWARE GA - NO DIVERSITY")
    print("="*70)
    print("🧠 Tests one hash160 target with detailed adaptive learning analysis")
    print("🧠 GA learns which hex positions matter and optimal byte ranges")
    print("🔬 NO DIVERSITY CONSTRAINTS - Pure performance focus")
    print("🔧 CHANGE TARGET_HASH160 variable at top of script to your target")
    print("="*70)

    # Run the test
    run_single_target_test()
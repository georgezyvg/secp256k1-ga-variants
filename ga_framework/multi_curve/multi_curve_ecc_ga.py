#!/usr/bin/env python3
"""
Multi-Curve ECC GA Test - Tests GA performance across different elliptic curves
Tests if GA shows similar patterns across curves (potential systematic ECC property)
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
    
    # Always try to get coincurve for secp256k1
    HAS_COINCURVE = False
    try:
        import coincurve
        HAS_COINCURVE = True
        print("✅ Using fast coincurve for secp256k1")
    except ImportError:
        print("⚠️ coincurve not found, will use ecdsa for secp256k1")
    
    # Try to get nacl for Curve25519
    HAS_CURVE25519 = False
    try:
        import nacl.bindings
        HAS_CURVE25519 = True
        print("✅ Using PyNaCl for Curve25519")
    except ImportError:
        try:
            # Alternative: try cryptography library
            from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
            HAS_CURVE25519 = True
            print("✅ Using cryptography for Curve25519")
        except ImportError:
            print("⚠️ Curve25519 not available - install pynacl or cryptography")
    
    # Always need ecdsa for other curves
    from ecdsa import SECP256k1, NIST256p, NIST384p, NIST521p, SigningKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os

except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    
    # Try to install coincurve for speed on secp256k1
    HAS_COINCURVE = False
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "coincurve"])
        import coincurve
        HAS_COINCURVE = True
        print("✅ Installed coincurve for fast secp256k1")
    except:
        print("⚠️ Could not install coincurve")
    
    # Try to install PyNaCl for Curve25519
    HAS_CURVE25519 = False
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynacl"])
        import nacl.bindings
        HAS_CURVE25519 = True
        print("✅ Installed PyNaCl for Curve25519")
    except:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
            from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
            HAS_CURVE25519 = True
            print("✅ Installed cryptography for Curve25519")
        except:
            print("⚠️ Could not install Curve25519 support")
    
    # Always install ecdsa for other curves
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "ecdsa", "pycryptodome"])
    
    import numpy as np
    from ecdsa import SECP256k1, NIST256p, NIST384p, NIST521p, SigningKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os

print(f"✅ Ready to test all curves")

# Curve25519 dummy class for consistency
class Curve25519:
    """Dummy class to hold Curve25519 parameters"""
    order = 0x1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed
    
    class curve:
        @staticmethod
        def p():
            return 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffed

# Build curve list based on what's available
CURVES_TO_TEST = [
    ('secp256k1', SECP256k1),      # Bitcoin curve - will use coincurve if available
    ('nist256p', NIST256p),        # NIST P-256
    ('nist384p', NIST384p),        # NIST P-384
    ('nist521p', NIST521p),        # NIST P-521
]

# Add Curve25519 if available
if HAS_CURVE25519:
    CURVES_TO_TEST.append(('curve25519', Curve25519))
    print("✅ Curve25519 added to test suite")
else:
    print("⚠️ Curve25519 not available - install py_ecc to test it")

# Curve specifications
CURVE_KEY_SIZES = {
    'secp256k1': 32,  # 256 bits
    'nist256p': 32,   # 256 bits
    'nist384p': 48,   # 384 bits
    'nist521p': 66,   # 521 bits (rounded up to 66 bytes)
    'curve25519': 32, # 256 bits
}

@dataclass
class SingleTargetConfig:
    """Configuration for single target adaptive hex GA - NO DIVERSITY CONSTRAINTS"""
    K_POOL: int = 8000                    # Population size
    ELITE_SIZE: int = 400                 # Elite pool size
    
    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MUTATION_INCREASE: float = 1.3
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 1.2
    
    STAGNATION_ROUNDS: int = 4
    DIVERSITY_INJECTION_RATE: float = 0.4  # For breaking local optima
    
    # Adaptive hex learning parameters - UNCONSTRAINED
    INITIAL_ACTIVE_BYTES: int = 1         # Start with 1 active byte
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
    MAX_ROUNDS: int = 20                  # ONLY 20 rounds per curve test
    DETAILED_LOGGING: bool = False        # Less verbose for multi-curve

class AdaptiveHexManager:
    """Manages adaptive hex range expansion/contraction and position learning"""
    
    def __init__(self, config: SingleTargetConfig, key_size: int):
        self.config = config
        self.key_size = key_size  # Total key size in bytes for this curve
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.max_active_bytes = key_size  # Adapt to curve's key size
        
        # Position importance weights (learned adaptively)
        self.position_weights = np.ones(key_size, dtype=np.float32)
        self.position_usage_stats = np.zeros(key_size, dtype=np.float32)
        self.position_performance = np.zeros(key_size, dtype=np.float32)
        
        # Range performance tracking
        self.range_performance = {}  # byte_range -> [improvements]
        self.generation_count = 0
        
        # Learning history for analysis
        self.learning_history = []
        
        self.lock = threading.RLock()
        
        print(f"   🧠 Adaptive Hex Manager initialized for {key_size}-byte keys")
    
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
            # For larger byte ranges, calculate based on curve's max key size
            max_bits = min(self.current_active_bytes * 8, self.key_size * 8)
            return (2 ** max_bits) - 1
    
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
            
            return key_value.to_bytes(self.key_size, 'big')
    
    def _generate_position_focused_key(self, max_value: int) -> int:
        """Generate key focusing on learned positions - UNBIASED WITHIN RANGE"""
        key_bytes = [0] * self.key_size
        
        # Fill bytes based on position weights - BUT USE FULL RANGE
        for byte_pos in range(min(self.current_active_bytes, self.key_size)):
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
            for byte_pos in range(min(self.current_active_bytes, self.key_size)):
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
            for byte_pos in range(self.key_size):
                if byte_pos >= self.current_active_bytes:
                    self.position_weights[byte_pos] *= self.config.POSITION_DECAY
                    self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                        self.position_weights[byte_pos])
    
    def apply_global_weight_decay(self):
        """Apply heavy weight decay per round to prevent lock-in"""
        with self.lock:
            for byte_pos in range(self.key_size):
                # Apply global decay to all positions
                self.position_weights[byte_pos] *= self.config.GLOBAL_WEIGHT_DECAY
                # Ensure minimum weight
                self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                    self.position_weights[byte_pos])
    
    def reset_position_weights(self):
        """Reset position weights when locked in local optimum"""
        with self.lock:
            # Reset to moderate values instead of 1.0 to encourage exploration
            self.position_weights = np.full(self.key_size, 0.3, dtype=np.float32)
    
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
                
                effective_bytes = max(1, min(effective_bytes, self.key_size))
                
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
                    self.current_active_bytes < self.max_active_bytes):
                    self.current_active_bytes = min(self.current_active_bytes + 1,
                                                  self.max_active_bytes)
                
                elif (best_smaller_perf > current_avg_perf and 
                      best_smaller_perf > best_larger_perf and
                      self.current_active_bytes > 1):
                    self.current_active_bytes = max(1, self.current_active_bytes - 1)
    
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
    def __init__(self, config: SingleTargetConfig, key_size: int):
        self.config = config
        self.key_size = key_size
        self.global_best_score = Value('i', 160, lock=True)
        self.global_improvements = Value('L', 0, lock=True)
        self.global_evaluations = Value('L', 0, lock=True)
        self.best_key_bytes = Array('B', key_size, lock=True)  # Adapt to key size
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
                    for i, byte_val in enumerate(new_key[:self.key_size]):
                        self.best_key_bytes[i] = byte_val
                return True
        return False
    
    def get_best_key(self) -> bytes:
        with self.best_key_bytes.get_lock():
            return bytes(self.best_key_bytes[:self.key_size])
    
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

class MultiCurveCryptoOps:
    """Crypto operations supporting multiple curves"""
    def __init__(self, curve, curve_name):
        self.curve = curve
        self.curve_name = curve_name
        self.key_size = CURVE_KEY_SIZES[curve_name]
        # Use coincurve for secp256k1 if available
        self.use_coincurve = (curve_name == 'secp256k1' and HAS_COINCURVE)
        # Use py_ecc for curve25519 if available
        self.use_curve25519 = (curve_name == 'curve25519' and HAS_CURVE25519)
        
    def scalar_mult_curve(self, private_key: bytes) -> bytes:
        if len(private_key) != self.key_size:
            raise ValueError(f"Private key must be {self.key_size} bytes for {self.curve_name}")
        
        try:
            if self.use_coincurve:
                # coincurve is MUCH faster for secp256k1
                privkey = coincurve.PrivateKey(private_key)
                return privkey.public_key.format(compressed=True)
            elif self.use_curve25519:
                # Curve25519 scalar multiplication
                priv_int = int.from_bytes(private_key, 'big')
                
                # Clamp the private key according to Curve25519 spec
                # Clear bits 0, 1, 2 of first byte and bit 7 of last byte
                # Set bit 6 of last byte
                clamped_key = bytearray(private_key)
                clamped_key[0] &= 248  # Clear bits 0,1,2
                clamped_key[31] &= 127  # Clear bit 7
                clamped_key[31] |= 64   # Set bit 6
                
                try:
                    # Try PyNaCl first
                    import nacl.bindings
                    # PyNaCl expects little-endian
                    scalar = bytes(clamped_key[::-1])  # Convert to little-endian
                    public_key = nacl.bindings.crypto_scalarmult_base(scalar)
                    # Return in compressed format (prefix + x-coordinate)
                    return b'\x02' + public_key[::-1]  # Convert back to big-endian
                except:
                    # Try cryptography library
                    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
                    from cryptography.hazmat.backends import default_backend
                    private = X25519PrivateKey.from_private_bytes(bytes(clamped_key))
                    public = private.public_key()
                    public_bytes = public.public_bytes_raw()
                    return b'\x02' + public_bytes
            else:
                # ecdsa for all other curves
                priv_int = int.from_bytes(private_key, 'big')
                if priv_int == 0 or priv_int >= self.curve.order:
                    priv_int = priv_int % (self.curve.order - 1) + 1
                    private_key = priv_int.to_bytes(self.key_size, 'big')
                
                sk = SigningKey.from_string(private_key, curve=self.curve)
                vk = sk.verifying_key
                point = vk.pubkey.point
                
                x = point.x()
                y = point.y()
                prefix = 0x02 if (y % 2 == 0) else 0x03
                # Handle different bit lengths for different curves
                byte_length = (self.curve.order.bit_length() + 7) // 8
                x_bytes = x.to_bytes(byte_length, 'big')
                return bytes([prefix]) + x_bytes
        except Exception as e:
            # Return a valid dummy compressed pubkey
            if self.curve_name == 'curve25519':
                return b'\x02' + b'\x00' * 32
            else:
                return b'\x02' + b'\x00' * ((self.curve.order.bit_length() + 7) // 8)
    
    def hash160(self, data: bytes) -> bytes:
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()
    
    def private_key_to_hash160(self, private_key: bytes) -> bytes:
        pubkey = self.scalar_mult_curve(private_key)
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
    if len(key1) != len(key2):
        return 0.0
    return float(sum(a != b for a, b in zip(key1, key2)))

def enhanced_fitness(hash160: bytes, target_hash: bytes) -> float:
    """Enhanced fitness with hex match weighting"""
    hd = hamming_distance_160(hash160, target_hash)
    hex_matches = sum(a == b for a, b in zip(hash160.hex(), target_hash.hex()))
    return hd - (hex_matches * 0.1)

def calculate_private_key_distance(found_key: bytes, true_key: bytes) -> Tuple[int, float]:
    """Calculate bit distance between found and true private keys"""
    if len(found_key) != len(true_key):
        return len(true_key) * 8, float('inf')
    
    # Calculate Hamming distance in bits
    distance_bits = 0
    for i in range(len(found_key)):
        xor_byte = found_key[i] ^ true_key[i]
        distance_bits += bin(xor_byte).count('1')
    
    # The distance represents how many bits need to be flipped
    # So we need to search 2^distance_bits possibilities to hit the true key
    return distance_bits, distance_bits


def apply_key_variants(private_key: bytes, curve_order: int, field_prime: int) -> Dict[str, bytes]:
    """Apply various mathematical transformations to test for patterns"""
    key_int = int.from_bytes(private_key, 'big')
    key_size = len(private_key)
    variants = {}
    
    # Original key
    variants['original'] = private_key
    
    # 1. Mirror: (n - k) mod n
    mirrored_int = (curve_order - key_int) % curve_order
    variants['mirror_n-k'] = mirrored_int.to_bytes(key_size, 'big')
    
    # 2. Multiplicative inverse: (1/k) mod n
    try:
        # Extended GCD for modular inverse
        def modinv(a, m):
            g, x, _ = extended_gcd(a, m)
            if g != 1:
                return None
            return x % m
        
        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1
            return gcd, x, y
        
        inv = modinv(key_int, curve_order)
        if inv:
            variants['inverse_1/k'] = inv.to_bytes(key_size, 'big')
            
            # 2a. Non-unit scalar inverse: (1/(2k)) mod n
            two_k = (2 * key_int) % curve_order
            if two_k != 0:
                inv_2k = modinv(two_k, curve_order)
                if inv_2k:
                    variants['inverse_1/2k'] = inv_2k.to_bytes(key_size, 'big')
            
            # 2b. Fractional harmonic: (0.5/k) mod n = (1/(2k)) mod n
            # This is same as above but conceptually different
            
            # 2c. Try (2/k) mod n for additional harmonic
            two_inv = modinv(key_int, curve_order)
            if two_inv:
                two_over_k = (2 * two_inv) % curve_order
                variants['2/k'] = two_over_k.to_bytes(key_size, 'big')
    except:
        pass
    
    # 3. XOR with common patterns
    patterns = [
        (0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, 'xor_all_ff'),
        (0x5555555555555555555555555555555555555555555555555555555555555555, 'xor_alternating'),
        (0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA, 'xor_alternating2'),
    ]
    
    for pattern_val, pattern_name in patterns:
        # Adjust pattern to key size
        pattern_mask = pattern_val & ((1 << (key_size * 8)) - 1)
        xor_result = key_int ^ pattern_mask
        if xor_result < curve_order:
            variants[pattern_name] = xor_result.to_bytes(key_size, 'big')
    
    # 4. Bit shifts
    if key_int << 1 < curve_order:
        variants['shift_left_1'] = (key_int << 1).to_bytes(key_size, 'big')
    if key_int >> 1 > 0:
        variants['shift_right_1'] = (key_int >> 1).to_bytes(key_size, 'big')
    
    # 5. Byte reversal
    variants['byte_reversed'] = private_key[::-1]
    
    # 6. Endianness swap (for multi-byte chunks)
    # Swap as 4-byte chunks (32-bit endian swap)
    if key_size >= 4:
        swapped = bytearray()
        for i in range(0, key_size, 4):
            chunk = private_key[i:i+4]
            if len(chunk) == 4:
                swapped.extend(chunk[::-1])
            else:
                swapped.extend(chunk)
        if int.from_bytes(bytes(swapped), 'big') < curve_order:
            variants['endian_swap_32'] = bytes(swapped)
    
    # 7. Modulo p folding (if different from n)
    if field_prime != curve_order:
        folded = key_int % field_prime
        if folded < curve_order and folded > 0:
            variants['mod_p_fold'] = folded.to_bytes(key_size, 'big')
    
    # 8. Complement operations
    complement = curve_order - key_int - 1
    if complement > 0:
        variants['complement'] = complement.to_bytes(key_size, 'big')
    
    # 9. Rotation operations
    # Rotate left by 1 byte
    if key_size > 1:
        rotated_left = private_key[1:] + private_key[:1]
        if int.from_bytes(rotated_left, 'big') < curve_order:
            variants['rotate_left_byte'] = rotated_left
    
    # 10. Additive patterns
    additive_patterns = [
        (1, 'add_1'),
        (-1, 'sub_1'),
        (curve_order // 2, 'add_half_n'),
    ]
    
    for delta, name in additive_patterns:
        result = (key_int + delta) % curve_order
        if result > 0 and result < curve_order:
            variants[name] = result.to_bytes(key_size, 'big')
    
    # 11. Double modulo folding: (k mod p) mod q
    # Use a safe prime q (example: 2^127 - 1, a Mersenne prime)
    safe_prime_q = (1 << 127) - 1  # 2^127 - 1
    if field_prime != curve_order:
        double_fold = (key_int % field_prime) % safe_prime_q
        if double_fold > 0 and double_fold < curve_order:
            try:
                variants['mod_p_mod_q'] = double_fold.to_bytes(key_size, 'big')
            except:
                pass
    
    # 12. Scalar-normalized field projections
    # k ÷ p (as ratio in field)
    if field_prime != curve_order and key_int < field_prime:
        # Represent as k/p * n to stay in scalar field
        k_div_p_scaled = (key_int * curve_order) // field_prime
        if k_div_p_scaled > 0 and k_div_p_scaled < curve_order:
            try:
                variants['k_div_p_scaled'] = k_div_p_scaled.to_bytes(key_size, 'big')
            except:
                pass
    
    # k ÷ n (as ratio, then scaled back)
    k_div_n_scaled = (key_int * field_prime) // curve_order
    if k_div_n_scaled > 0 and k_div_n_scaled < curve_order:
        try:
            variants['k_div_n_scaled'] = k_div_n_scaled.to_bytes(key_size, 'big')
        except:
            pass
    
    # 13. Galois trace (simplified for binary field behavior)
    # trace_GF(k) = k + k^2 + k^4 + k^8 + ... (mod n)
    # This is meaningful if treating scalar field as having GF(2^m) structure
    trace = key_int
    temp = key_int
    for _ in range(min(8, key_size * 8)):  # Limit iterations
        temp = (temp * temp) % curve_order
        trace = (trace + temp) % curve_order
        if temp == key_int:  # Cycle detected
            break
    
    if trace > 0 and trace < curve_order and trace != key_int:
        try:
            variants['trace_gf'] = trace.to_bytes(key_size, 'big')
        except:
            pass
    
    # 14. Square root variants (if they exist in the field)
    # Check if k is a quadratic residue
    # For prime fields, use Tonelli-Shanks or similar
    # Simplified: just check if k^((n-1)/2) ≡ 1 (mod n)
    if pow(key_int, (curve_order - 1) // 2, curve_order) == 1:
        # k is a quadratic residue, but finding sqrt is complex
        # For now, try simple case where sqrt might be obvious
        sqrt_candidate = pow(key_int, (curve_order + 1) // 4, curve_order)
        if (sqrt_candidate * sqrt_candidate) % curve_order == key_int:
            variants['sqrt_k'] = sqrt_candidate.to_bytes(key_size, 'big')
    
    # 15. Harmonic series: k/3, k/5, k/7 (for small primes)
    small_primes = [3, 5, 7, 11, 13]
    for prime in small_primes:
        if key_int % prime == 0:
            divided = key_int // prime
            if divided > 0 and divided < curve_order:
                variants[f'k_div_{prime}'] = divided.to_bytes(key_size, 'big')
    
    # 16. Fibonacci-like transforms
    # k' = (k + k>>1) mod n - creates Fibonacci-like mixing
    fib_like = (key_int + (key_int >> 1)) % curve_order
    if fib_like > 0:
        variants['fibonacci_mix'] = fib_like.to_bytes(key_size, 'big')
    
    # 17. Additional XOR patterns for more coverage
    additional_xor_patterns = [
        (0x0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F, 'xor_0f0f'),
        (0xF0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0, 'xor_f0f0'),
        (0x3333333333333333333333333333333333333333333333333333333333333333, 'xor_3333'),
        (0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC, 'xor_cccc'),
    ]
    
    for pattern_val, pattern_name in additional_xor_patterns:
        pattern_mask = pattern_val & ((1 << (key_size * 8)) - 1)
        xor_result = key_int ^ pattern_mask
        if xor_result < curve_order:
            variants[pattern_name] = xor_result.to_bytes(key_size, 'big')
    
    # 18. Gradient edge variants (±1, ±2, ±4 from key)
    gradient_deltas = [1, 2, 4, 8, 16, 32, 64, 128, 256]
    for delta in gradient_deltas:
        # Add delta
        result_add = (key_int + delta) % curve_order
        if result_add > 0:
            variants[f'gradient_add_{delta}'] = result_add.to_bytes(key_size, 'big')
        
        # Subtract delta
        result_sub = (key_int - delta) % curve_order
        if result_sub > 0:
            variants[f'gradient_sub_{delta}'] = result_sub.to_bytes(key_size, 'big')
    
    # 19. Rational/fractional inverses (simulated as (1/nk) for various n)
    rational_multipliers = [3, 4, 5, 6, 7, 8]
    for n in rational_multipliers:
        nk = (n * key_int) % curve_order
        if nk != 0:
            try:
                inv_nk = modinv(nk, curve_order)
                if inv_nk:
                    variants[f'inverse_1/{n}k'] = inv_nk.to_bytes(key_size, 'big')
            except:
                pass
    
    # 20. Bit rotation variants (rotate by different amounts)
    bit_rotations = [1, 2, 4, 8, 16]
    for rot in bit_rotations:
        if rot < key_size * 8:
            # Left rotation
            rotated = ((key_int << rot) | (key_int >> (key_size * 8 - rot))) & ((1 << (key_size * 8)) - 1)
            if rotated < curve_order:
                variants[f'rotate_left_{rot}bit'] = rotated.to_bytes(key_size, 'big')
            
            # Right rotation
            rotated = ((key_int >> rot) | (key_int << (key_size * 8 - rot))) & ((1 << (key_size * 8)) - 1)
            if rotated < curve_order:
                variants[f'rotate_right_{rot}bit'] = rotated.to_bytes(key_size, 'big')
    
    return variants


def find_dual_ec_scalar(k1: bytes, k2: bytes, curve_order: int, max_d: int = 2**24) -> int:
    """Try to find a small d such that k2 = d * k1 mod n or k1 = d * k2 mod n."""
    i1 = int.from_bytes(k1, 'big')
    i2 = int.from_bytes(k2, 'big')
    for d in range(1, max_d):
        if (i2 - d * i1) % curve_order == 0:
            return d
        if (i1 - d * i2) % curve_order == 0:
            return -d
    return None

def analyze_curve_results_with_true_key(results: dict, true_private_key: bytes, elite_keys: List[bytes], curve_order: int, field_prime: int) -> dict:
    """Analyze how close the GA got to the true private key, including all variants"""
    analysis = {
        'true_key_hex': true_private_key.hex(),
        'true_key_int': int.from_bytes(true_private_key, 'big'),
        'best_found_analysis': {},
        'top_10_analysis': [],
        'curve_order': curve_order,
        'variant_analysis': {}
    }
    
    # Analyze best found key
    best_key = bytes.fromhex(results['best_key_hex'])
    best_distance_bits, _ = calculate_private_key_distance(best_key, true_private_key)
    
    analysis['best_found_analysis'] = {
        'key_hex': results['best_key_hex'],
        'key_int': int.from_bytes(best_key, 'big'),
        'hamming_distance_bits': best_distance_bits,
        'power_to_true_key': f"2^{best_distance_bits}",
        'exact_match': best_distance_bits == 0
    }
    
    # Track the overall closest (including all variants)
    closest_distance = best_distance_bits
    closest_key = best_key
    closest_source = "best_key"
    closest_variant = "original"
    
    # Collect all keys to test (best + elite)
    all_keys_to_test = [('best', best_key)] + [(f'elite_{i+1}', key) for i, key in enumerate(elite_keys[:10])]
    
    # Test all variants for all keys
    variant_stats = {}
    for key_source, test_key in all_keys_to_test:
        # Get all variants of this key
        variants = apply_key_variants(test_key, curve_order, field_prime)
        
        for variant_name, variant_key in variants.items():
            distance_bits, _ = calculate_private_key_distance(variant_key, true_private_key)
            
            # Track statistics for each variant type
            if variant_name not in variant_stats:
                variant_stats[variant_name] = {
                    'total_tested': 0,
                    'best_distance': float('inf'),
                    'times_best': 0,
                    'average_distance': 0,
                    'distances': []
                }
            
            variant_stats[variant_name]['total_tested'] += 1
            variant_stats[variant_name]['distances'].append(distance_bits)
            
            if distance_bits < variant_stats[variant_name]['best_distance']:
                variant_stats[variant_name]['best_distance'] = distance_bits
            
            # Check if this is the closest overall
            if distance_bits < closest_distance:
                closest_distance = distance_bits
                closest_key = variant_key
                closest_source = key_source
                closest_variant = variant_name
                
                # Track which variant types are best
                variant_stats[variant_name]['times_best'] += 1
    
    # Calculate averages and create variant table
    variant_table = []
    for variant_name, stats in variant_stats.items():
        if stats['distances']:
            avg_distance = sum(stats['distances']) / len(stats['distances'])
            stats['average_distance'] = avg_distance
            
            variant_table.append({
                'variant': variant_name,
                'description': get_variant_description(variant_name),
                'best_distance': stats['best_distance'],
                'avg_distance': avg_distance,
                'times_best': stats['times_best']
            })
    
    # Sort variant table by best distance
    variant_table.sort(key=lambda x: x['best_distance'])
    
    # Add analysis results
    analysis['closest_found'] = {
        'key_hex': closest_key.hex(),
        'key_int': int.from_bytes(closest_key, 'big'),
        'hamming_distance_bits': closest_distance,
        'power_to_reach_true_key': f"2^{closest_distance}",
        'source': closest_source,
        'variant_type': closest_variant,
        'key_size_bits': len(true_private_key) * 8,
        'correct_bits': len(true_private_key) * 8 - closest_distance,
        'percentage_correct': ((len(true_private_key) * 8 - closest_distance) / (len(true_private_key) * 8)) * 100
    }
    
    analysis['variant_analysis'] = {
        'variant_table': variant_table,
        'best_variant': closest_variant,
        'total_variants_tested': len(variant_stats),
        'total_keys_tested': len(all_keys_to_test) * len(variant_stats)
    }
    
    # Add top 10 analysis (simplified)
    for i, elite_key in enumerate(elite_keys[:10]):
        distance_bits, _ = calculate_private_key_distance(elite_key, true_private_key)
        
        elite_analysis = {
            'rank': i + 1,
            'key_hex': elite_key.hex(),
            'key_int': int.from_bytes(elite_key, 'big'),
            'hamming_distance_bits': distance_bits,
            'power_to_true_key': f"2^{distance_bits}",
            'exact_match': distance_bits == 0
        }
        # Dual EC DRBG-like scalar check
        d = find_dual_ec_scalar(elite_key, true_private_key, curve_order)
        if d is not None:
            elite_analysis['dual_ec_scalar'] = d
        analysis['top_10_analysis'].append(elite_analysis)
    
    # Thorough check: all elite keys vs true key
    analysis['dual_ec_scalar_findings'] = []
    for idx, elite in enumerate(elite_keys):
        d = find_dual_ec_scalar(elite, true_private_key, curve_order)
        if d is not None:
            analysis['dual_ec_scalar_findings'].append({
                'elite_index': idx + 1,
                'elite_key_hex': elite.hex(),
                'scalar_d': d
            })
    return analysis

class SingleTargetEngine:
    """Single target adaptive hex-aware GA engine"""
    
    def __init__(self, config: SingleTargetConfig, curve_name: str, curve):
        self.config = config
        self.curve_name = curve_name
        self.curve = curve
        self.key_size = CURVE_KEY_SIZES[curve_name]
        self.crypto = MultiCurveCryptoOps(curve, curve_name)
        self.hex_manager = AdaptiveHexManager(config, self.key_size)
        self.atomics = SingleTargetAtomics(config, self.key_size)
        
        # Population storage
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.elite_scores = []
        
        self.target_hash = None
    
    def score_key(self, private_key: bytes) -> int:
        try:
            self.atomics.atomic_increment_evals(1)
            hash160 = self.crypto.private_key_to_hash160(private_key)
            distance = enhanced_fitness(hash160, self.target_hash)
            distance_int = int(round(distance))
            improved = self.atomics.try_update_global_best(distance_int, private_key)
            
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
            for byte_pos in range(min(active_bytes, self.key_size)):
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
            
            mutations.append(bytes(key_bytes[:self.key_size]))
            
            # Integer-level mutations in FULL active range
            for i in range(4):  # More mutations
                if random.random() < strength:
                    # Scale delta by current range - MUCH LARGER DELTAS
                    delta_range = max(1000, int(max_range * strength * 0.1))  # 10% of range
                    delta = random.randint(-delta_range, delta_range)
                    new_int = max(1, min(key_int + delta, max_range))
                    mutations.append(new_int.to_bytes(self.key_size, 'big'))
            
            # Bit flips across FULL active range
            if random.random() < strength:
                max_bit = min(self.key_size * 8 - 1, active_bytes * 8 - 1)
                # Try multiple bit flips
                for _ in range(random.randint(1, 3)):
                    bit_pos = random.randint(0, max_bit)
                    new_int = key_int ^ (1 << bit_pos)
                    new_int = max(1, min(new_int, max_range))
                    mutations.append(new_int.to_bytes(self.key_size, 'big'))
            
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
                    mutations.append(new_int.to_bytes(self.key_size, 'big'))
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
                child = bytearray(self.key_size)
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
        """Update elite pool - NO DIVERSITY CONSTRAINTS but reject duplicate keys"""
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
        """Inject fresh adaptive diversity to break local optima"""
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
    
    def run_optimization(self, target_hash_hex: str) -> dict:
        """Run adaptive hex GA optimization against target"""
        
        # Parse target
        try:
            self.target_hash = bytes.fromhex(target_hash_hex.replace('0x', ''))
            if len(self.target_hash) != 20:
                raise ValueError(f"Target hash must be 40 hex characters (20 bytes)")
        except Exception as e:
            return {'error': f"Invalid target hash: {e}"}
        
        with self.atomics.start_time.get_lock():
            self.atomics.start_time.value = time.time()
        
        # Initialize population with adaptive hex generation
        print(f"   Initializing {self.config.K_POOL} keys...")
        for i in range(self.config.K_POOL):
            try:
                key = self.hex_manager.generate_adaptive_key()
                score = self.score_key(key)
                self.population.append(key)
                self.scores.append(score)
            except Exception:
                continue
        
        self.update_elite_pool()
        initial_stats = self.atomics.atomic_get_all_stats()
        print(f"   Initial best: {initial_stats['best_score']} bits")
        
        # Main optimization loop
        for round_num in range(self.config.MAX_ROUNDS):
            try:
                round_start_stats = self.atomics.atomic_get_all_stats()
                
                # Show progress
                if round_num % 5 == 0:
                    print(f"   Round {round_num}/{self.config.MAX_ROUNDS} - Best: {round_start_stats['best_score']} bits")
                
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
                
                improved = round_end_stats['best_score'] < round_start_stats['best_score']
                if improved:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_DECAY)
                    print(f"   ⭐ NEW BEST: {round_end_stats['best_score']} bits at round {round_num}")
                elif round_num % 5 == 0:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_INCREASE)
                
                # Diversity injection on stagnation
                if round_num % 8 == 0:
                    self.inject_diversity()
                
                # Heavy weight reset if locked in (no improvements for many rounds)
                if round_num % 20 == 0 and round_end_stats['best_score'] == round_start_stats['best_score']:
                    self.hex_manager.reset_position_weights()
                
                # Early termination for excellent results
                if round_end_stats['best_score'] <= 30:
                    break
                
            except Exception as e:
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
                'curve_name': self.curve_name,
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
                'evals_per_second': final_stats['evaluations'] / total_time if total_time > 0 else 0,
                'elite_keys': self.elite_keys  # Store for post-mortem analysis
            }
        except Exception as e:
            return {'error': str(e)}

def compare_curve_results(all_results: List[dict]) -> dict:
    """Analyze results across curves for patterns"""
    valid_results = [r for r in all_results if 'error' not in r]
    
    if not valid_results:
        return {'error': 'No valid results to compare'}
    
    # Extract key metrics
    best_scores = [r['best_score'] for r in valid_results]
    evaluations = [r['total_evaluations'] for r in valid_results]
    improvements = [r['improvements'] for r in valid_results]
    elite_means = [r['elite_mean'] for r in valid_results]
    active_bytes = [r['final_hex_stats']['current_active_bytes'] for r in valid_results]
    
    # Calculate statistics
    comparison = {
        'curves_tested': len(valid_results),
        'best_score_stats': {
            'mean': statistics.mean(best_scores),
            'stdev': statistics.stdev(best_scores) if len(best_scores) > 1 else 0,
            'min': min(best_scores),
            'max': max(best_scores),
            'range': max(best_scores) - min(best_scores)
        },
        'evaluations_stats': {
            'mean': statistics.mean(evaluations),
            'stdev': statistics.stdev(evaluations) if len(evaluations) > 1 else 0,
            'min': min(evaluations),
            'max': max(evaluations)
        },
        'improvements_stats': {
            'mean': statistics.mean(improvements),
            'stdev': statistics.stdev(improvements) if len(improvements) > 1 else 0,
            'min': min(improvements),
            'max': max(improvements)
        },
        'elite_mean_stats': {
            'mean': statistics.mean(elite_means),
            'stdev': statistics.stdev(elite_means) if len(elite_means) > 1 else 0,
            'min': min(elite_means),
            'max': max(elite_means)
        },
        'active_bytes_stats': {
            'mean': statistics.mean(active_bytes),
            'stdev': statistics.stdev(active_bytes) if len(active_bytes) > 1 else 0,
            'min': min(active_bytes),
            'max': max(active_bytes)
        },
        'improvement_over_random': {
            curve['curve_name']: 80.0 - curve['best_score'] 
            for curve in valid_results
        }
    }
    
    # Detect patterns
    patterns = []
    
    # Check if performance is similar across curves
    if comparison['best_score_stats']['stdev'] < 5.0:
        patterns.append("SIMILAR PERFORMANCE: GA shows consistent behavior across curves")
    
    if comparison['active_bytes_stats']['stdev'] < 1.0:
        patterns.append("SIMILAR BYTE USAGE: GA converges to similar key ranges")
    
    # Check if all curves show significant improvement over random
    all_improved = all(imp > 10 for imp in comparison['improvement_over_random'].values())
    if all_improved:
        patterns.append("UNIVERSAL IMPROVEMENT: All curves show significant gains over random")
    
    # Check for NIST vs non-NIST patterns
    nist_scores = [r['best_score'] for r in valid_results if 'nist' in r['curve_name'].lower()]
    non_nist_scores = [r['best_score'] for r in valid_results if 'nist' not in r['curve_name'].lower()]
    
    if nist_scores and non_nist_scores:
        nist_mean = statistics.mean(nist_scores)
        non_nist_mean = statistics.mean(non_nist_scores)
        if abs(nist_mean - non_nist_mean) > 10:
            patterns.append(f"CURVE TYPE DIFFERENCE: NIST curves avg {nist_mean:.1f} vs non-NIST {non_nist_mean:.1f}")
    
    # Check for Montgomery vs Weierstrass curve patterns
    montgomery_scores = [r['best_score'] for r in valid_results if r['curve_name'] == 'curve25519']
    weierstrass_scores = [r['best_score'] for r in valid_results if r['curve_name'] != 'curve25519']
    
    if montgomery_scores and weierstrass_scores:
        montgomery_mean = statistics.mean(montgomery_scores)
        weierstrass_mean = statistics.mean(weierstrass_scores)
        if abs(montgomery_mean - weierstrass_mean) > 10:
            patterns.append(f"CURVE FORM DIFFERENCE: Montgomery avg {montgomery_mean:.1f} vs Weierstrass {weierstrass_mean:.1f}")
    
    comparison['patterns'] = patterns
    
    return comparison

def run_multi_curve_test():
    """Run GA test across multiple curves"""
    print("🔥 MULTI-CURVE ECC GA TEST - NO DIVERSITY")
    print("="*70)
    print(f"🧪 Testing GA performance across {len(CURVES_TO_TEST)} elliptic curves")
    print("🔍 Looking for universal patterns that might indicate systematic ECC properties")
    print("⚡ 20 rounds per curve, unique target per curve")
    if HAS_COINCURVE:
        print("🚀 Using coincurve for secp256k1 (fast)")
    if HAS_CURVE25519:
        print("🚀 Using py_ecc for Curve25519")
    if not HAS_COINCURVE and not HAS_CURVE25519:
        print("⚠️  Using ecdsa for all curves (slower)")
    print("="*70)
    
    config = SingleTargetConfig()
    all_results = []
    all_true_keys = []
    
    for i, (curve_name, curve) in enumerate(CURVES_TO_TEST):
        print(f"\n{'='*70}")
        print(f"🧪 TESTING CURVE {i+1}/{len(CURVES_TO_TEST)}: {curve_name}")
        if curve_name == 'secp256k1' and HAS_COINCURVE:
            print("   Using fast coincurve engine")
        elif curve_name == 'curve25519' and HAS_CURVE25519:
            print("   Using PyNaCl/cryptography for Montgomery curve")
        else:
            print("   Using ecdsa engine")
        print(f"{'='*70}")
        
        # Generate UNIQUE target and true private key for this curve
        target_hash, true_private_key = generate_unique_target_for_curve(curve_name, curve, i)
        all_true_keys.append(true_private_key)
        print(f"🎯 Generated unique target: {target_hash}")
        print(f"🔑 True private key: 0x{int.from_bytes(true_private_key, 'big'):X}")
        
        # Run GA
        engine = SingleTargetEngine(config, curve_name, curve)
        results = engine.run_optimization(target_hash)
        
        # Store elite keys for analysis
        results['elite_keys'] = engine.elite_keys
        all_results.append(results)
        
        # Show curve-specific results
        if 'error' not in results:
            print(f"\n📊 {curve_name} RESULTS:")
            print(f"   Best Score: {results['best_score']} bits")
            print(f"   Best Key: {results['best_key_int']}")
            print(f"   Evaluations: {results['total_evaluations']:,}")
            print(f"   Time: {results['total_time']:.1f}s")
            print(f"   Speed: {results['evals_per_second']:,.0f} evals/sec")
            print(f"   Active Bytes: {results['final_hex_stats']['current_active_bytes']}")
            print(f"   Improvement over random: {80.0 - results['best_score']:.1f} bits")
            
            # POST-MORTEM ANALYSIS
            print(f"\n🔬 POST-MORTEM PRIVATE KEY ANALYSIS:")
            
            # Get curve order and field prime for variants
            if isinstance(curve, str):
                # secp256k1 via coincurve
                curve_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
                field_prime = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
            elif curve_name == 'curve25519':
                # Curve25519 parameters
                curve_order = curve.order
                field_prime = curve.curve.p()
            else:
                # ecdsa curves
                curve_order = curve.order
                field_prime = curve.curve.p()
                
            key_analysis = analyze_curve_results_with_true_key(results, true_private_key, results['elite_keys'], curve_order, field_prime)
            
            print(f"   📌 True Private Key: 0x{key_analysis['true_key_int']:X}")
            print(f"   🎯 Best Found Key:   0x{key_analysis['best_found_analysis']['key_int']:X}")
            print(f"   📏 Distance to true: {key_analysis['best_found_analysis']['hamming_distance_bits']} bits")
            print(f"   🎲 Need {key_analysis['best_found_analysis']['power_to_true_key']} operations to reach true key")
            
            if key_analysis['best_found_analysis']['exact_match']:
                print(f"   🎉 EXACT MATCH FOUND!")
            
            print(f"\n   🏆 CLOSEST KEY FOUND (checking all variants):")
            print(f"      Key: 0x{key_analysis['closest_found']['key_int']:X}")
            print(f"      Source: {key_analysis['closest_found']['source']}")
            print(f"      Variant: {key_analysis['closest_found']['variant_type']}")
            print(f"      Distance: {key_analysis['closest_found']['hamming_distance_bits']} bits away")
            print(f"      To reach true key: {key_analysis['closest_found']['power_to_reach_true_key']} operations")
            print(f"      Correct bits: {key_analysis['closest_found']['percentage_correct']:.1f}%")
            
            # Variant analysis table
            print(f"\n   📊 VARIANT ANALYSIS TABLE:")
            print(f"      {'Variant':<25} | {'Description':<50} | {'Best 2^x':<10} | {'Avg 2^x':<10}")
            print(f"      {'-'*25}-+-{'-'*50}-+-{'-'*10}-+-{'-'*10}")
            
            for variant in key_analysis['variant_analysis']['variant_table'][:10]:  # Show top 10
                desc = variant['description'][:50]
                best = f"2^{variant['best_distance']}"
                avg = f"2^{variant['avg_distance']:.1f}"
                print(f"      {variant['variant']:<25} | {desc:<50} | {best:<10} | {avg:<10}")
            
            print(f"\n      Total variants tested: {key_analysis['variant_analysis']['total_variants_tested']}")
            print(f"      Total keys×variants: {key_analysis['variant_analysis']['total_keys_tested']}")
            print(f"      Best variant type: {key_analysis['variant_analysis']['best_variant']}")
            
            # Show top 3 from elite
            print(f"\n   📊 TOP 3 ELITE KEYS (original only):")
            for elite_info in key_analysis['top_10_analysis'][:3]:
                print(f"      #{elite_info['rank']}: {elite_info['hamming_distance_bits']} bits away, "
                      f"need {elite_info['power_to_true_key']} to reach true key")
                if 'dual_ec_scalar' in elite_info:
                    print(f"         ⚠️  Dual EC-like scalar found: d = {elite_info['dual_ec_scalar']}")
            # Thorough Dual EC scalar search
            if key_analysis.get('dual_ec_scalar_findings'):
                print(f"\n   🔎 DUAL EC-LIKE SCALAR SEARCH (all elite keys):")
                for finding in key_analysis['dual_ec_scalar_findings']:
                    print(f"      ⚠️  Elite #{finding['elite_index']} ({finding['elite_key_hex']}) has scalar d = {finding['scalar_d']} to true key")
            else:
                print(f"\n   ✅ No Dual EC-like scalar found among elite keys.")
            
            # Store analysis in results
            results['private_key_analysis'] = key_analysis
            
        else:
            print(f"❌ Error: {results['error']}")
    
    # Compare results across curves
    print(f"\n{'='*70}")
    print("🔬 CROSS-CURVE ANALYSIS")
    print("="*70)
    
    comparison = compare_curve_results(all_results)
    
    if 'error' not in comparison:
        print(f"📊 STATISTICAL SUMMARY:")
        print(f"   Curves tested: {comparison['curves_tested']}")
        
        print(f"\n   Best Score Statistics:")
        print(f"      Mean: {comparison['best_score_stats']['mean']:.1f} bits")
        print(f"      StdDev: {comparison['best_score_stats']['stdev']:.1f} bits")
        print(f"      Range: {comparison['best_score_stats']['min']} - {comparison['best_score_stats']['max']} bits")
        
        print(f"\n   Active Bytes Statistics:")
        print(f"      Mean: {comparison['active_bytes_stats']['mean']:.1f} bytes")
        print(f"      StdDev: {comparison['active_bytes_stats']['stdev']:.1f} bytes")
        print(f"      Range: {comparison['active_bytes_stats']['min']} - {comparison['active_bytes_stats']['max']} bytes")
        
        print(f"\n   Improvement over Random (per curve):")
        for curve, improvement in comparison['improvement_over_random'].items():
            print(f"      {curve}: {improvement:.1f} bits")
        
        # Add private key analysis summary
        print(f"\n   🔑 PRIVATE KEY CLOSENESS SUMMARY:")
        for i, (curve_name, _) in enumerate(CURVES_TO_TEST):
            if i < len(all_results) and 'private_key_analysis' in all_results[i]:
                analysis = all_results[i]['private_key_analysis']
                print(f"      {curve_name}: {analysis['closest_found']['power_to_reach_true_key']} to reach true key "
                      f"({analysis['closest_found']['percentage_correct']:.1f}% bits correct)")
        
        if comparison['patterns']:
            print(f"\n🔍 DETECTED PATTERNS:")
            for pattern in comparison['patterns']:
                print(f"   ⚠️  {pattern}")
        else:
            print(f"\n✅ No significant universal patterns detected")
        
        # Final interpretation
        print(f"\n{'='*70}")
        print("🧪 INTERPRETATION:")
        
        if comparison['best_score_stats']['stdev'] < 5.0:
            print("🚨 HIGH SIMILARITY: GA performs nearly identically across curves!")
            print("   This could indicate:")
            print("   - A universal property of elliptic curve discrete logs")
            print("   - A systematic weakness or pattern in ECC")
            print("   - GA exploiting a common structure across curves")
        else:
            print("✅ DIVERSE RESULTS: GA shows different performance across curves")
            print("   This suggests curve-specific properties matter")
        
        all_improved = all(imp > 10 for imp in comparison['improvement_over_random'].values())
        if all_improved:
            print("\n⚠️  ALL CURVES VULNERABLE: Every tested curve shows significant GA improvement")
            print("   This universal improvement pattern is concerning!")
    
    return all_results, comparison

def generate_unique_target_for_curve(curve_name, curve, index):
    """Generate a unique target hash and true private key for the given curve."""
    key_size = CURVE_KEY_SIZES[curve_name]
    # Generate a random private key in the valid range
    if hasattr(curve, 'order'):
        order = curve.order
    else:
        # For dummy Curve25519 class
        order = 0x1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed
    while True:
        priv_int = random.randrange(1, order)
        private_key = priv_int.to_bytes(key_size, 'big')
        if 1 <= priv_int < order:
            break
    # Generate the corresponding public key hash160
    crypto = MultiCurveCryptoOps(curve, curve_name)
    pub_hash = crypto.private_key_to_hash160(private_key)
    return pub_hash.hex(), private_key

# Main execution
if __name__ == "__main__":
    results, comparison = run_multi_curve_test()
    
    print(f"\n{'='*70}")
    print("🔬 TEST COMPLETE")
    print("="*70)
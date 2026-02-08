#!/usr/bin/env python3
"""
Enhanced Multi-Curve ECC GA Test - Tests both compressed/uncompressed formats
with extensive mathematical post-mortem analysis looking for patterns and constants
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
    
    # Always install ecdsa for other curves
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "ecdsa", "pycryptodome"])
    
    import numpy as np
    from ecdsa import SECP256k1, NIST256p, NIST384p, NIST521p, SigningKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os

print(f"✅ Ready to test all curves with both compression formats")

# Always test all 4 curves
CURVES_TO_TEST = [
    ('secp256k1', SECP256k1),      # Bitcoin curve - will use coincurve if available
    ('nist256p', NIST256p),        # NIST P-256
    ('nist384p', NIST384p),        # NIST P-384
    ('nist521p', NIST521p),        # NIST P-521
]

# Test both compression formats
COMPRESSION_FORMATS = [True, False]  # True = compressed, False = uncompressed

# Curve specifications
CURVE_KEY_SIZES = {
    'secp256k1': 32,  # 256 bits
    'nist256p': 32,   # 256 bits
    'nist384p': 48,   # 384 bits
    'nist521p': 66,   # 521 bits (rounded up to 66 bytes)
}

# REAL BITCOIN CONSTANTS AND PATTERNS - NO ARTIFICIAL CONSTRAINTS!
BITCOIN_CONSTANTS = {
    # Core secp256k1 curve constants
    'secp256k1_order': 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
    'secp256k1_field_prime': 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F,
    'secp256k1_generator_x': 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    'secp256k1_generator_y': 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
    'secp256k1_half_order': 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0,
    'secp256k1_quarter_order': 0x3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFAEABABBBA9D2280EEFF497A340D905,
    
    # Generator/2 special point (mysterious pattern)
    'secp256k1_generator_half_x': 0x3b78ce563f89a0ed9414f5aa28ad0d96d6795f9c63,
    
    # Bitcoin specific values
    'satoshi_per_bitcoin': 100000000,  # 1 BTC = 100M satoshis
    'max_bitcoin_supply': 2100000000000000,  # 21M BTC in satoshis
    'max_bitcoin_supply_raw': 21000000,  # 21M BTC
    'genesis_reward': 5000000000,  # 50 BTC in satoshis
    'current_reward': 312500000,   # 3.125 BTC in satoshis (post 2024 halving)
    
    # Block and transaction constants
    'max_block_size': 4000000,  # 4MB weight limit
    'legacy_block_size': 1000000,  # 1MB legacy limit
    'blocks_per_halving': 210000,  # Halving every 210k blocks
    'target_block_time': 600,  # 10 minutes in seconds
    'difficulty_adjustment_blocks': 2016,  # Adjust every 2016 blocks
    
    # Common transaction fee ranges (in satoshis)
    'typical_fees_low': [1, 2, 3, 4, 5, 10, 20, 30, 50, 100],
    'typical_fees_medium': [200, 300, 500, 1000, 1500, 2000, 3000, 5000],
    'typical_fees_high': [10000, 15000, 20000, 30000, 50000, 100000],
    'fee_spike_2024': [160000, 180500, 200000, 250000],  # Post-halving spike
    
    # Version bytes for addresses
    'address_version_p2pkh_mainnet': 0x00,  # Legacy addresses start with '1'
    'address_version_p2sh_mainnet': 0x05,   # Script addresses start with '3'
    'address_version_p2pkh_testnet': 0x6f,  # Testnet legacy
    'address_version_p2sh_testnet': 0xc4,   # Testnet script
    
    # Common opcodes (hex values)
    'op_dup': 0x76,
    'op_hash160': 0xa9,
    'op_equalverify': 0x88,
    'op_checksig': 0xac,
    'op_return': 0x6a,
    'op_pushdata1': 0x4c,
    'op_pushdata2': 0x4d,
    'op_pushdata4': 0x4e,
    'op_1': 0x51,
    'op_16': 0x60,
    
    # Script sizes and patterns
    'p2pkh_script_size': 25,  # OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG
    'p2sh_script_size': 23,   # OP_HASH160 <20 bytes> OP_EQUAL
    'p2wpkh_script_size': 22, # OP_0 <20 bytes>
    'hash160_size': 20,       # RIPEMD160(SHA256(pubkey))
    'sha256_size': 32,        # SHA256 output
    
    # Timestamp boundaries
    'bitcoin_genesis_timestamp': 1231006505,  # Jan 3, 2009
    'first_halving_timestamp': 1353616706,   # 2012
    'second_halving_timestamp': 1468057825,  # 2016
    'third_halving_timestamp': 1589256139,   # 2020
    'fourth_halving_timestamp': 1713487217,  # 2024
}

# Generate extensive moduli list from Bitcoin reality
def generate_bitcoin_moduli():
    """Generate comprehensive list of moduli based on real Bitcoin patterns"""
    moduli = []
    
    # Core Bitcoin constants - handle both integers and lists
    for const_name, const_value in BITCOIN_CONSTANTS.items():
        if isinstance(const_value, int):
            moduli.append(const_value)
        elif isinstance(const_value, list):
            moduli.extend([v for v in const_value if isinstance(v, int)])
    
    # Powers of 2 (Bitcoin is heavily based on powers of 2)
    for i in range(1, 300):  # Up to 2^300 - no artificial constraints!
        try:
            power_val = 2**i
            moduli.append(power_val)
            moduli.append(power_val - 1)  # Mersenne-like numbers
            moduli.append(power_val + 1)  # Fermat-like numbers
        except OverflowError:
            break  # Stop if numbers get too large
    
    # Small primes and composites (common in crypto)
    small_numbers = list(range(1, 100000))  # First 100k numbers (reduced for performance)
    moduli.extend(small_numbers)
    
    # Bitcoin-specific derived values
    bitcoin_bases = [100000000, 21000000, 210000, 2016, 600]  # Core BTC numbers
    for base in bitcoin_bases:
        for mult in range(1, 1000):  # Reduced multipliers for performance
            moduli.append(base * mult)
            if base % mult == 0:
                moduli.append(base // mult)
    
    # Transaction fee patterns (real observed values)
    fee_bases = [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000]
    for base in fee_bases:
        for mult in range(1, 10000):  # Reasonable range
            moduli.append(base * mult)
    
    # Hex boundary patterns
    hex_boundaries = []
    for bytes_count in range(1, 50):  # Up to 50 bytes (reduced for performance)
        try:
            boundary = 256**bytes_count
            hex_boundaries.append(boundary)
            hex_boundaries.append(boundary - 1)
            hex_boundaries.append(boundary + 1)
        except OverflowError:
            break
    moduli.extend(hex_boundaries)
    
    # Address and script patterns
    address_patterns = [26, 27, 28, 29, 30, 31, 32, 33, 34, 35]  # Address lengths
    for length in address_patterns:
        for base in [58, 256]:  # Base58 and byte patterns
            try:
                val = base**length
                moduli.append(val)
                moduli.append(val - 1)
            except OverflowError:
                continue
    
    # Curve order related patterns
    curve_order = BITCOIN_CONSTANTS['secp256k1_order']
    field_prime = BITCOIN_CONSTANTS['secp256k1_field_prime']
    
    # Fractions and multiples of curve order (reasonable range)
    for divisor in range(1, 10000):  # Reduced for performance
        try:
            if curve_order % divisor == 0:
                moduli.append(curve_order // divisor)
            moduli.append(curve_order * divisor)
            
            if field_prime % divisor == 0:
                moduli.append(field_prime // divisor)
            moduli.append(field_prime * divisor)
        except OverflowError:
            continue
    
    # Mystery generator/2 pattern derivatives
    gen_half = BITCOIN_CONSTANTS['secp256k1_generator_half_x']
    for mult in range(1, 10000):  # Reduced range
        try:
            moduli.append(gen_half * mult)
            moduli.append(gen_half + mult)
            moduli.append(abs(gen_half - mult))
        except OverflowError:
            continue
    
    # Timestamp derivatives
    timestamps = [BITCOIN_CONSTANTS['bitcoin_genesis_timestamp'], 
                 BITCOIN_CONSTANTS['fourth_halving_timestamp']]
    for timestamp in timestamps:
        for mult in range(1, 1000):  # Reduced range
            try:
                moduli.append(timestamp * mult)
                moduli.append(timestamp + mult)
            except OverflowError:
                continue
    
    # Common crypto numbers
    crypto_numbers = [
        # DES/AES related
        56, 64, 128, 192, 256, 512, 1024, 2048, 4096, 8192,
        # RSA common sizes
        1024, 2048, 3072, 4096, 7680, 15360,
        # Hash output sizes
        160, 224, 256, 384, 512,
        # Common moduli in number theory
        997, 1009, 1013, 1019, 1021, 1031, 1033, 1039,  # Primes near 1024
    ]
    
    for base in crypto_numbers:
        for mult in range(1, 1000):  # Reduced range
            try:
                moduli.append(base * mult)
            except OverflowError:
                continue
    
    # Financial/economic numbers
    economic_bases = [
        365, 366,  # Days per year
        12, 52,    # Months, weeks
        7, 24, 60, 3600,  # Time units
        100, 1000, 10000, 100000, 1000000,  # Decimal scales
    ]
    
    for base in economic_bases:
        for mult in range(1, 10000):  # Reduced range
            try:
                moduli.append(base * mult)
            except OverflowError:
                continue
    
    # Fibonacci and Lucas sequences (crypto loves these)
    fib_a, fib_b = 1, 1
    for _ in range(500):  # Reduced to 500 Fibonacci numbers
        try:
            moduli.append(fib_a)
            fib_a, fib_b = fib_b, fib_a + fib_b
        except OverflowError:
            break
    
    # Perfect numbers, primes, and special sequences
    for n in range(1, 10000):  # Reduced range for performance
        try:
            # Perfect squares and cubes
            moduli.append(n**2)
            moduli.append(n**3)
            
            # Triangular numbers
            moduli.append(n * (n + 1) // 2)
            
            # Factorials (up to reasonable size)
            if n <= 50:  # Reduced factorial range
                factorial = 1
                for i in range(1, n + 1):
                    factorial *= i
                    if factorial > 10**50:  # Limit factorial size
                        break
                moduli.append(factorial)
        except OverflowError:
            continue
    
    # Remove duplicates, filter positive integers only, and return sorted
    unique_moduli = []
    seen = set()
    for m in moduli:
        if isinstance(m, int) and m > 0 and m not in seen and m < 10**50:  # Reasonable size limit
            unique_moduli.append(m)
            seen.add(m)
    
    unique_moduli.sort()
    
    print(f"Generated {len(unique_moduli):,} unique moduli for testing")
    return unique_moduli

# Global moduli list - generated once
EXTENSIVE_MODULI = generate_bitcoin_moduli()

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
    MAX_ROUNDS: int = 15                  # Reduced to 15 rounds per test
    DETAILED_LOGGING: bool = True        # Less verbose for multi-curve

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
    """Crypto operations supporting multiple curves with compression format control"""
    def __init__(self, curve, curve_name, compressed=True):
        self.curve = curve
        self.curve_name = curve_name
        self.key_size = CURVE_KEY_SIZES[curve_name]
        self.compressed = compressed  # NEW: Control compression format
        # Use coincurve for secp256k1 if available
        self.use_coincurve = (curve_name == 'secp256k1' and HAS_COINCURVE)
        
    def scalar_mult_curve(self, private_key: bytes) -> bytes:
        if len(private_key) != self.key_size:
            raise ValueError(f"Private key must be {self.key_size} bytes for {self.curve_name}")
        
        try:
            if self.use_coincurve:
                # coincurve is MUCH faster for secp256k1
                privkey = coincurve.PrivateKey(private_key)
                return privkey.public_key.format(compressed=self.compressed)
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
                
                if self.compressed:
                    # Compressed format
                    prefix = 0x02 if (y % 2 == 0) else 0x03
                    # Handle different bit lengths for different curves
                    byte_length = (self.curve.order.bit_length() + 7) // 8
                    x_bytes = x.to_bytes(byte_length, 'big')
                    return bytes([prefix]) + x_bytes
                else:
                    # Uncompressed format
                    byte_length = (self.curve.order.bit_length() + 7) // 8
                    x_bytes = x.to_bytes(byte_length, 'big')
                    y_bytes = y.to_bytes(byte_length, 'big')
                    return bytes([0x04]) + x_bytes + y_bytes
        except Exception as e:
            # Return a valid dummy pubkey
            byte_length = (self.curve.order.bit_length() + 7) // 8 if not self.use_coincurve else 32
            if self.compressed:
                return b'\x02' + b'\x00' * byte_length
            else:
                return b'\x04' + b'\x00' * (byte_length * 2)
    
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

# ENHANCED MATHEMATICAL ANALYSIS FUNCTIONS

def gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor"""
    while b:
        a, b = b, a % b
    return a

def find_mathematical_patterns(numbers: List[int]) -> dict:
    """Look for mathematical patterns in a list of integers"""
    if not numbers:
        return {}
    
    patterns = {}
    
    # Basic statistics
    patterns['count'] = len(numbers)
    patterns['sum'] = sum(numbers)
    patterns['mean'] = statistics.mean(numbers)
    patterns['median'] = statistics.median(numbers)
    if len(numbers) > 1:
        patterns['stdev'] = statistics.stdev(numbers)
    
    # Look for common factors
    if len(numbers) > 1:
        overall_gcd = numbers[0]
        for num in numbers[1:]:
            overall_gcd = gcd(overall_gcd, num)
        patterns['gcd'] = overall_gcd
    
    # Check for arithmetic progressions
    if len(numbers) > 2:
        diffs = [numbers[i+1] - numbers[i] for i in range(len(numbers)-1)]
        if len(set(diffs)) == 1 and diffs[0] != 0:
            patterns['arithmetic_progression'] = diffs[0]
    
    # Check for geometric progressions
    if len(numbers) > 2 and all(n > 0 for n in numbers):
        ratios = [numbers[i+1] / numbers[i] for i in range(len(numbers)-1) if numbers[i] != 0]
        if ratios and len(set(ratios)) == 1:
            patterns['geometric_progression'] = ratios[0]
    
    # Check for powers of 2
    powers_of_2 = [n for n in numbers if n > 0 and (n & (n - 1)) == 0]
    if powers_of_2:
        patterns['powers_of_2'] = powers_of_2
    
    # Check for Fibonacci-like sequences
    if len(numbers) >= 3:
        fib_like = True
        for i in range(2, len(numbers)):
            if numbers[i] != numbers[i-1] + numbers[i-2]:
                fib_like = False
                break
        if fib_like:
            patterns['fibonacci_like'] = True
    
    return patterns

def analyze_key_mathematical_relationships(best_key: bytes, elite_keys: List[bytes], 
                                         true_key: bytes, curve_order: int, field_prime: int) -> dict:
    """UNRESTRICTED mathematical analysis using ALL Bitcoin patterns and extensive moduli"""
    
    analysis = {
        'true_key_int': int.from_bytes(true_key, 'big'),
        'best_key_int': int.from_bytes(best_key, 'big'),
        'curve_order': curve_order,
        'field_prime': field_prime,
        'relationships': {},
        'elite_analysis': {},
        'constants_found': {},
        'patterns': {},
        'bitcoin_specific_analysis': {}
    }
    
    best_int = int.from_bytes(best_key, 'big')
    true_int = int.from_bytes(true_key, 'big')
    elite_ints = [int.from_bytes(key, 'big') for key in elite_keys[:50]]  # More elite keys
    
    # ABSOLUTE DIFFERENCES
    abs_diff_best = abs(best_int - true_int)
    elite_abs_diffs = [abs(elite_int - true_int) for elite_int in elite_ints]
    elite_abs_diffs_from_best = [abs(elite_int - best_int) for elite_int in elite_ints]
    
    analysis['relationships']['absolute_differences'] = {
        'best_to_true': abs_diff_best,
        'best_to_true_hex': f"0x{abs_diff_best:X}",
        'elite_to_true': elite_abs_diffs,
        'elite_to_best': elite_abs_diffs_from_best
    }
    
    # EXTENSIVE MODULAR ARITHMETIC - NO CONSTRAINTS!
    print(f"   🔍 Testing {len(EXTENSIVE_MODULI):,} moduli for patterns...")
    
    remainder_analysis = {}
    significant_patterns = []
    
    # Test sample of moduli (to avoid excessive computation but still be thorough)
    moduli_to_test = EXTENSIVE_MODULI[::max(1, len(EXTENSIVE_MODULI) // 50000)]  # Sample up to 50k moduli
    
    for modulus in moduli_to_test:
        if modulus == 0:
            continue
            
        try:
            remainders = {
                'true_key_mod': true_int % modulus,
                'best_key_mod': best_int % modulus,
                'abs_diff_mod': abs_diff_best % modulus,
                'elite_mods': [elite_int % modulus for elite_int in elite_ints]
            }
            
            # Check if there are patterns in the remainders
            elite_mod_counts = {}
            for mod_val in remainders['elite_mods']:
                elite_mod_counts[mod_val] = elite_mod_counts.get(mod_val, 0) + 1
            
            # Look for clustering
            most_common_remainder = max(elite_mod_counts.items(), key=lambda x: x[1]) if elite_mod_counts else (0, 0)
            clustering_strength = most_common_remainder[1] / len(elite_ints) if elite_ints else 0
            
            # Only store interesting patterns (clustering > 20% or special moduli)
            if (clustering_strength > 0.2 or 
                modulus in BITCOIN_CONSTANTS.values() or
                modulus in [2**i for i in range(1, 65)] or  # Powers of 2
                modulus < 1000):  # Small numbers
                
                remainder_analysis[modulus] = {
                    **remainders,
                    'elite_mod_counts': elite_mod_counts,
                    'most_common_remainder': most_common_remainder[0],
                    'clustering_strength': clustering_strength
                }
                
                # Track significant patterns
                if clustering_strength > 0.3:
                    significant_patterns.append({
                        'modulus': modulus,
                        'clustering': clustering_strength,
                        'remainder': most_common_remainder[0],
                        'count': most_common_remainder[1]
                    })
        except:
            continue
    
    analysis['relationships']['remainder_analysis'] = remainder_analysis
    analysis['relationships']['significant_patterns'] = sorted(significant_patterns, 
                                                             key=lambda x: x['clustering'], reverse=True)
    
    # BITCOIN-SPECIFIC ANALYSIS
    bitcoin_analysis = {}
    
    # Check relationships to core Bitcoin constants
    for const_name, const_value in BITCOIN_CONSTANTS.items():
        if isinstance(const_value, int):
            bitcoin_analysis[const_name] = {
                'true_key_relation': {
                    'mod': true_int % const_value if const_value > 0 else 0,
                    'quotient': true_int // const_value if const_value > 0 else 0,
                    'difference': abs(true_int - const_value),
                    'ratio': true_int / const_value if const_value > 0 else 0
                },
                'best_key_relation': {
                    'mod': best_int % const_value if const_value > 0 else 0,
                    'quotient': best_int // const_value if const_value > 0 else 0,
                    'difference': abs(best_int - const_value),
                    'ratio': best_int / const_value if const_value > 0 else 0
                },
                'abs_diff_relation': {
                    'mod': abs_diff_best % const_value if const_value > 0 else 0,
                    'quotient': abs_diff_best // const_value if const_value > 0 else 0,
                    'difference': abs(abs_diff_best - const_value),
                    'ratio': abs_diff_best / const_value if const_value > 0 else 0
                }
            }
    
    analysis['bitcoin_specific_analysis'] = bitcoin_analysis
    
    # SUMS AND PRODUCTS
    sums_analysis = {
        'best_plus_true': best_int + true_int,
        'best_plus_true_hex': f"0x{(best_int + true_int):X}",
        'elite_sums_with_true': [elite_int + true_int for elite_int in elite_ints],
        'elite_sums_with_best': [elite_int + best_int for elite_int in elite_ints],
        'total_elite_sum': sum(elite_ints),
        'avg_elite': statistics.mean(elite_ints) if elite_ints else 0,
        'geometric_mean_elite': statistics.geometric_mean([e for e in elite_ints if e > 0]) if elite_ints else 0
    }
    
    analysis['relationships']['sums_analysis'] = sums_analysis
    
    # GCD ANALYSIS
    if elite_ints:
        all_keys = [true_int, best_int] + elite_ints
        overall_gcd = all_keys[0]
        for key_int in all_keys[1:]:
            overall_gcd = gcd(overall_gcd, key_int)
        
        # Pairwise GCDs
        pairwise_gcds = []
        for i in range(len(all_keys)):
            for j in range(i+1, len(all_keys)):
                pairwise_gcds.append(gcd(all_keys[i], all_keys[j]))
        
        gcd_analysis = {
            'overall_gcd': overall_gcd,
            'pairwise_gcds': pairwise_gcds,
            'unique_gcds': list(set(pairwise_gcds)),
            'gcd_patterns': find_mathematical_patterns(pairwise_gcds)
        }
        
        analysis['relationships']['gcd_analysis'] = gcd_analysis
    
    # BIT PATTERNS
    bit_analysis = {
        'true_key_bits': bin(true_int)[2:],
        'best_key_bits': bin(best_int)[2:],
        'xor_pattern': bin(true_int ^ best_int)[2:],
        'and_pattern': bin(true_int & best_int)[2:],
        'or_pattern': bin(true_int | best_int)[2:],
        'true_key_popcount': bin(true_int).count('1'),
        'best_key_popcount': bin(best_int).count('1'),
        'elite_popcounts': [bin(elite_int).count('1') for elite_int in elite_ints],
        'hamming_weight_distribution': {
            count: sum(1 for e in elite_ints if bin(e).count('1') == count)
            for count in range(0, max([bin(e).count('1') for e in elite_ints] + [0]) + 1)
        }
    }
    
    analysis['relationships']['bit_analysis'] = bit_analysis
    
    # ENHANCED MATHEMATICAL CONSTANTS DETECTION
    constants_to_check = {
        'pi': int(math.pi * 10**15),  # Much higher precision
        'e': int(math.e * 10**15),
        'phi': int(((1 + math.sqrt(5)) / 2) * 10**15),  # Golden ratio
        'sqrt2': int(math.sqrt(2) * 10**15),
        'sqrt3': int(math.sqrt(3) * 10**15),
        'sqrt5': int(math.sqrt(5) * 10**15),
        'ln2': int(math.log(2) * 10**15),
        'ln10': int(math.log(10) * 10**15),
        'euler_gamma': int(0.5772156649015329 * 10**15),  # Euler-Mascheroni constant
        'catalan': int(0.9159655941772190 * 10**15),       # Catalan's constant
        'apery': int(1.2020569031595943 * 10**15),         # Apéry's constant (ζ(3))
        'khinchin': int(2.6854520010653064 * 10**15),      # Khinchin's constant
        'glaisher': int(1.2824271291006226 * 10**15),      # Glaisher-Kinkelin constant
    }
    
    constants_found = {}
    for const_name, const_val in constants_to_check.items():
        # Check multiple scaling factors - NO LIMITS
        for scale_exp in range(-10, 50):  # Much wider range
            scale = 10**scale_exp
            scaled_const = int(const_val * scale)
            
            if scaled_const == 0:
                continue
                
            # Check various relationships
            relationships_to_check = [
                ('abs_diff_match', abs_diff_best),
                ('sum_match', best_int + true_int),
                ('true_key_match', true_int),
                ('best_key_match', best_int),
                ('elite_avg_match', int(statistics.mean(elite_ints)) if elite_ints else 0),
                ('elite_sum_match', sum(elite_ints)),
            ]
            
            for rel_name, value in relationships_to_check:
                if value == 0:
                    continue
                    
                # Check direct equality and close matches
                diff = abs(value - scaled_const)
                relative_diff = diff / max(value, scaled_const) if max(value, scaled_const) > 0 else float('inf')
                
                if diff < 10000 or relative_diff < 0.01:  # Close match
                    key = f"{const_name}_{rel_name}_scale_1e{scale_exp}"
                    constants_found[key] = {
                        'constant_value': scaled_const,
                        'actual_value': value,
                        'difference': diff,
                        'relative_difference': relative_diff,
                        'type': rel_name,
                        'scale_exponent': scale_exp
                    }
    
    analysis['constants_found'] = constants_found
    
    # PATTERN ANALYSIS IN COLLECTIONS
    pattern_collections = {
        'absolute_differences': elite_abs_diffs,
        'remainders_mod_256': [x % 256 for x in elite_abs_diffs],
        'remainders_mod_curve_order': [x % curve_order for x in elite_abs_diffs],
        'remainders_mod_satoshi': [x % 100000000 for x in elite_abs_diffs],  # Bitcoin specific
        'remainders_mod_halving': [x % 210000 for x in elite_abs_diffs],      # Bitcoin specific
        'bit_counts': [bin(x).count('1') for x in elite_ints],
        'hex_digit_sums': [sum(int(c, 16) for c in hex(x)[2:]) for x in elite_ints],
        'byte_sums': [sum(x.to_bytes((x.bit_length() + 7) // 8, 'big')) for x in elite_ints],
        'leading_zeros': [len(bin(x)[2:]) for x in elite_ints],
    }
    
    for pattern_name, collection in pattern_collections.items():
        if collection:
            analysis['patterns'][pattern_name] = find_mathematical_patterns(collection)
    
    # SPECIAL SEQUENCE ANALYSIS
    sequences_found = {}
    
    # Check if elite keys follow known sequences
    sorted_elite = sorted(elite_ints)
    
    # Arithmetic progression check
    if len(sorted_elite) >= 3:
        diffs = [sorted_elite[i+1] - sorted_elite[i] for i in range(len(sorted_elite)-1)]
        if len(set(diffs)) <= 2:  # Allow small variations
            sequences_found['arithmetic_progression'] = {
                'common_difference': statistics.mode(diffs) if diffs else 0,
                'variations': len(set(diffs))
            }
    
    # Geometric progression check (with tolerance)
    if len(sorted_elite) >= 3 and all(x > 0 for x in sorted_elite):
        ratios = [sorted_elite[i+1] / sorted_elite[i] for i in range(len(sorted_elite)-1)]
        ratio_variance = statistics.variance(ratios) if len(ratios) > 1 else 0
        if ratio_variance < 0.1:  # Low variance indicates geometric progression
            sequences_found['geometric_progression'] = {
                'common_ratio': statistics.mean(ratios),
                'variance': ratio_variance
            }
    
    # Fibonacci-like check
    if len(sorted_elite) >= 3:
        fib_like_count = 0
        for i in range(2, len(sorted_elite)):
            if abs(sorted_elite[i] - (sorted_elite[i-1] + sorted_elite[i-2])) < 1000:
                fib_like_count += 1
        
        if fib_like_count > len(sorted_elite) * 0.5:
            sequences_found['fibonacci_like'] = {
                'matches': fib_like_count,
                'total': len(sorted_elite) - 2,
                'confidence': fib_like_count / (len(sorted_elite) - 2)
            }
    
    analysis['patterns']['special_sequences'] = sequences_found
    
    return analysis

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
    
    return variants

def analyze_curve_results_with_true_key(results: dict, true_private_key: bytes, elite_keys: List[bytes], 
                                      curve_order: int, field_prime: int, compressed: bool) -> dict:
    """Analyze how close the GA got to the true private key, including mathematical analysis"""
    analysis = {
        'compression_format': 'compressed' if compressed else 'uncompressed',
        'true_key_hex': true_private_key.hex(),
        'true_key_int': int.from_bytes(true_private_key, 'big'),
        'best_found_analysis': {},
        'top_10_analysis': [],
        'curve_order': curve_order,
        'variant_analysis': {},
        'mathematical_analysis': {}  # NEW: Enhanced mathematical analysis
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
        
        analysis['top_10_analysis'].append(elite_analysis)
    
    # NEW: EXTENSIVE MATHEMATICAL ANALYSIS
    analysis['mathematical_analysis'] = analyze_key_mathematical_relationships(
        best_key, elite_keys, true_private_key, curve_order, field_prime
    )
    
    return analysis

def get_variant_description(variant_name: str) -> str:
    """Get human-readable description of variant"""
    descriptions = {
        'original': 'Original key',
        'mirror_n-k': '(n - k) mod n - Mirror/negation',
        'inverse_1/k': '(1/k) mod n - Multiplicative inverse',
        'xor_all_ff': 'k ⊕ 0xFF...FF - XOR with all 1s',
        'xor_alternating': 'k ⊕ 0x5555... - XOR alternating bits',
        'xor_alternating2': 'k ⊕ 0xAAAA... - XOR alternating bits (inv)',
        'shift_left_1': 'k << 1 - Left shift by 1 bit',
        'shift_right_1': 'k >> 1 - Right shift by 1 bit',
        'byte_reversed': 'Byte-level reversal',
        'endian_swap_32': '32-bit endianness swap',
        'mod_p_fold': 'k mod p - Field prime folding',
        'complement': 'n - k - 1 - Complement',
        'rotate_left_byte': 'Rotate left by 1 byte',
        'add_1': '(k + 1) mod n',
        'sub_1': '(k - 1) mod n',
        'add_half_n': '(k + n/2) mod n - Add half order'
    }
    return descriptions.get(variant_name, variant_name)

def generate_unique_target_for_curve(curve_name: str, curve, index: int, compressed: bool) -> Tuple[str, bytes]:
    """Generate a UNIQUE target hash and private key for each curve using index and compression format"""
    # Use curve name + index + compression + random salt to ensure different targets
    import secrets
    
    # Generate a random private key for this curve
    key_size = CURVE_KEY_SIZES[curve_name]
    
    # Generate a valid private key for the curve
    if isinstance(curve, str):
        # For coincurve (secp256k1)
        max_key = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140
    else:
        # For ecdsa curves
        max_key = curve.order - 1
    
    # Generate random private key in valid range, influenced by compression format and index
    seed = hash((curve_name, index, compressed, secrets.randbits(64)))
    random.seed(seed)
    private_key_int = random.randint(1, max_key)
    private_key = private_key_int.to_bytes(key_size, 'big')
    
    # Generate the target hash from this private key
    crypto = MultiCurveCryptoOps(curve, curve_name, compressed)
    target_hash = crypto.private_key_to_hash160(private_key)
    
    return target_hash.hex(), private_key

class SingleTargetEngine:
    """Single target adaptive hex-aware GA engine"""
    
    def __init__(self, config: SingleTargetConfig, curve_name: str, curve, compressed: bool):
        self.config = config
        self.curve_name = curve_name
        self.curve = curve
        self.compressed = compressed
        self.key_size = CURVE_KEY_SIZES[curve_name]
        self.crypto = MultiCurveCryptoOps(curve, curve_name, compressed)
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
        compression_str = "compressed" if self.compressed else "uncompressed"
        print(f"   Initializing {self.config.K_POOL} keys ({compression_str})...")
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
        print(f"   Initial best: {initial_stats['best_score']} bits ({compression_str})")
        
        # Main optimization loop
        for round_num in range(self.config.MAX_ROUNDS):
            try:
                round_start_stats = self.atomics.atomic_get_all_stats()
                
                # Show progress
                if round_num % 5 == 0:
                    print(f"   Round {round_num}/{self.config.MAX_ROUNDS} - Best: {round_start_stats['best_score']} bits ({compression_str})")
                
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
                    print(f"   ⭐ NEW BEST: {round_end_stats['best_score']} bits at round {round_num} ({compression_str})")
                elif round_num % 5 == 0:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_INCREASE)
                
                # Diversity injection on stagnation
                if round_num % 8 == 0:
                    self.inject_diversity()
                
                # Heavy weight reset if locked in (no improvements for many rounds)
                if round_num % 20 == 0 and round_end_stats['best_score'] == round_start_stats['best_score']:
                    self.hex_manager.reset_position_weights()
                
                # Early termination for excellent results
                if round_end_stats['best_score'] <= 20:
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
                'compressed': self.compressed,
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
    """Analyze results across curves and compression formats for patterns"""
    valid_results = [r for r in all_results if 'error' not in r]
    
    if not valid_results:
        return {'error': 'No valid results to compare'}
    
    # Separate by compression format
    compressed_results = [r for r in valid_results if r.get('compressed', True)]
    uncompressed_results = [r for r in valid_results if not r.get('compressed', True)]
    
    # Extract key metrics
    best_scores = [r['best_score'] for r in valid_results]
    evaluations = [r['total_evaluations'] for r in valid_results]
    improvements = [r['improvements'] for r in valid_results]
    elite_means = [r['elite_mean'] for r in valid_results]
    
    # Calculate statistics
    comparison = {
        'total_tests': len(valid_results),
        'compressed_tests': len(compressed_results),
        'uncompressed_tests': len(uncompressed_results),
        'best_score_stats': {
            'mean': statistics.mean(best_scores),
            'stdev': statistics.stdev(best_scores) if len(best_scores) > 1 else 0,
            'min': min(best_scores),
            'max': max(best_scores),
            'range': max(best_scores) - min(best_scores)
        },
        'compression_comparison': {},
        'curve_comparison': {},
        'patterns': []
    }
    
    # Compare compression formats
    if compressed_results and uncompressed_results:
        comp_scores = [r['best_score'] for r in compressed_results]
        uncomp_scores = [r['best_score'] for r in uncompressed_results]
        
        comparison['compression_comparison'] = {
            'compressed_mean': statistics.mean(comp_scores),
            'uncompressed_mean': statistics.mean(uncomp_scores),
            'difference': statistics.mean(comp_scores) - statistics.mean(uncomp_scores),
            'compressed_better': statistics.mean(comp_scores) < statistics.mean(uncomp_scores)
        }
    
    # Compare by curve
    curve_stats = {}
    for result in valid_results:
        curve = result['curve_name']
        if curve not in curve_stats:
            curve_stats[curve] = {'scores': [], 'compressed': [], 'uncompressed': []}
        
        curve_stats[curve]['scores'].append(result['best_score'])
        if result.get('compressed', True):
            curve_stats[curve]['compressed'].append(result['best_score'])
        else:
            curve_stats[curve]['uncompressed'].append(result['best_score'])
    
    for curve, stats in curve_stats.items():
        comparison['curve_comparison'][curve] = {
            'mean_score': statistics.mean(stats['scores']),
            'compressed_mean': statistics.mean(stats['compressed']) if stats['compressed'] else None,
            'uncompressed_mean': statistics.mean(stats['uncompressed']) if stats['uncompressed'] else None,
            'test_count': len(stats['scores'])
        }
    
    # Detect patterns
    patterns = []
    
    # Check if performance is similar across compression formats
    if comparison.get('compression_comparison'):
        comp_diff = abs(comparison['compression_comparison']['difference'])
        if comp_diff < 3.0:
            patterns.append("COMPRESSION INSENSITIVE: Similar performance for compressed/uncompressed")
        elif comparison['compression_comparison']['compressed_better']:
            patterns.append(f"COMPRESSED ADVANTAGE: {comp_diff:.1f} bits better on average")
        else:
            patterns.append(f"UNCOMPRESSED ADVANTAGE: {comp_diff:.1f} bits better on average")
    
    # Check for curve-specific patterns
    curve_means = [stats['mean_score'] for stats in comparison['curve_comparison'].values()]
    if curve_means and statistics.stdev(curve_means) < 3.0:
        patterns.append("CURVE INSENSITIVE: Similar performance across all curves")
    
    comparison['patterns'] = patterns
    
    return comparison

def run_multi_curve_compression_test():
    """Run GA test across multiple curves and compression formats"""
    print("🔥 ENHANCED MULTI-CURVE ECC GA TEST - COMPRESSION FORMATS + MATH ANALYSIS")
    print("="*80)
    print("🧪 Testing GA performance across 4 elliptic curves × 2 compression formats")
    print("🔍 Looking for patterns between compressed/uncompressed public keys")
    print("🧮 EXTENSIVE mathematical post-mortem analysis with constants & relationships")
    print("⚡ 15 rounds per test, unique targets per curve+compression combo")
    if HAS_COINCURVE:
        print("🚀 Using coincurve for secp256k1 (fast), ecdsa for NIST curves")
    else:
        print("⚠️  Using ecdsa for all curves (slower)")
    print("="*80)
    
    config = SingleTargetConfig()
    all_results = []
    all_true_keys = []
    test_index = 0
    
    for curve_name, curve in CURVES_TO_TEST:
        for compressed in COMPRESSION_FORMATS:
            compression_str = "COMPRESSED" if compressed else "UNCOMPRESSED"
            print(f"\n{'='*80}")
            print(f"🧪 TESTING {curve_name} - {compression_str}")
            if curve_name == 'secp256k1' and HAS_COINCURVE:
                print("   Using fast coincurve engine")
            else:
                print("   Using ecdsa engine")
            print(f"{'='*80}")
            
            # Generate UNIQUE target and true private key for this curve+compression combo
            target_hash, true_private_key = generate_unique_target_for_curve(curve_name, curve, test_index, compressed)
            all_true_keys.append(true_private_key)
            print(f"🎯 Generated unique target: {target_hash}")
            print(f"🔑 True private key: 0x{int.from_bytes(true_private_key, 'big'):X}")
            print(f"📦 Compression format: {compression_str}")
            
            # Run GA
            engine = SingleTargetEngine(config, curve_name, curve, compressed)
            results = engine.run_optimization(target_hash)
            
            # Store elite keys for analysis
            results['elite_keys'] = engine.elite_keys
            all_results.append(results)
            
            # Show curve+compression specific results
            if 'error' not in results:
                print(f"\n📊 {curve_name} {compression_str} RESULTS:")
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
                else:
                    # ecdsa curves
                    curve_order = curve.order
                    field_prime = curve.curve.p()
                    
                key_analysis = analyze_curve_results_with_true_key(results, true_private_key, results['elite_keys'], 
                                                                 curve_order, field_prime, compressed)
                
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
                print(f"      Correct bits: {key_analysis['closest_found']['correct_bits']}/{key_analysis['closest_found']['key_size_bits']}")
                print(f"      Accuracy: {key_analysis['closest_found']['percentage_correct']:.1f}%")
                
                # 🧮 MATHEMATICAL ANALYSIS DISPLAY
                math_analysis = key_analysis['mathematical_analysis']
                
                print(f"\n   🧮 MATHEMATICAL RELATIONSHIPS:")
                print(f"      Absolute difference (best-true): {math_analysis['relationships']['absolute_differences']['best_to_true']:,}")
                print(f"      Absolute difference hex: {math_analysis['relationships']['absolute_differences']['best_to_true_hex']}")
                print(f"      Sum (best+true): {math_analysis['relationships']['sums_analysis']['best_plus_true']:,}")
                print(f"      Sum hex: {math_analysis['relationships']['sums_analysis']['best_plus_true_hex']}")
                
                # Show GCD if meaningful
                if 'gcd_analysis' in math_analysis['relationships']:
                    gcd_info = math_analysis['relationships']['gcd_analysis']
                    print(f"      Overall GCD: {gcd_info['overall_gcd']:,}")
                    print(f"      Unique pairwise GCDs: {len(gcd_info['unique_gcds'])} different values")
                
                # Show bit patterns
                bit_info = math_analysis['relationships']['bit_analysis']
                print(f"      True key bit count: {bit_info['true_key_popcount']}")
                print(f"      Best key bit count: {bit_info['best_key_popcount']}")
                print(f"      XOR pattern length: {len(bit_info['xor_pattern'])} bits")
                
                # Show SIGNIFICANT remainder patterns only
                if 'significant_patterns' in math_analysis['relationships']:
                    sig_patterns = math_analysis['relationships']['significant_patterns']
                    if sig_patterns:
                        print(f"      🎯 SIGNIFICANT REMAINDER PATTERNS:")
                        for pattern in sig_patterns[:5]:  # Top 5 most significant
                            print(f"        mod {pattern['modulus']:,}: remainder {pattern['remainder']} "
                                  f"({pattern['clustering']:.1%} of elite keys)")
                
                # Show Bitcoin-specific analysis
                if 'bitcoin_specific_analysis' in math_analysis:
                    bitcoin_info = math_analysis['bitcoin_specific_analysis']
                    interesting_btc_patterns = []
                    
                    for const_name, const_data in bitcoin_info.items():
                        if isinstance(const_data, dict):
                            # Check for interesting relationships
                            abs_diff_mod = const_data.get('abs_diff_relation', {}).get('mod', 0)
                            abs_diff_quotient = const_data.get('abs_diff_relation', {}).get('quotient', 0)
                            
                            if abs_diff_mod < 1000 or abs_diff_quotient > 0:
                                interesting_btc_patterns.append({
                                    'constant': const_name,
                                    'mod': abs_diff_mod,
                                    'quotient': abs_diff_quotient
                                })
                    
                    if interesting_btc_patterns:
                        print(f"      ₿ BITCOIN CONSTANT RELATIONSHIPS:")
                        for pattern in interesting_btc_patterns[:3]:  # Top 3
                            print(f"        {pattern['constant']}: mod={pattern['mod']}, quotient={pattern['quotient']:,}")
                
                # Show mathematical constants found
                constants_found = math_analysis.get('constants_found', {})
                if constants_found:
                    print(f"      📐 Mathematical constants detected: {len(constants_found)}")
                    # Show most significant constants (smallest relative difference)
                    sorted_constants = sorted(constants_found.items(), 
                                            key=lambda x: x[1].get('relative_difference', float('inf')))
                    for const_name, const_info in sorted_constants[:3]:  # Top 3
                        rel_diff = const_info.get('relative_difference', 0)
                        const_type = const_info.get('type', 'unknown')
                        print(f"        {const_name}: {rel_diff:.2%} difference ({const_type})")
                
                # Special sequences
                if 'special_sequences' in math_analysis.get('patterns', {}):
                    sequences = math_analysis['patterns']['special_sequences']
                    if sequences:
                        print(f"      🔢 SPECIAL SEQUENCES DETECTED:")
                        for seq_name, seq_data in sequences.items():
                            if seq_name == 'arithmetic_progression':
                                print(f"        Arithmetic: common diff = {seq_data['common_difference']:,}")
                            elif seq_name == 'geometric_progression':
                                print(f"        Geometric: ratio = {seq_data['common_ratio']:.3f}")
                            elif seq_name == 'fibonacci_like':
                                print(f"        Fibonacci-like: {seq_data['confidence']:.1%} confidence")
                
                # Variant analysis table (condensed)
                print(f"\n   📊 TOP 5 VARIANT ANALYSIS:")
                print(f"      {'Variant':<20} | {'Best 2^x':<10} | {'Avg 2^x':<10}")
                print(f"      {'-'*20}-+-{'-'*10}-+-{'-'*10}")
                
                for variant in key_analysis['variant_analysis']['variant_table'][:5]:  # Show top 5
                    best = f"2^{variant['best_distance']}"
                    avg = f"2^{variant['avg_distance']:.1f}"
                    print(f"      {variant['variant']:<20} | {best:<10} | {avg:<10}")
                
                # Store analysis in results
                results['private_key_analysis'] = key_analysis
                
            else:
                print(f"❌ Error: {results['error']}")
            
            test_index += 1
    
    # Compare results across curves and compression formats
    print(f"\n{'='*80}")
    print("🔬 CROSS-CURVE AND COMPRESSION ANALYSIS")
    print("="*80)
    
    comparison = compare_curve_results(all_results)
    
    if 'error' not in comparison:
        print(f"📊 STATISTICAL SUMMARY:")
        print(f"   Total tests: {comparison['total_tests']}")
        print(f"   Compressed tests: {comparison['compressed_tests']}")
        print(f"   Uncompressed tests: {comparison['uncompressed_tests']}")
        
        print(f"\n   Best Score Statistics:")
        print(f"      Mean: {comparison['best_score_stats']['mean']:.1f} bits")
        print(f"      StdDev: {comparison['best_score_stats']['stdev']:.1f} bits")
        print(f"      Range: {comparison['best_score_stats']['min']} - {comparison['best_score_stats']['max']} bits")
        
        # Compression format comparison
        if comparison.get('compression_comparison'):
            comp_info = comparison['compression_comparison']
            print(f"\n   📦 COMPRESSION FORMAT COMPARISON:")
            print(f"      Compressed mean: {comp_info['compressed_mean']:.1f} bits")
            print(f"      Uncompressed mean: {comp_info['uncompressed_mean']:.1f} bits")
            print(f"      Difference: {comp_info['difference']:.1f} bits")
            better_format = "COMPRESSED" if comp_info['compressed_better'] else "UNCOMPRESSED"
            print(f"      Better format: {better_format}")
        
        # Curve-specific comparison
        print(f"\n   🔄 CURVE-SPECIFIC PERFORMANCE:")
        for curve, stats in comparison['curve_comparison'].items():
            print(f"      {curve}: {stats['mean_score']:.1f} bits avg ({stats['test_count']} tests)")
            if stats['compressed_mean'] and stats['uncompressed_mean']:
                comp_diff = stats['compressed_mean'] - stats['uncompressed_mean']
                print(f"        Compressed vs Uncompressed: {comp_diff:+.1f} bits")
        
        # Add comprehensive mathematical analysis summary
        print(f"\n   🧮 MATHEMATICAL PATTERN SUMMARY:")
        math_constants_total = 0
        interesting_gcds = []
        bit_pattern_similarities = []
        
        for i, result in enumerate(all_results):
            if 'private_key_analysis' in result and 'mathematical_analysis' in result['private_key_analysis']:
                math_analysis = result['private_key_analysis']['mathematical_analysis']
                
                # Count constants found
                math_constants_total += len(math_analysis.get('constants_found', {}))
                
                # Collect GCD info
                if 'gcd_analysis' in math_analysis.get('relationships', {}):
                    gcd_info = math_analysis['relationships']['gcd_analysis']
                    if gcd_info['overall_gcd'] > 1:
                        interesting_gcds.append(gcd_info['overall_gcd'])
                
                # Collect bit patterns
                if 'bit_analysis' in math_analysis.get('relationships', {}):
                    bit_info = math_analysis['relationships']['bit_analysis']
                    bit_pattern_similarities.append(bit_info['true_key_popcount'])
        
        print(f"      Total mathematical constants detected: {math_constants_total}")
        if interesting_gcds:
            print(f"      Non-trivial GCDs found: {len(interesting_gcds)} tests")
            print(f"      Common GCD values: {list(set(interesting_gcds))}")
        
        if bit_pattern_similarities:
            avg_popcount = statistics.mean(bit_pattern_similarities)
            print(f"      Average true key bit density: {avg_popcount:.1f} bits set")
        
        if comparison['patterns']:
            print(f"\n🔍 DETECTED PATTERNS:")
            for pattern in comparison['patterns']:
                print(f"   ⚠️  {pattern}")
        else:
            print(f"\n✅ No significant universal patterns detected")
        
        # Final interpretation
        print(f"\n{'='*80}")
        print("🧪 FINAL INTERPRETATION:")
        
        if comparison.get('compression_comparison') and abs(comparison['compression_comparison']['difference']) < 2.0:
            print("🚨 COMPRESSION INSENSITIVE: GA performs nearly identically on compressed/uncompressed!")
            print("   This suggests the GA is finding fundamental private key patterns")
            print("   independent of the public key representation format!")
        
        curve_means = [stats['mean_score'] for stats in comparison['curve_comparison'].values()]
        if curve_means and statistics.stdev(curve_means) < 3.0:
            print("\n🚨 CURVE INSENSITIVE: GA shows similar performance across different curves!")
            print("   This could indicate a universal property of elliptic curve discrete logs")
            print("   or a systematic pattern that transcends curve-specific parameters!")
        
        if math_constants_total > len(all_results) * 0.5:
            print(f"\n🧮 MATHEMATICAL CONSTANTS DETECTED: Found in {math_constants_total} instances!")
            print("   This suggests the GA may be discovering relationships to fundamental")
            print("   mathematical constants like π, e, φ, etc. - highly intriguing!")
        
        print(f"\n📈 PSEUDOSCIENCE SPECULATION:")
        print("   While these patterns are fascinating to explore, remember that")
        print("   • Random data often contains apparent patterns")
        print("   • Statistical significance testing would be needed for real conclusions")
        print("   • The discrete log problem is still considered computationally hard")
        print("   • These results are for educational/entertainment purposes only!")
    
    return all_results, comparison

# Main execution
if __name__ == "__main__":
    results, comparison = run_multi_curve_compression_test()
    
    print(f"\n{'='*80}")
    print("🔬 ENHANCED TEST COMPLETE - READY FOR FURTHER ANALYSIS!")
    print("="*80)
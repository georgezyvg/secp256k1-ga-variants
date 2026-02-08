#!/usr/bin/env python3
"""
Mathematical Hash160 Adaptive GA - Universal Mathematical Relationship Exploiter
Discovers and exploits unique mathematical patterns in any hash160 target
Combines adaptive hex learning with mathematical constant relationship discovery
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

print(f"✅ Mathematical GA loaded with {CRYPTO_ENGINE} crypto engine")

# PUT YOUR TARGET HASH160 HERE (40 hex characters)
TARGET_HASH160 = "328660ef43f66abe2653fa178452a5dfc594c2a1"  # ← CHANGE THIS TO YOUR TARGET

@dataclass
class MathematicalGAConfig:
    """Enhanced config with mathematical relationship parameters"""
    # Population parameters
    K_POOL: int = 8000
    ELITE_SIZE: int = 400
    MAX_ROUNDS: int = 1000
    
    # Adaptive hex parameters (keep ALL existing goodness)
    INITIAL_ACTIVE_BYTES: int = 1
    MAX_ACTIVE_BYTES: int = 32
    EXPANSION_THRESHOLD: float = 0.05
    CONTRACTION_THRESHOLD: float = 0.1
    RANGE_ADAPTATION_FREQ: int = 2
    AGGRESSIVE_EXPANSION: bool = True
    
    # Position learning (keep ALL existing magic)
    POSITION_LEARNING_RATE: float = 0.08
    POSITION_DECAY: float = 0.98
    GLOBAL_WEIGHT_DECAY: float = 0.998
    MIN_POSITION_WEIGHT: float = 0.05
    MAX_POSITION_WEIGHT: float = 0.75
    
    # Mutation parameters (keep ALL existing power)
    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MUTATION_INCREASE: float = 1.3
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 1.2
    STAGNATION_ROUNDS: int = 4
    DIVERSITY_INJECTION_RATE: float = 0.4
    
    # ADAPTIVE FITNESS WEIGHTS - can float and learn!
    INITIAL_DECIMAL_WEIGHT: float = 0.35        # Start with decimal proximity important
    INITIAL_MATHEMATICAL_WEIGHT: float = 0.65   # Start with math relationships primary
    
    # Adaptive fitness learning
    FITNESS_ADAPTATION: bool = True             # Learn optimal weights during run
    WEIGHT_LEARNING_RATE: float = 0.02         # How fast to adapt fitness weights
    MIN_WEIGHT: float = 0.05                   # Minimum weight for any component
    MAX_WEIGHT: float = 0.95                   # Maximum weight for any component
    
    # Mathematical relationship parameters
    MATH_ACCURACY_THRESHOLD: float = 0.90      # Minimum accuracy to consider "mathematical"
    MATH_LEARNING_RATE: float = 0.1            # How fast to learn mathematical patterns
    PATTERN_RETENTION: int = 50                # Keep best N mathematical patterns
    
    # Mathematical constants to test
    MATHEMATICAL_CONSTANTS: Dict[str, float] = None
    
    # Enhanced features
    CROSS_SPACE_ANALYSIS: bool = True          # Analyze private key vs hash160 relationships
    CHECK_BOTH_FORMATS: bool = True            # Check compressed AND uncompressed
    
    # Micro-refinement parameters
    ENABLE_MICRO_REFINEMENT: bool = True       # Enable micro-refinement for near-perfect solutions
    MICRO_REFINEMENT_THRESHOLD: float = 0.001  # Trigger micro-refinement at 99.9% accuracy
    HIGH_PRECISION_MODE: bool = True           # Use high-precision mathematical constants
    
    DETAILED_LOGGING: bool = True

    def __post_init__(self):
        if self.MATHEMATICAL_CONSTANTS is None:
            self.MATHEMATICAL_CONSTANTS = {
                'pi': math.pi,
                'e': math.e,
                'phi': (1 + math.sqrt(5)) / 2,
                'sqrt2': math.sqrt(2),
                'sqrt3': math.sqrt(3),
                'sqrt5': math.sqrt(5),
                'ln2': math.log(2),
                'ln10': math.log(10),
                'gamma': 0.5772156649015329,
                'catalan': 0.9159655941772190,
                'euler_mascheroni': 0.5772156649015329,
                'apery': 1.2020569031595942,
                'khinchin': 2.6854520010653062,
                'glaisher': 1.2824271291006226,
            }

class MathematicalRelationshipDetector:
    """Detects and tracks mathematical relationships for any hash160 target"""
    
    def __init__(self, target_hash160_int: int, config: MathematicalGAConfig):
        self.target_hash160_int = target_hash160_int
        self.config = config
        self.constants = config.MATHEMATICAL_CONSTANTS.copy()
        
        # Discovered patterns for this specific target
        self.discovered_patterns = []
        self.pattern_performance = {}
        
        # Learning statistics
        self.relationship_stats = {const: {'hits': 0, 'accuracy_sum': 0.0} 
                                 for const in self.constants.keys()}
        
        # Dynamic power ranges (learned from data)
        self.effective_power_ranges = {
            'hash160_multiply': range(0, 8),   # For hash160 * constant * 2^N relationships
            'hash160_divide': range(0, 8),     # For hash160 / (constant * 2^N) relationships
            'key_cross': range(20, 80),        # For cross-space private key relationships
            'decimal_proximity': range(0, 4),  # For decimal difference relationships
        }
        
        self.lock = threading.RLock()
        
        print(f"🧮 Mathematical detector initialized for target: {target_hash160_int}")
        print(f"🧮 Testing {len(self.constants)} mathematical constants")

    def analyze_mathematical_relationships(self, candidate_hash160_int: int, 
                                        candidate_private_key_int: int = None) -> Dict:
        """Universal mathematical relationship analysis for any hash160"""
        
        if candidate_hash160_int == 0 or self.target_hash160_int == 0:
            return {'max_accuracy': 0.0, 'best_pattern': None, 'relationships': []}
        
        relationships = []
        max_accuracy = 0.0
        best_pattern = None
        
        with self.lock:
            # 1. DIRECT HASH160 RELATIONSHIPS
            ratio = candidate_hash160_int / self.target_hash160_int
            inverse_ratio = self.target_hash160_int / candidate_hash160_int
            
            for const_name, const_val in self.constants.items():
                # Test multiply relationships: candidate ≈ target * constant * 2^N
                for power in self.effective_power_ranges['hash160_multiply']:
                    expected_ratio = const_val * (2 ** power)
                    if expected_ratio > 0:
                        accuracy = self._calculate_accuracy(ratio, expected_ratio)
                        if accuracy > max_accuracy:
                            max_accuracy = accuracy
                            best_pattern = f"hash160: {const_name} * 2^{power}"
                        
                        relationships.append({
                            'type': 'hash160_multiply',
                            'constant': const_name,
                            'power': power,
                            'accuracy': accuracy,
                            'expected_ratio': expected_ratio,
                            'actual_ratio': ratio
                        })
                
                # Test divide relationships: candidate ≈ target / (constant * 2^N)
                for power in self.effective_power_ranges['hash160_divide']:
                    if power > 0:
                        expected_ratio = 1.0 / (const_val * (2 ** power))
                        if expected_ratio > 0:
                            accuracy = self._calculate_accuracy(ratio, expected_ratio)
                            if accuracy > max_accuracy:
                                max_accuracy = accuracy
                                best_pattern = f"hash160: 1/({const_name} * 2^{power})"
                            
                            relationships.append({
                                'type': 'hash160_divide',
                                'constant': const_name,
                                'power': power,
                                'accuracy': accuracy,
                                'expected_ratio': expected_ratio,
                                'actual_ratio': ratio
                            })
                
                # Test inverse relationships: target ≈ candidate * constant * 2^N
                for power in self.effective_power_ranges['hash160_multiply']:
                    expected_inverse = const_val * (2 ** power)
                    if expected_inverse > 0:
                        accuracy = self._calculate_accuracy(inverse_ratio, expected_inverse)
                        if accuracy > max_accuracy:
                            max_accuracy = accuracy
                            best_pattern = f"hash160_inv: {const_name} * 2^{power}"
                        
                        relationships.append({
                            'type': 'hash160_inverse',
                            'constant': const_name,
                            'power': power,
                            'accuracy': accuracy,
                            'expected_ratio': expected_inverse,
                            'actual_ratio': inverse_ratio
                        })
            
            # 2. DECIMAL DIFFERENCE RELATIONSHIPS
            decimal_diff = abs(candidate_hash160_int - self.target_hash160_int)
            if decimal_diff > 0:
                for const_name, const_val in self.constants.items():
                    for power in self.effective_power_ranges['decimal_proximity']:
                        expected_diff = int(const_val * (2 ** power))
                        if expected_diff > 0:
                            accuracy = self._calculate_accuracy(decimal_diff, expected_diff)
                            if accuracy > max_accuracy:
                                max_accuracy = accuracy
                                best_pattern = f"decimal_diff: {const_name} * 2^{power}"
                            
                            relationships.append({
                                'type': 'decimal_difference',
                                'constant': const_name,
                                'power': power,
                                'accuracy': accuracy,
                                'expected_value': expected_diff,
                                'actual_value': decimal_diff
                            })
            
            # 3. CROSS-SPACE RELATIONSHIPS (private key vs target hash160)
            if candidate_private_key_int and self.config.CROSS_SPACE_ANALYSIS:
                cross_ratio = candidate_private_key_int / self.target_hash160_int
                
                for const_name, const_val in self.constants.items():
                    for power in self.effective_power_ranges['key_cross']:
                        expected_cross_ratio = const_val * (2 ** power)
                        if expected_cross_ratio > 0:
                            accuracy = self._calculate_accuracy(cross_ratio, expected_cross_ratio)
                            if accuracy > max_accuracy:
                                max_accuracy = accuracy
                                best_pattern = f"cross: privkey/hash160 ≈ {const_name} * 2^{power}"
                            
                            relationships.append({
                                'type': 'cross_space',
                                'constant': const_name,
                                'power': power,
                                'accuracy': accuracy,
                                'expected_ratio': expected_cross_ratio,
                                'actual_ratio': cross_ratio
                            })
            
            # 4. SIMPLE RATIO RELATIONSHIPS
            simple_ratios = [0.5, 1.5, 2.0, 3.0, 4.0, 5.0, 0.25, 0.75, 1.25, 
                           0.1, 0.2, 0.3, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2, 1.3, 1.4]
            
            for simple_ratio in simple_ratios:
                accuracy = self._calculate_accuracy(ratio, simple_ratio)
                if accuracy > max_accuracy:
                    max_accuracy = accuracy
                    best_pattern = f"simple: {simple_ratio:.2f} * target"
                
                relationships.append({
                    'type': 'simple_ratio',
                    'ratio': simple_ratio,
                    'accuracy': accuracy,
                    'expected_ratio': simple_ratio,
                    'actual_ratio': ratio
                })
            
            # Update learning statistics
            if max_accuracy > self.config.MATH_ACCURACY_THRESHOLD:
                self._learn_from_relationship(best_pattern, max_accuracy)
        
        return {
            'max_accuracy': max_accuracy,
            'best_pattern': best_pattern,
            'relationships': relationships,
            'total_relationships': len(relationships)
        }

    def _calculate_accuracy(self, actual: float, expected: float) -> float:
        """Calculate mathematical accuracy between actual and expected values"""
        if expected == 0 or actual == 0:
            return 0.0
        
        error = abs(actual - expected) / expected
        accuracy = max(0.0, 1.0 - error)
        return accuracy

    def _learn_from_relationship(self, pattern: str, accuracy: float):
        """Learn from discovered mathematical relationships"""
        # Extract constant name from pattern
        for const_name in self.constants.keys():
            if const_name in pattern:
                self.relationship_stats[const_name]['hits'] += 1
                self.relationship_stats[const_name]['accuracy_sum'] += accuracy
                
                # Adapt power ranges based on discoveries
                if 'cross:' in pattern and accuracy > 0.95:
                    # Extend cross-space power range if high accuracy found
                    current_max = max(self.effective_power_ranges['key_cross'])
                    if current_max < 100:
                        self.effective_power_ranges['key_cross'] = range(
                            min(self.effective_power_ranges['key_cross']), 
                            current_max + 10
                        )
                break
        
        # Store high-accuracy patterns
        if accuracy > self.config.MATH_ACCURACY_THRESHOLD:
            self.discovered_patterns.append({
                'pattern': pattern,
                'accuracy': accuracy,
                'discovery_time': time.time()
            })
            
            # Keep only best patterns
            self.discovered_patterns.sort(key=lambda x: x['accuracy'], reverse=True)
            if len(self.discovered_patterns) > self.config.PATTERN_RETENTION:
                self.discovered_patterns = self.discovered_patterns[:self.config.PATTERN_RETENTION]

    def get_mathematical_guidance(self) -> Dict:
        """Get guidance for generating mathematically-informed candidates"""
        with self.lock:
            guidance = {
                'best_constants': [],
                'effective_powers': {},
                'discovered_patterns': self.discovered_patterns.copy()
            }
            
            # Identify best-performing constants
            for const_name, stats in self.relationship_stats.items():
                if stats['hits'] > 0:
                    avg_accuracy = stats['accuracy_sum'] / stats['hits']
                    guidance['best_constants'].append({
                        'constant': const_name,
                        'avg_accuracy': avg_accuracy,
                        'hits': stats['hits'],
                        'value': self.constants[const_name]
                    })
            
            guidance['best_constants'].sort(key=lambda x: x['avg_accuracy'], reverse=True)
            guidance['effective_powers'] = self.effective_power_ranges.copy()
            
            return guidance

class EnhancedAdaptiveHexManager:
    """Enhanced hex manager with mathematical relationship integration"""
    
    def __init__(self, config: MathematicalGAConfig, math_detector: MathematicalRelationshipDetector):
        self.config = config
        self.math_detector = math_detector
        
        # Keep all existing adaptive hex functionality
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.max_tested_bytes = config.INITIAL_ACTIVE_BYTES
        self.position_weights = np.ones(32, dtype=np.float32)
        self.position_usage_stats = np.zeros(32, dtype=np.float32)
        self.position_performance = np.zeros(32, dtype=np.float32)
        self.range_performance = {}
        self.generation_count = 0
        self.learning_history = []
        
        # NEW: Mathematical generation patterns
        self.mathematical_generation_patterns = []
        self.pattern_success_rate = {}
        
        self.lock = threading.RLock()
        
        print(f"🧠 Enhanced adaptive hex manager with mathematical integration")

    def generate_mathematically_informed_key(self) -> bytes:
        """Generate keys using mathematical insights + adaptive hex learning"""
        with self.lock:
            self.generation_count += 1
            
            # Get mathematical guidance
            guidance = self.math_detector.get_mathematical_guidance()
            
            # 60% mathematical guidance, 40% adaptive hex
            if random.random() < 0.6 and guidance['best_constants']:
                return self._generate_mathematical_candidate(guidance)
            else:
                return self._generate_adaptive_hex_candidate()

    def _generate_mathematical_candidate(self, guidance: Dict) -> bytes:
        """Generate candidate based on discovered mathematical relationships"""
        target_int = self.math_detector.target_hash160_int
        
        # Use best performing constants
        if guidance['best_constants']:
            const_info = random.choice(guidance['best_constants'][:5])  # Top 5 constants
            const_val = const_info['value']
            const_name = const_info['constant']
            
            # Generate target hash160 values that would create mathematical relationships
            generation_strategies = []
            
            # Strategy 1: Direct multiplication
            for power in guidance['effective_powers'].get('hash160_multiply', range(0, 8)):
                target_candidate_hash160 = int(target_int * const_val * (2 ** power))
                if target_candidate_hash160 > 0:
                    generation_strategies.append(('multiply', target_candidate_hash160, power))
            
            # Strategy 2: Division
            for power in guidance['effective_powers'].get('hash160_divide', range(1, 8)):
                target_candidate_hash160 = int(target_int / (const_val * (2 ** power)))
                if target_candidate_hash160 > 0:
                    generation_strategies.append(('divide', target_candidate_hash160, power))
            
            # Strategy 3: Decimal difference
            for power in guidance['effective_powers'].get('decimal_proximity', range(0, 4)):
                diff = int(const_val * (2 ** power))
                target_candidate_hash160 = target_int + random.choice([-diff, diff])
                if target_candidate_hash160 > 0:
                    generation_strategies.append(('decimal', target_candidate_hash160, power))
            
            if generation_strategies:
                strategy, target_hash160, power = random.choice(generation_strategies)
                
                # Now we need to find a private key that might produce this hash160
                # This is the hard part - we can't directly invert, so we use guided search
                return self._search_for_hash160_target(target_hash160)
        
        # Fallback to adaptive hex
        return self._generate_adaptive_hex_candidate()

    def _search_for_hash160_target(self, target_hash160_int: int) -> bytes:
        """Search for private key that might produce target hash160 using mathematical guidance"""
        # This is still probabilistic, but we can use mathematical relationships
        # to guide the search in the private key space
        
        # Convert target hash160 back to potential private key ranges using cross-space relationships
        guidance = self.math_detector.get_mathematical_guidance()
        
        for const_info in guidance['best_constants'][:3]:
            const_val = const_info['value']
            
            # Try cross-space relationships: privkey ≈ hash160 * constant * 2^N
            for power in range(20, 60):  # Reasonable power range for cross-space
                potential_key_int = int(target_hash160_int * const_val * (2 ** power))
                if 1 <= potential_key_int <= 2**256:
                    # Add some variation around this mathematical target
                    variation = random.randint(-1000000, 1000000)
                    final_key_int = max(1, min(potential_key_int + variation, 2**256 - 1))
                    return final_key_int.to_bytes(32, 'big')
        
        # Fallback: use adaptive hex approach
        return self._generate_adaptive_hex_candidate()

    def _generate_adaptive_hex_candidate(self) -> bytes:
        """Original adaptive hex generation (keep all existing logic)"""
        max_value = self.get_active_range()
        
        if random.random() < 0.8:
            key_value = self._generate_position_focused_key(max_value)
        else:
            key_value = self._generate_exploratory_key(max_value)
        
        return key_value.to_bytes(32, 'big')

    # Keep all existing methods from the original AdaptiveHexManager
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

    def _generate_position_focused_key(self, max_value: int) -> int:
        """Keep existing position-focused generation"""
        key_bytes = [0] * 32
        
        for byte_pos in range(min(self.current_active_bytes, 32)):
            weight = self.position_weights[byte_pos]
            
            if random.random() < min(0.9, weight + 0.2):
                if random.random() < 0.4:
                    key_bytes[byte_pos] = random.randint(0, 255)
                else:
                    if random.random() < 0.5:
                        patterns = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF]
                        key_bytes[byte_pos] = random.choice(patterns)
                    else:
                        key_bytes[byte_pos] = random.randint(1, 255)
        
        key_value = 0
        for i, byte_val in enumerate(key_bytes[:self.current_active_bytes]):
            key_value += byte_val * (256 ** i)
        
        return max(1, min(key_value, max_value))

    def _generate_exploratory_key(self, max_value: int) -> int:
        """Keep existing exploratory generation"""
        exploration_patterns = [
            lambda: random.randint(1, max_value),
            lambda: random.randint(max_value // 2, max_value),
            lambda: random.randint(max_value // 4, max_value // 2),
            lambda: random.randint(1, max_value // 10),
            lambda: int(max_value * (random.random() ** 0.5)),
            lambda: int(max_value * random.random()),
        ]
        
        pattern_func = random.choice(exploration_patterns)
        try:
            return max(1, min(pattern_func(), max_value))
        except:
            return random.randint(1, max_value)

    # Keep all other existing methods...
    def learn_from_mutation(self, old_key: bytes, new_key: bytes, improvement: float):
        """Enhanced learning that includes mathematical insights"""
        if improvement <= 0:
            return
        
        # Keep existing position learning
        with self.lock:
            for byte_pos in range(min(self.current_active_bytes, 32)):
                if byte_pos < len(old_key) and byte_pos < len(new_key):
                    old_byte = old_key[byte_pos]
                    new_byte = new_key[byte_pos]
                    
                    if old_byte != new_byte:
                        learning_factor = improvement * self.config.POSITION_LEARNING_RATE
                        old_weight = self.position_weights[byte_pos]
                        new_weight = min(self.config.MAX_POSITION_WEIGHT, old_weight + learning_factor)
                        self.position_weights[byte_pos] = new_weight
                        self.position_performance[byte_pos] += improvement
                        self.position_usage_stats[byte_pos] += 1

            # Keep existing learning history
            self.learning_history.append({
                'generation': self.generation_count,
                'improvement': improvement,
                'active_bytes': self.current_active_bytes,
                'position_weights': self.position_weights.copy(),
                'old_key_int': int.from_bytes(old_key, 'big'),
                'new_key_int': int.from_bytes(new_key, 'big')
            })

            # Decay unused positions
            for byte_pos in range(32):
                if byte_pos >= self.current_active_bytes:
                    self.position_weights[byte_pos] *= self.config.POSITION_DECAY
                    self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                        self.position_weights[byte_pos])

    # Keep all other existing methods unchanged...
    def apply_global_weight_decay(self):
        """Keep existing global weight decay"""
        with self.lock:
            for byte_pos in range(32):
                self.position_weights[byte_pos] *= self.config.GLOBAL_WEIGHT_DECAY
                self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                    self.position_weights[byte_pos])

    def reset_position_weights(self):
        """Keep existing weight reset"""
        with self.lock:
            self.position_weights = np.full(32, 0.3, dtype=np.float32)
            print(f"        🔄 Position weights reset to 0.3 for exploration")

    def analyze_population_ranges(self, population: List[bytes], scores: List[float]):
        """Enhanced range analysis for mathematical fitness scores"""
        if not population:
            return
        
        with self.lock:
            range_improvements = {}
            
            for key, score in zip(population, scores):
                # Convert mathematical fitness score to improvement metric
                # Lower score = better, so improvement = 1.0 - score
                if score >= 1.0:  # Worst possible mathematical fitness
                    continue
                
                effective_bytes = 1
                key_int = int.from_bytes(key, 'big')
                if key_int > 0:
                    effective_bytes = (key_int.bit_length() + 7) // 8
                
                effective_bytes = max(1, min(effective_bytes, 32))
                improvement = 1.0 - score  # Higher is better (mathematical accuracy)
                
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
                    
                    if len(self.range_performance[byte_range]) > 10:
                        self.range_performance[byte_range] = self.range_performance[byte_range][-10:]

    def adapt_active_range(self, round_num: int, elite_scores: List[float]):
        """Keep existing adaptive range logic"""
        if round_num % self.config.RANGE_ADAPTATION_FREQ != 0:
            return
        
        with self.lock:
            old_range = self.current_active_bytes
            
            if len(self.range_performance) >= 2:
                current_avg_perf = 0
                if self.current_active_bytes in self.range_performance:
                    recent_perfs = self.range_performance[self.current_active_bytes]
                    current_avg_perf = statistics.mean(recent_perfs) if recent_perfs else 0
                
                larger_ranges = [r for r in self.range_performance.keys()
                               if r > self.current_active_bytes]
                best_larger_perf = 0
                if larger_ranges:
                    larger_perfs = []
                    for r in larger_ranges:
                        if self.range_performance[r]:
                            larger_perfs.extend(self.range_performance[r])
                    if larger_perfs:
                        best_larger_perf = max(larger_perfs)
                
                smaller_ranges = [r for r in self.range_performance.keys()
                                if r < self.current_active_bytes and r >= 1]
                best_smaller_perf = 0
                if smaller_ranges:
                    smaller_perfs = []
                    for r in smaller_ranges:
                        if self.range_performance[r]:
                            smaller_perfs.extend(self.range_performance[r])
                    if smaller_perfs:
                        best_smaller_perf = max(smaller_perfs)
                
                if (best_larger_perf > current_avg_perf and
                    best_larger_perf > best_smaller_perf and
                    self.current_active_bytes < self.config.MAX_ACTIVE_BYTES):
                    self.current_active_bytes = min(self.current_active_bytes + 1,
                                                  self.config.MAX_ACTIVE_BYTES)
                    print(f"    🔧 EXPANDING hex range: {old_range} → {self.current_active_bytes} bytes")
                
                elif (best_smaller_perf > current_avg_perf and
                      best_smaller_perf > best_larger_perf and
                      self.current_active_bytes > 1):
                    self.current_active_bytes = max(1, self.current_active_bytes - 1)
                    print(f"    🔧 CONTRACTING hex range: {old_range} → {self.current_active_bytes} bytes")

    def get_detailed_stats(self) -> dict:
        """Enhanced stats including mathematical insights"""
        with self.lock:
            # Keep all existing stats
            active_positions = np.sum(self.position_weights[:self.current_active_bytes] > 0.5)
            highly_active_positions = np.sum(self.position_weights[:self.current_active_bytes] > 0.8)
            avg_position_weight = np.mean(self.position_weights[:self.current_active_bytes])
            
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
            
            # Add mathematical insights
            math_guidance = self.math_detector.get_mathematical_guidance()
            
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
                'learning_events': len(self.learning_history),
                # NEW: Mathematical insights
                'mathematical_patterns_discovered': len(math_guidance['discovered_patterns']),
                'best_mathematical_constants': [c['constant'] for c in math_guidance['best_constants'][:5]],
                'mathematical_generation_rate': len(self.mathematical_generation_patterns)
            }

class MathematicalAtomics:
    """Enhanced atomics with mathematical fitness tracking"""
    def __init__(self, config: MathematicalGAConfig):
        self.config = config
        # Keep all existing atomics
        self.global_best_score = Value('f', 1000.0, lock=True)  # Changed to float for enhanced scoring
        self.global_improvements = Value('L', 0, lock=True)
        self.global_evaluations = Value('L', 0, lock=True)
        self.best_key_bytes = Array('B', 32, lock=True)
        self.mutation_strength = Value('f', config.MUTATION_STRENGTH, lock=True)
        self.last_improvement_round = Value('i', 0, lock=True)
        self.start_time = Value('d', 0.0, lock=True)
        
        # NEW: Mathematical fitness tracking
        self.best_mathematical_accuracy = Value('f', 0.0, lock=True)
        self.mathematical_discoveries = Value('L', 0, lock=True)

    def try_update_global_best(self, new_score: float, new_key: bytes, 
                              mathematical_accuracy: float = 0.0) -> bool:
        """Enhanced global best tracking with mathematical accuracy"""
        improved = False
        
        with self.global_best_score.get_lock():
            current_best = self.global_best_score.value
            if new_score < current_best:
                self.global_best_score.value = new_score
                improved = True
                
                with self.global_improvements.get_lock():
                    self.global_improvements.value += 1
                
                with self.best_key_bytes.get_lock():
                    for i, byte_val in enumerate(new_key[:32]):
                        self.best_key_bytes[i] = byte_val
        
        # Track mathematical accuracy improvements separately
        if mathematical_accuracy > 0.95:  # High mathematical accuracy
            with self.best_mathematical_accuracy.get_lock():
                if mathematical_accuracy > self.best_mathematical_accuracy.value:
                    self.best_mathematical_accuracy.value = mathematical_accuracy
                    with self.mathematical_discoveries.get_lock():
                        self.mathematical_discoveries.value += 1
        
        return improved

    def atomic_get_all_stats(self) -> dict:
        """Enhanced stats with mathematical tracking"""
        with self.global_best_score.get_lock():
            best_score = self.global_best_score.value
        with self.global_improvements.get_lock():
            improvements = self.global_improvements.value
        with self.global_evaluations.get_lock():
            evaluations = self.global_evaluations.value
        with self.mutation_strength.get_lock():
            mutation_strength = self.mutation_strength.value
        with self.best_mathematical_accuracy.get_lock():
            math_accuracy = self.best_mathematical_accuracy.value
        with self.mathematical_discoveries.get_lock():
            math_discoveries = self.mathematical_discoveries.value
        
        return {
            'best_score': best_score,
            'improvements': improvements,
            'evaluations': evaluations,
            'mutation_strength': mutation_strength,
            'best_mathematical_accuracy': math_accuracy,
            'mathematical_discoveries': math_discoveries
        }

    # Keep all other existing atomic methods...
    def atomic_increment_evals(self, count: int = 1) -> int:
        with self.global_evaluations.get_lock():
            old_val = self.global_evaluations.value
            self.global_evaluations.value = old_val + count
            return self.global_evaluations.value

    def get_best_key(self) -> bytes:
        with self.best_key_bytes.get_lock():
            return bytes(self.best_key_bytes[:32])

    def atomic_update_mutation_strength(self, multiplier: float) -> float:
        with self.mutation_strength.get_lock():
            old_value = self.mutation_strength.value
            new_value = old_value * multiplier
            new_value = max(self.config.MUTATION_MIN, min(self.config.MUTATION_MAX, new_value))
            self.mutation_strength.value = new_value
            return new_value

class CryptoOps:
    """Enhanced crypto operations supporting both compressed and uncompressed formats"""
    def __init__(self):
        self.engine = CRYPTO_ENGINE

    def scalar_mult_secp256k1(self, private_key: bytes, compressed: bool = True) -> bytes:
        """Generate public key in compressed or uncompressed format"""
        if len(private_key) != 32:
            raise ValueError("Private key must be 32 bytes")

        try:
            if self.engine == 'coincurve':
                privkey = coincurve.PrivateKey(private_key)
                return privkey.public_key.format(compressed=compressed)
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
                
                if compressed:
                    prefix = 0x02 if (y % 2 == 0) else 0x03
                    x_bytes = x.to_bytes(32, 'big')
                    return bytes([prefix]) + x_bytes
                else:
                    # Uncompressed format: 0x04 + x + y
                    x_bytes = x.to_bytes(32, 'big')
                    y_bytes = y.to_bytes(32, 'big')
                    return bytes([0x04]) + x_bytes + y_bytes
        except Exception:
            if compressed:
                return b'\x02' + b'\x00' * 32
            else:
                return b'\x04' + b'\x00' * 64

    def hash160(self, data: bytes) -> bytes:
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()

    def private_key_to_hash160_both(self, private_key: bytes) -> tuple:
        """Return both compressed and uncompressed hash160s"""
        try:
            # Compressed hash160
            pubkey_compressed = self.scalar_mult_secp256k1(private_key, compressed=True)
            hash160_compressed = self.hash160(pubkey_compressed)
            
            # Uncompressed hash160  
            pubkey_uncompressed = self.scalar_mult_secp256k1(private_key, compressed=False)
            hash160_uncompressed = self.hash160(pubkey_uncompressed)
            
            return hash160_compressed, hash160_uncompressed
        except Exception:
            # Return dummy values on error
            dummy = b'\x00' * 20
            return dummy, dummy

    def private_key_to_hash160(self, private_key: bytes) -> bytes:
        """Default to compressed for backward compatibility"""
        hash160_compressed, _ = self.private_key_to_hash160_both(private_key)
        return hash160_compressed

def hamming_distance_160(h1: bytes, h2: bytes) -> int:
    """Keep existing hamming distance"""
    if len(h1) != 20 or len(h2) != 20:
        return 160
    distance = 0
    for i in range(20):
        xor_byte = h1[i] ^ h2[i]
        distance += bin(xor_byte).count('1')
    return distance

class AdaptiveFitnessManager:
    """Learns optimal fitness weights during the run - keeps the adaptive magic!"""
    
    def __init__(self, config: MathematicalGAConfig):
        self.config = config
        
        # Current adaptive weights (start with config defaults)
        self.decimal_weight = config.INITIAL_DECIMAL_WEIGHT
        self.mathematical_weight = config.INITIAL_MATHEMATICAL_WEIGHT
        
        # Performance tracking for each component
        self.decimal_performance_history = deque(maxlen=100)
        self.mathematical_performance_history = deque(maxlen=100)
        
        # Learning statistics
        self.weight_adjustment_count = 0
        self.best_combination_seen = None
        self.improvement_attribution = {'decimal': 0, 'mathematical': 0}
        
        self.lock = threading.RLock()
        
        print(f"🎯 Adaptive fitness manager initialized")
        print(f"🎯 Starting weights: Decimal={self.decimal_weight:.3f}, Math={self.mathematical_weight:.3f}")

    def get_current_weights(self) -> tuple:
        """Get current adaptive weights"""
        with self.lock:
            # Ensure weights sum to 1.0
            total = self.decimal_weight + self.mathematical_weight
            if total > 0:
                decimal_norm = self.decimal_weight / total
                math_norm = self.mathematical_weight / total
            else:
                decimal_norm = 0.5
                math_norm = 0.5
            
            return decimal_norm, math_norm

    def learn_from_improvement(self, improvement_details: dict):
        """Learn which fitness components are driving improvements - KEEP THE MAGIC!"""
        if not improvement_details or improvement_details.get('improvement', 0) <= 0:
            return
        
        with self.lock:
            improvement_size = improvement_details['improvement']
            decimal_contrib = improvement_details.get('decimal_contribution', 0.0)
            math_contrib = improvement_details.get('mathematical_contribution', 0.0)
            
            # Track which component is contributing more to improvements
            if decimal_contrib > math_contrib:
                self.improvement_attribution['decimal'] += improvement_size
                # Slightly increase decimal weight if it's driving improvements
                if self.config.FITNESS_ADAPTATION:
                    self.decimal_weight = min(self.config.MAX_WEIGHT, 
                                            self.decimal_weight + self.config.WEIGHT_LEARNING_RATE * improvement_size)
                    self.mathematical_weight = max(self.config.MIN_WEIGHT,
                                                 self.mathematical_weight - self.config.WEIGHT_LEARNING_RATE * improvement_size * 0.5)
            
            elif math_contrib > decimal_contrib:
                self.improvement_attribution['mathematical'] += improvement_size
                # Slightly increase mathematical weight if it's driving improvements
                if self.config.FITNESS_ADAPTATION:
                    self.mathematical_weight = min(self.config.MAX_WEIGHT,
                                                 self.mathematical_weight + self.config.WEIGHT_LEARNING_RATE * improvement_size)
                    self.decimal_weight = max(self.config.MIN_WEIGHT,
                                            self.decimal_weight - self.config.WEIGHT_LEARNING_RATE * improvement_size * 0.5)
            
            # Track performance history
            self.decimal_performance_history.append(decimal_contrib)
            self.mathematical_performance_history.append(math_contrib)
            self.weight_adjustment_count += 1
            
            if self.config.DETAILED_LOGGING and self.weight_adjustment_count % 50 == 0:
                decimal_w, math_w = self.get_current_weights()
                print(f"        🎯 Fitness weights adapted: Decimal={decimal_w:.3f}, Math={math_w:.3f}")

    def analyze_component_performance(self) -> dict:
        """Analyze which components are performing well"""
        with self.lock:
            analysis = {}
            
            if self.decimal_performance_history:
                analysis['decimal_avg'] = statistics.mean(self.decimal_performance_history)
                analysis['decimal_trend'] = 'improving' if len(self.decimal_performance_history) > 10 and \
                    statistics.mean(list(self.decimal_performance_history)[-10:]) > \
                    statistics.mean(list(self.decimal_performance_history)[:10]) else 'stable'
            else:
                analysis['decimal_avg'] = 0.0
                analysis['decimal_trend'] = 'unknown'
            
            if self.mathematical_performance_history:
                analysis['mathematical_avg'] = statistics.mean(self.mathematical_performance_history)
                analysis['mathematical_trend'] = 'improving' if len(self.mathematical_performance_history) > 10 and \
                    statistics.mean(list(self.mathematical_performance_history)[-10:]) > \
                    statistics.mean(list(self.mathematical_performance_history)[:10]) else 'stable'
            else:
                analysis['mathematical_avg'] = 0.0
                analysis['mathematical_trend'] = 'unknown'
            
            analysis['current_weights'] = self.get_current_weights()
            analysis['adjustments_made'] = self.weight_adjustment_count
            analysis['improvement_attribution'] = self.improvement_attribution.copy()
            
            return analysis

    def reset_if_stagnant(self):
        """Reset weights if performance stagnates - part of the adaptive magic"""
        with self.lock:
            if len(self.decimal_performance_history) > 50 and len(self.mathematical_performance_history) > 50:
                recent_decimal = statistics.mean(list(self.decimal_performance_history)[-20:])
                recent_math = statistics.mean(list(self.mathematical_performance_history)[-20:])
                
                # If both components are performing poorly, reset to balanced weights
                if recent_decimal < 0.01 and recent_math < 0.01:
                    self.decimal_weight = self.config.INITIAL_DECIMAL_WEIGHT
                    self.mathematical_weight = self.config.INITIAL_MATHEMATICAL_WEIGHT
                    print(f"        🔄 Fitness weights reset due to stagnation")

class MicroPrecisionRefiner:
    """Micro-precision refinement for when we're 99.99%+ there"""
    
    def __init__(self, crypto: CryptoOps, math_detector: MathematicalRelationshipDetector, target_hash: bytes):
        self.crypto = crypto
        self.math_detector = math_detector
        self.target_hash = target_hash
        
        # High precision mathematical constants
        self.high_precision_constants = {
            'pi': 3.141592653589793238462643383279502884197169399375105820974944592307816406286,
            'e': 2.718281828459045235360287471352662497757247093699959574966967627724076630353,
            'phi': 1.618033988749894848204586834365638117720309179805762862135448622705260462818,
            'sqrt2': 1.414213562373095048801688724209698078569671875376948073176679737990732478462,
            'sqrt3': 1.732050807568877293527446341505872366942805253810380628055806979451933016908,
            'sqrt5': 2.236067977499789696409173668731276235440618359611525724270897245410520925637,
            'ln2': 0.693147180559945309417232121458176568075500134360255254120680009493393621969,
            'ln10': 2.302585092994045684017991454684364207601101488628772976033327900967572609677,
            'gamma': 0.577215664901532860606512090082402431042159335939923598805767234884867726777,
            'catalan': 0.915965594177219015054603514932384110774149374281672134266498119621763019776,
            'apery': 1.202056903159594285399738161511449990764986292340498881792271555341838205786,
            'khinchin': 2.685452010653062236019854011633525549737170943527491351577180354438026690717,
            'glaisher': 1.282427129100622636875342568869791727767688927325001192063740021740406308690,
        }
        
        print(f"🔬 Micro-precision refiner initialized for 99.99%+ solutions")

    def micro_refine_around_best(self, best_private_key: bytes, current_score: float) -> tuple:
        """Micro-refinement around the best candidate"""
        print(f"\n🔬 MICRO-PRECISION REFINEMENT MODE")
        print(f"🎯 Current best score: {current_score:.8f}")
        print(f"🔑 Refining around: 0x{int.from_bytes(best_private_key, 'big'):X}")
        
        best_key_int = int.from_bytes(best_private_key, 'big')
        best_score = current_score
        best_candidate = best_private_key
        best_details = None
        
        # Strategy 1: Direct micro-adjustments
        print(f"🔍 Strategy 1: Direct micro-adjustments...")
        micro_deltas = [-1000, -100, -10, -5, -2, -1, 1, 2, 5, 10, 100, 1000]
        
        for delta in micro_deltas:
            test_key_int = max(1, best_key_int + delta)
            test_key = test_key_int.to_bytes(32, 'big')
            
            score, details = self._test_key_precision(test_key)
            if score < best_score:
                best_score = score
                best_candidate = test_key
                best_details = details
                print(f"   🎯 Improvement: {score:.8f} (delta: {delta})")
                
                if score == 0.0:
                    print(f"   🎉 PERFECT MATCH FOUND!")
                    return best_candidate, best_details
        
        # Strategy 2: Mathematical relationship micro-adjustments
        print(f"🔍 Strategy 2: Mathematical relationship refinement...")
        
        # Get the best mathematical pattern from current best
        hash160_comp, hash160_uncomp = self.crypto.private_key_to_hash160_both(best_private_key)
        target_int = int.from_bytes(self.target_hash, 'big')
        
        # Test both formats
        for format_name, hash160 in [("compressed", hash160_comp), ("uncompressed", hash160_uncomp)]:
            candidate_int = int.from_bytes(hash160, 'big')
            
            # Find the mathematical relationship
            for const_name, const_val in self.high_precision_constants.items():
                for power in range(15, 25):  # Around 2^20
                    # Test multiple relationship types
                    relationships_to_test = [
                        ('cross_multiply', lambda: target_int * const_val * (2 ** power)),
                        ('cross_divide', lambda: target_int / (const_val * (2 ** power))),
                        ('inv_multiply', lambda: candidate_int * const_val * (2 ** power)),
                        ('direct_ratio', lambda: best_key_int / (const_val * (2 ** power))),
                    ]
                    
                    for rel_type, calc_func in relationships_to_test:
                        try:
                            target_private_key_float = calc_func()
                            
                            # Test integer values around this mathematical target
                            base_int = int(target_private_key_float)
                            
                            for offset in [-5, -2, -1, 0, 1, 2, 5]:
                                test_key_int = max(1, base_int + offset)
                                test_key = test_key_int.to_bytes(32, 'big')
                                
                                score, details = self._test_key_precision(test_key)
                                if score < best_score:
                                    best_score = score
                                    best_candidate = test_key
                                    best_details = details
                                    print(f"   🧮 Math improvement: {score:.8f} ({const_name}*2^{power}, {rel_type}, offset:{offset})")
                                    
                                    if score == 0.0:
                                        print(f"   🎉 PERFECT MATHEMATICAL MATCH!")
                                        return best_candidate, best_details
                        except:
                            continue
        
        # Strategy 3: High-precision fractional adjustments
        print(f"🔍 Strategy 3: High-precision fractional adjustments...")
        
        for const_name, const_val in self.high_precision_constants.items():
            for power in range(18, 23):  # Fine-tune around 2^20
                for micro_factor in [0.9999, 0.99995, 0.99999, 1.00001, 1.00005, 1.0001]:
                    try:
                        adjusted_const = const_val * micro_factor
                        target_calc = target_int * adjusted_const * (2 ** power)
                        test_key_int = max(1, int(target_calc))
                        test_key = test_key_int.to_bytes(32, 'big')
                        
                        score, details = self._test_key_precision(test_key)
                        if score < best_score:
                            best_score = score
                            best_candidate = test_key
                            best_details = details
                            print(f"   🎯 Precision improvement: {score:.8f} ({const_name}*{micro_factor:.6f}*2^{power})")
                            
                            if score == 0.0:
                                print(f"   🎉 PERFECT PRECISION MATCH!")
                                return best_candidate, best_details
                    except:
                        continue
        
        print(f"🔬 Micro-refinement complete. Best score: {best_score:.8f}")
        return best_candidate, best_details
    
    def _test_key_precision(self, private_key: bytes) -> tuple:
        """High-precision test of a private key"""
        try:
            # Generate both formats
            hash160_compressed, hash160_uncompressed = self.crypto.private_key_to_hash160_both(private_key)
            
            # Check for exact match first
            if hash160_compressed == self.target_hash:
                return 0.0, {
                    'exact_match': True,
                    'match_type': 'compressed',
                    'hash160_used': hash160_compressed
                }
            
            if hash160_uncompressed == self.target_hash:
                return 0.0, {
                    'exact_match': True,
                    'match_type': 'uncompressed',
                    'hash160_used': hash160_uncompressed
                }
            
            # Calculate high-precision fitness for both formats
            target_int = int.from_bytes(self.target_hash, 'big')
            private_key_int = int.from_bytes(private_key, 'big')
            
            best_score = 1.0
            best_details = None
            
            for format_name, hash160 in [("compressed", hash160_compressed), ("uncompressed", hash160_uncompressed)]:
                candidate_int = int.from_bytes(hash160, 'big')
                
                # High-precision decimal fitness
                decimal_diff = abs(candidate_int - target_int)
                max_possible_diff = 2 ** 160
                decimal_fitness = 1.0 - (decimal_diff / max_possible_diff)
                
                # High-precision mathematical analysis
                math_analysis = self.math_detector.analyze_mathematical_relationships(
                    candidate_int, private_key_int
                )
                math_fitness = math_analysis['max_accuracy']
                
                # High-precision combined fitness (equal weights for micro-refinement)
                combined_fitness = 0.5 * decimal_fitness + 0.5 * math_fitness
                score = 1.0 - combined_fitness
                
                if score < best_score:
                    best_score = score
                    best_details = {
                        'exact_match': False,
                        'match_type': format_name,
                        'mathematical_fitness': math_fitness,
                        'decimal_fitness': decimal_fitness,
                        'mathematical_pattern': math_analysis['best_pattern'],
                        'final_score': score,
                        'hash160_used': hash160
                    }
            
            return best_score, best_details
            
        except Exception:
            return 1.0, {'error': 'test_failed'}
    """Learns optimal fitness weights during the run - keeps the adaptive magic!"""
    
    def __init__(self, config: MathematicalGAConfig):
        self.config = config
        
        # Current adaptive weights (start with config defaults)
        self.decimal_weight = config.INITIAL_DECIMAL_WEIGHT
        self.mathematical_weight = config.INITIAL_MATHEMATICAL_WEIGHT
        
        # Performance tracking for each component
        self.decimal_performance_history = deque(maxlen=100)
        self.mathematical_performance_history = deque(maxlen=100)
        
        # Learning statistics
        self.weight_adjustment_count = 0
        self.best_combination_seen = None
        self.improvement_attribution = {'decimal': 0, 'mathematical': 0}
        
        self.lock = threading.RLock()
        
        print(f"🎯 Adaptive fitness manager initialized")
        print(f"🎯 Starting weights: Decimal={self.decimal_weight:.3f}, Math={self.mathematical_weight:.3f}")

    def get_current_weights(self) -> tuple:
        """Get current adaptive weights"""
        with self.lock:
            # Ensure weights sum to 1.0
            total = self.decimal_weight + self.mathematical_weight
            if total > 0:
                decimal_norm = self.decimal_weight / total
                math_norm = self.mathematical_weight / total
            else:
                decimal_norm = 0.5
                math_norm = 0.5
            
            return decimal_norm, math_norm

    def learn_from_improvement(self, improvement_details: dict):
        """Learn which fitness components are driving improvements - KEEP THE MAGIC!"""
        if not improvement_details or improvement_details.get('improvement', 0) <= 0:
            return
        
        with self.lock:
            improvement_size = improvement_details['improvement']
            decimal_contrib = improvement_details.get('decimal_contribution', 0.0)
            math_contrib = improvement_details.get('mathematical_contribution', 0.0)
            
            # Track which component is contributing more to improvements
            if decimal_contrib > math_contrib:
                self.improvement_attribution['decimal'] += improvement_size
                # Slightly increase decimal weight if it's driving improvements
                if self.config.FITNESS_ADAPTATION:
                    self.decimal_weight = min(self.config.MAX_WEIGHT, 
                                            self.decimal_weight + self.config.WEIGHT_LEARNING_RATE * improvement_size)
                    self.mathematical_weight = max(self.config.MIN_WEIGHT,
                                                 self.mathematical_weight - self.config.WEIGHT_LEARNING_RATE * improvement_size * 0.5)
            
            elif math_contrib > decimal_contrib:
                self.improvement_attribution['mathematical'] += improvement_size
                # Slightly increase mathematical weight if it's driving improvements
                if self.config.FITNESS_ADAPTATION:
                    self.mathematical_weight = min(self.config.MAX_WEIGHT,
                                                 self.mathematical_weight + self.config.WEIGHT_LEARNING_RATE * improvement_size)
                    self.decimal_weight = max(self.config.MIN_WEIGHT,
                                            self.decimal_weight - self.config.WEIGHT_LEARNING_RATE * improvement_size * 0.5)
            
            # Track performance history
            self.decimal_performance_history.append(decimal_contrib)
            self.mathematical_performance_history.append(math_contrib)
            self.weight_adjustment_count += 1
            
            if self.config.DETAILED_LOGGING and self.weight_adjustment_count % 50 == 0:
                decimal_w, math_w = self.get_current_weights()
                print(f"        🎯 Fitness weights adapted: Decimal={decimal_w:.3f}, Math={math_w:.3f}")

    def analyze_component_performance(self) -> dict:
        """Analyze which components are performing well"""
        with self.lock:
            analysis = {}
            
            if self.decimal_performance_history:
                analysis['decimal_avg'] = statistics.mean(self.decimal_performance_history)
                analysis['decimal_trend'] = 'improving' if len(self.decimal_performance_history) > 10 and \
                    statistics.mean(list(self.decimal_performance_history)[-10:]) > \
                    statistics.mean(list(self.decimal_performance_history)[:10]) else 'stable'
            else:
                analysis['decimal_avg'] = 0.0
                analysis['decimal_trend'] = 'unknown'
            
            if self.mathematical_performance_history:
                analysis['mathematical_avg'] = statistics.mean(self.mathematical_performance_history)
                analysis['mathematical_trend'] = 'improving' if len(self.mathematical_performance_history) > 10 and \
                    statistics.mean(list(self.mathematical_performance_history)[-10:]) > \
                    statistics.mean(list(self.mathematical_performance_history)[:10]) else 'stable'
            else:
                analysis['mathematical_avg'] = 0.0
                analysis['mathematical_trend'] = 'unknown'
            
            analysis['current_weights'] = self.get_current_weights()
            analysis['adjustments_made'] = self.weight_adjustment_count
            analysis['improvement_attribution'] = self.improvement_attribution.copy()
            
            return analysis

    def reset_if_stagnant(self):
        """Reset weights if performance stagnates - part of the adaptive magic"""
        with self.lock:
            if len(self.decimal_performance_history) > 50 and len(self.mathematical_performance_history) > 50:
                recent_decimal = statistics.mean(list(self.decimal_performance_history)[-20:])
                recent_math = statistics.mean(list(self.mathematical_performance_history)[-20:])
                
                # If both components are performing poorly, reset to balanced weights
                if recent_decimal < 0.01 and recent_math < 0.01:
                    self.decimal_weight = self.config.INITIAL_DECIMAL_WEIGHT
                    self.mathematical_weight = self.config.INITIAL_MATHEMATICAL_WEIGHT
                    print(f"        🔄 Fitness weights reset due to stagnation")

def adaptive_fitness_function(private_key: bytes, target_hash: bytes,
                             math_detector: MathematicalRelationshipDetector,
                             fitness_manager: AdaptiveFitnessManager,
                             crypto: CryptoOps) -> Tuple[float, dict]:
    """Adaptive fitness with decimal + mathematical - NO HAMMING NOISE!"""
    
    # Generate both compressed and uncompressed hash160s
    hash160_compressed, hash160_uncompressed = crypto.private_key_to_hash160_both(private_key)
    
    # Check for EXACT MATCH first - instant win!
    if hash160_compressed == target_hash:
        return 0.0, {
            'exact_match': True,
            'match_type': 'compressed',
            'mathematical_fitness': 1.0,
            'decimal_fitness': 1.0,
            'mathematical_pattern': 'EXACT_MATCH_COMPRESSED',
            'final_score': 0.0,
            'hash160_used': hash160_compressed,
            'improvement': 0.0,
            'decimal_contribution': 1.0,
            'mathematical_contribution': 1.0
        }
    
    if hash160_uncompressed == target_hash:
        return 0.0, {
            'exact_match': True,
            'match_type': 'uncompressed', 
            'mathematical_fitness': 1.0,
            'decimal_fitness': 1.0,
            'mathematical_pattern': 'EXACT_MATCH_UNCOMPRESSED',
            'final_score': 0.0,
            'hash160_used': hash160_uncompressed,
            'improvement': 0.0,
            'decimal_contribution': 1.0,
            'mathematical_contribution': 1.0
        }
    
    # No exact match - calculate adaptive fitness
    target_int = int.from_bytes(target_hash, 'big')
    private_key_int = int.from_bytes(private_key, 'big')
    
    # Analyze both formats
    candidate_compressed_int = int.from_bytes(hash160_compressed, 'big')
    candidate_uncompressed_int = int.from_bytes(hash160_uncompressed, 'big')
    
    # Mathematical analysis for both formats
    math_analysis_compressed = math_detector.analyze_mathematical_relationships(
        candidate_compressed_int, private_key_int
    )
    math_analysis_uncompressed = math_detector.analyze_mathematical_relationships(
        candidate_uncompressed_int, private_key_int
    )
    
    # Decimal proximity for both formats
    decimal_diff_compressed = abs(candidate_compressed_int - target_int)
    decimal_diff_uncompressed = abs(candidate_uncompressed_int - target_int)
    max_possible_diff = 2 ** 160
    
    decimal_fitness_compressed = 1.0 - (decimal_diff_compressed / max_possible_diff)
    decimal_fitness_uncompressed = 1.0 - (decimal_diff_uncompressed / max_possible_diff)
    
    # Calculate combined fitness for both formats
    decimal_w, math_w = fitness_manager.get_current_weights()
    
    combined_fitness_compressed = (decimal_w * decimal_fitness_compressed + 
                                 math_w * math_analysis_compressed['max_accuracy'])
    combined_fitness_uncompressed = (decimal_w * decimal_fitness_uncompressed + 
                                   math_w * math_analysis_uncompressed['max_accuracy'])
    
    # Use whichever format has better combined fitness
    if combined_fitness_compressed >= combined_fitness_uncompressed:
        best_decimal_fitness = decimal_fitness_compressed
        best_math_fitness = math_analysis_compressed['max_accuracy']
        best_pattern = math_analysis_compressed['best_pattern']
        best_hash160 = hash160_compressed
        best_combined = combined_fitness_compressed
        format_used = 'compressed'
        best_relationships = math_analysis_compressed['total_relationships']
    else:
        best_decimal_fitness = decimal_fitness_uncompressed
        best_math_fitness = math_analysis_uncompressed['max_accuracy']
        best_pattern = math_analysis_uncompressed['best_pattern']
        best_hash160 = hash160_uncompressed
        best_combined = combined_fitness_uncompressed
        format_used = 'uncompressed'
        best_relationships = math_analysis_uncompressed['total_relationships']
    
    # Final score: lower is better (invert the fitness)
    final_score = 1.0 - best_combined
    
    details = {
        'exact_match': False,
        'match_type': format_used,
        'mathematical_fitness': best_math_fitness,
        'decimal_fitness': best_decimal_fitness,
        'mathematical_pattern': best_pattern,
        'final_score': final_score,
        'total_relationships': best_relationships,
        'hash160_used': best_hash160,
        'compressed_math_accuracy': math_analysis_compressed['max_accuracy'],
        'uncompressed_math_accuracy': math_analysis_uncompressed['max_accuracy'],
        'compressed_decimal_fitness': decimal_fitness_compressed,
        'uncompressed_decimal_fitness': decimal_fitness_uncompressed,
        'weights_used': (decimal_w, math_w),
        'improvement': 0.0,  # Will be calculated when comparing to previous best
        'decimal_contribution': best_decimal_fitness,
        'mathematical_contribution': best_math_fitness
    }
    
    return final_score, details

class MathematicalHashGA:
    """Enhanced GA engine with mathematical relationship exploitation + ALL original adaptive magic"""
    
    def __init__(self, config: MathematicalGAConfig):
        self.config = config
        self.crypto = CryptoOps()
        
        # Initialize components after target is set
        self.math_detector = None
        self.hex_manager = None
        self.fitness_manager = None  # NEW: Adaptive fitness manager
        self.atomics = MathematicalAtomics(config)
        
        # Population storage
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.elite_scores = []
        self.target_hash = None
        
        # KEEP ALL: Track previous best for improvement calculations
        self.previous_best_score = 1.0
        
        print(f"🔥 Mathematical Hash160 GA initialized with adaptive fitness")
        print(f"🧮 Ready to exploit mathematical relationships with adaptive learning!")

    def initialize_target_specific_components(self, target_hash_hex: str):
        """Initialize components that depend on the specific target"""
        target_int = int(target_hash_hex.replace('0x', ''), 16)
        self.math_detector = MathematicalRelationshipDetector(target_int, self.config)
        self.hex_manager = EnhancedAdaptiveHexManager(self.config, self.math_detector)
        self.fitness_manager = AdaptiveFitnessManager(self.config)  # NEW: Adaptive fitness
        
        print(f"🎯 Target-specific components initialized for: {target_hash_hex}")

    def score_key(self, private_key: bytes) -> float:
        """Enhanced scoring with adaptive fitness and dual format checking"""
        try:
            self.atomics.atomic_increment_evals(1)
            
            # Use adaptive fitness function - keeps decimal + mathematical balance
            score, details = adaptive_fitness_function(
                private_key, self.target_hash, self.math_detector, self.fitness_manager, self.crypto
            )
            
            # Check for EXACT MATCH - we win!
            if details['exact_match']:
                key_int = int.from_bytes(private_key, 'big')
                print(f"\n🎉🎉🎉 EXACT MATCH FOUND! 🎉🎉🎉")
                print(f"🔑 Private Key: 0x{key_int:X}")
                print(f"📍 Format: {details['match_type']}")
                print(f"🎯 Target Hash160: {self.target_hash.hex()}")
                print(f"✅ Generated Hash160: {details['hash160_used'].hex()}")
                print(f"🏆 PUZZLE SOLVED!")
                
                # This should trigger immediate termination
                self.atomics.try_update_global_best(0.0, private_key, 1.0)
                return 0.0
            
            # Calculate improvement for adaptive learning
            improvement = max(0.0, self.previous_best_score - score)
            if improvement > 0:
                details['improvement'] = improvement
                # Learn from this improvement - KEEP THE ADAPTIVE MAGIC!
                self.fitness_manager.learn_from_improvement(details)
            
            # Track mathematical discoveries
            math_accuracy = details['mathematical_fitness']
            improved = self.atomics.try_update_global_best(score, private_key, math_accuracy)
            
            if improved:
                self.previous_best_score = score
                key_int = int.from_bytes(private_key, 'big')
                decimal_w, math_w = details['weights_used']
                print(f"      🎯 NEW GLOBAL BEST: {score:.6f} "
                      f"(D:{details['decimal_fitness']:.3f}, M:{math_accuracy:.3f}, {details['match_type']}) "
                      f"key: 0x{key_int:X}")
                print(f"         💪 Weights: Decimal={decimal_w:.3f}, Math={math_w:.3f}")
                
                if math_accuracy > 0.999:
                    print(f"         🧮 MATHEMATICAL BREAKTHROUGH: {details['mathematical_pattern']}")
                elif math_accuracy > 0.99:
                    print(f"         🔥 HIGH MATHEMATICAL ACCURACY: {details['mathematical_pattern']}")
                
                # Show both format accuracies if significantly different
                comp_math = details['compressed_math_accuracy']
                uncomp_math = details['uncompressed_math_accuracy']
                if abs(comp_math - uncomp_math) > 0.05:
                    print(f"         📊 Math accuracy - Compressed: {comp_math:.3f}, Uncompressed: {uncomp_math:.3f}")
            
            return score
            
        except Exception as e:
            return 1.0  # Worst possible fitness

    # KEEP ALL original adaptive mutation magic!
    def adaptive_mutate_key(self, key: bytes, strength: float) -> bytes:
        """Enhanced mutation with mathematical guidance + ALL original adaptive logic"""
        try:
            # 30% chance for mathematically-informed mutation
            if random.random() < 0.3 and self.hex_manager:
                return self.hex_manager.generate_mathematically_informed_key()
            else:
                # Use ALL the original adaptive mutation logic - KEEP THE MAGIC!
                return self._original_adaptive_mutate(key, strength)
        except Exception:
            return key

    def _original_adaptive_mutate(self, key: bytes, strength: float) -> bytes:
        """KEEP ALL the original adaptive mutation logic - this is the magic!"""
        try:
            active_bytes = self.hex_manager.current_active_bytes
            max_range = self.hex_manager.get_active_range()
            
            key_int = int.from_bytes(key, 'big')
            if key_int > max_range:
                key_int = key_int % max_range
            key_int = max(1, key_int)
            
            mutations = []
            
            # KEEP ALL: Position-weighted byte mutations with learned weights
            key_bytes = list(key)
            for byte_pos in range(min(active_bytes, 32)):
                position_weight = self.hex_manager.position_weights[byte_pos]
                mutation_prob = strength * position_weight * 0.6
                
                if random.random() < mutation_prob:
                    old_byte = key_bytes[byte_pos]
                    if random.random() < 0.5:
                        key_bytes[byte_pos] = random.randint(0, 255)
                    elif random.random() < 0.5:
                        delta = random.randint(-50, 50)
                        key_bytes[byte_pos] = max(0, min(255, old_byte + delta))
                    else:
                        patterns = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF,
                                  0x7F, 0x3F, 0x1F, 0x0F]
                        key_bytes[byte_pos] = random.choice(patterns)
            
            mutations.append(bytes(key_bytes))
            
            # KEEP ALL: Integer-level mutations in adaptive range
            for i in range(4):
                if random.random() < strength:
                    delta_range = max(1000, int(max_range * strength * 0.1))
                    delta = random.randint(-delta_range, delta_range)
                    new_int = max(1, min(key_int + delta, max_range))
                    mutations.append(new_int.to_bytes(32, 'big'))
            
            # KEEP ALL: Bit flips with adaptive range
            if random.random() < strength:
                max_bit = min(255, active_bytes * 8 - 1)
                for _ in range(random.randint(1, 3)):
                    bit_pos = random.randint(0, max_bit)
                    new_int = key_int ^ (1 << bit_pos)
                    new_int = max(1, min(new_int, max_range))
                    mutations.append(new_int.to_bytes(32, 'big'))
            
            # KEEP ALL: Mathematical operations
            if random.random() < strength * 0.8:
                operations = [
                    lambda x: min(x * random.randint(2, 10), max_range),
                    lambda x: max(1, x // random.randint(2, 10)),
                    lambda x: max(1, min(x + random.randint(1000, 100000), max_range)),
                    lambda x: max(1, x - random.randint(1000, 100000)),
                    lambda x: max(1, min(x ^ random.randint(1, max_range // 100), max_range)),
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

    # KEEP ALL: Original evolution logic with position awareness
    def evolve_individual(self, base_key: bytes) -> List[bytes]:
        """Enhanced evolution with mathematical generation + ALL original adaptive logic"""
        candidates = []
        current_strength = self.atomics.atomic_get_all_stats()['mutation_strength']
        
        # KEEP ALL: Multiple adaptive mutations
        for i in range(5):
            try:
                varying_strength = current_strength * (0.4 + i * 0.2)
                mutated = self.adaptive_mutate_key(base_key, varying_strength)
                candidates.append(mutated)
            except Exception:
                continue
        
        # KEEP ALL: Elite crossover with position awareness
        if len(self.elite_keys) >= 2:
            try:
                parent1, parent2 = random.sample(self.elite_keys, 2)
                child = bytearray(32)
                active_bytes = self.hex_manager.current_active_bytes
                
                for byte_pos in range(active_bytes):
                    weight = self.hex_manager.position_weights[byte_pos]
                    if random.random() < weight:
                        child[byte_pos] = parent1[byte_pos] if random.random() < 0.5 else parent2[byte_pos]
                    else:
                        child[byte_pos] = base_key[byte_pos]
                
                candidates.append(bytes(child))
            except Exception:
                pass
        
        # Enhanced: Fresh mathematically-informed generation
        try:
            fresh_key = self.hex_manager.generate_mathematically_informed_key()
            candidates.append(fresh_key)
        except Exception:
            pass
        
        return candidates if candidates else [base_key]

    # KEEP ALL other original methods (update_elite_pool, inject_diversity, etc.) unchanged
    def update_elite_pool(self):
        """KEEP ALL: Update elite pool - no diversity constraints but reject duplicate keys"""
        if not self.population:
            return
        
        scored_individuals = list(zip(self.scores, self.population))
        scored_individuals.sort(key=lambda x: x[0])  # Lower scores are better
        
        selected_elite = []
        used_keys = set()
        
        for score, key in scored_individuals:
            if score >= 1.0:  # Worst possible fitness
                continue
            
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
        """KEEP ALL: Inject fresh mathematically-informed diversity"""
        if not self.population:
            return
        
        num_to_replace = max(1, int(len(self.population) * self.config.DIVERSITY_INJECTION_RATE))
        
        scored_individuals = list(zip(self.scores, range(len(self.population))))
        scored_individuals.sort(key=lambda x: x[0], reverse=True)  # Worst first
        
        fresh_count = 0
        for score, idx in scored_individuals[:num_to_replace]:
            try:
                fresh_key = self.hex_manager.generate_mathematically_informed_key()
                fresh_score = self.score_key(fresh_key)
                
                self.population[idx] = fresh_key
                self.scores[idx] = fresh_score
                fresh_count += 1
            except Exception:
                continue
        
        if self.config.DETAILED_LOGGING:
            print(f"    💉 Injected {fresh_count} fresh mathematically-informed keys")

    def run_optimization(self, target_hash_hex: str) -> dict:
        """Run enhanced mathematical GA optimization"""
        
        # Parse target
        try:
            self.target_hash = bytes.fromhex(target_hash_hex.replace('0x', ''))
            if len(self.target_hash) != 20:
                raise ValueError(f"Target hash must be 40 hex characters (20 bytes)")
        except Exception as e:
            return {'error': f"Invalid target hash: {e}"}
        
        # Initialize target-specific components
        self.initialize_target_specific_components(target_hash_hex)
        
        print(f"\n🎯 TARGET: {target_hash_hex}")
        print(f"🧮 Starting mathematical relationship exploitation...")
        
        with self.atomics.start_time.get_lock():
            self.atomics.start_time.value = time.time()
        
        # Initialize population with mathematical generation
        print(f"🧬 Initializing population of {self.config.K_POOL}...")
        for i in range(self.config.K_POOL):
            try:
                key = self.hex_manager.generate_mathematically_informed_key()
                score = self.score_key(key)
                self.population.append(key)
                self.scores.append(score)
                
                if i < 5:
                    key_int = int.from_bytes(key, 'big')
                    print(f"  Key {i}: 0x{key_int:X} → score={score:.3f}")
            except Exception:
                continue
        
        # Show initial mathematical state
        hex_stats = self.hex_manager.get_detailed_stats()
        print(f"🧮 Initial mathematical state:")
        print(f"   Active bytes: {hex_stats['current_active_bytes']}")
        print(f"   Mathematical patterns: {hex_stats['mathematical_patterns_discovered']}")
        print(f"   Best constants: {hex_stats['best_mathematical_constants']}")
        
        self.update_elite_pool()
        initial_stats = self.atomics.atomic_get_all_stats()
        print(f"🎯 Initial best: {initial_stats['best_score']:.3f}")
        print(f"🧮 Mathematical accuracy: {initial_stats['best_mathematical_accuracy']:.3f}")
        
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
                
                # Update components
                self.update_elite_pool()
                self.hex_manager.analyze_population_ranges(self.population, self.scores)
                self.hex_manager.adapt_active_range(round_num, self.elite_scores)
                self.hex_manager.apply_global_weight_decay()
                
                # Round statistics
                round_end_stats = self.atomics.atomic_get_all_stats()
                round_time = time.time() - round_start_time
                
                improved = round_end_stats['best_score'] < round_start_stats['best_score']
                if improved:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_DECAY)
                elif round_num % 5 == 0:
                    self.atomics.atomic_update_mutation_strength(self.config.MUTATION_INCREASE)
                
                # Show round results with adaptive fitness analysis
                elite_fitness = statistics.mean([1.0 - score for score in self.elite_scores]) if self.elite_scores else 0.0
                decimal_w, math_w = self.fitness_manager.get_current_weights()
                print(f"   Best: {round_end_stats['best_score']:.6f} "
                      f"(Math: {round_end_stats['best_mathematical_accuracy']:.6f})")
                print(f"   Elite: {elite_fitness:.3f} avg fitness ({len(self.elite_scores)} individuals)")
                print(f"   Weights: Decimal={decimal_w:.3f}, Math={math_w:.3f}")
                print(f"   Learning: {learning_events} events, "
                      f"{round_end_stats['mathematical_discoveries']} math discoveries")
                print(f"   Round time: {round_time:.1f}s")
                
                # Show adaptive insights every few rounds
                if round_num % 5 == 0 or improved:
                    hex_stats = self.hex_manager.get_detailed_stats()
                    fitness_analysis = self.fitness_manager.analyze_component_performance()
                    print(f"   🧮 Mathematical state: {hex_stats['mathematical_patterns_discovered']} patterns, "
                          f"constants: {hex_stats['best_mathematical_constants'][:3]}")
                    print(f"   🎯 Fitness trends: Decimal={fitness_analysis['decimal_trend']}, "
                          f"Math={fitness_analysis['mathematical_trend']}")
                
                # Diversity injection on stagnation - KEEP ALL original logic
                if round_num % 8 == 0:
                    self.inject_diversity()
                
                # Adaptive reset logic - enhanced with fitness manager
                if round_num % 20 == 0 and round_end_stats['best_score'] == round_start_stats['best_score']:
                    print(f"    🔄 Adaptive reset - no improvement for 20 rounds")
                    self.hex_manager.reset_position_weights()
                    self.fitness_manager.reset_if_stagnant()  # NEW: Reset fitness weights too
                
                # Enhanced: Early termination with micro-refinement for near-perfect results
                if (self.config.ENABLE_MICRO_REFINEMENT and 
                    round_end_stats['best_score'] <= self.config.MICRO_REFINEMENT_THRESHOLD and 
                    round_end_stats['best_score'] > 0.0):
                    
                    print(f"\n🔬 NEAR-PERFECT RESULT - Activating micro-refinement!")
                    print(f"   Current score: {round_end_stats['best_score']:.8f}")
                    print(f"   Mathematical accuracy: {round_end_stats['best_mathematical_accuracy']:.8f}")
                    
                    # Initialize micro-refiner
                    micro_refiner = MicroPrecisionRefiner(self.crypto, self.math_detector, self.target_hash)
                    
                    # Get current best key
                    current_best_key = self.atomics.get_best_key()
                    
                    # Attempt micro-refinement
                    refined_key, refined_details = micro_refiner.micro_refine_around_best(
                        current_best_key, round_end_stats['best_score']
                    )
                    
                    # Test the refined result
                    refined_score = self.score_key(refined_key)
                    
                    if refined_score == 0.0:
                        print(f"\n🎉🎉🎉 PERFECT SOLUTION FOUND via micro-refinement! 🎉🎉🎉")
                        break
                    elif refined_score < round_end_stats['best_score']:
                        print(f"🔬 Micro-refinement improved score: {refined_score:.8f}")
                        print(f"🎯 Continuing optimization from refined position...")
                    else:
                        print(f"🔬 Micro-refinement complete, continuing GA optimization...")
                        print(f"🎯 Current best remains: {round_end_stats['best_score']:.8f}")
                    
                    # Continue GA after micro-refinement attempt
                
                # Original early termination for exact matches
                elif round_end_stats['best_score'] == 0.0:
                    print(f"\n🎉 EXACT MATCH FOUND! Terminating at round {round_num + 1}")
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
            
            # Get mathematical analysis of final result
            final_hash160 = self.crypto.private_key_to_hash160(best_key)
            final_analysis = self.math_detector.analyze_mathematical_relationships(
                int.from_bytes(final_hash160, 'big'), best_key_int
            )
            
            # Get final adaptive fitness analysis
            final_fitness_analysis = self.fitness_manager.analyze_component_performance()
            final_weights = self.fitness_manager.get_current_weights()
            
            return {
                'target_hash': target_hash_hex,
                'best_score': final_stats['best_score'],
                'best_mathematical_accuracy': final_stats['best_mathematical_accuracy'],
                'best_key_hex': best_key.hex(),
                'best_key_int': f"0x{best_key_int:X}",
                'total_evaluations': final_stats['evaluations'],
                'improvements': final_stats['improvements'],
                'mathematical_discoveries': final_stats['mathematical_discoveries'],
                'total_time': total_time,
                'elite_mean_fitness': statistics.mean([1.0 - score for score in self.elite_scores]) if self.elite_scores else 0.0,
                'elite_count': len(self.elite_scores),
                'final_hex_stats': final_hex_stats,
                'final_mathematical_analysis': final_analysis,
                'final_fitness_analysis': final_fitness_analysis,  # NEW: Adaptive fitness results
                'final_weights': final_weights,  # NEW: Final adaptive weights
                'rounds_completed': min(round_num + 1, self.config.MAX_ROUNDS),
                'evals_per_second': final_stats['evaluations'] / total_time if total_time > 0 else 0,
                'exact_match_found': final_stats['best_score'] == 0.0,
                'micro_refinement_used': self.config.ENABLE_MICRO_REFINEMENT and final_stats['best_score'] <= self.config.MICRO_REFINEMENT_THRESHOLD
            }
        except Exception as e:
            return {'error': str(e)}

def print_mathematical_analysis(results: dict):
    """Print comprehensive mathematical analysis of results"""
    print("\n" + "="*100)
    print("🧮 PURE MATHEMATICAL FITNESS GA ANALYSIS")
    print("="*100)
    
    if 'error' in results:
        print(f"❌ Analysis failed: {results['error']}")
        return
    
    # Check for exact match first
    if results.get('exact_match_found', False):
        print("🎉🎉🎉 PUZZLE SOLVED! 🎉🎉🎉")
        print(f"🔑 Private Key: {results['best_key_int']}")
        print(f"🎯 Target Hash160: {results['target_hash']}")
        print("✅ EXACT HASH160 MATCH ACHIEVED!")
        print("="*100)
        return
    
    print(f"🎯 Target:                    {results['target_hash']}")
    print(f"🏆 Best Score:                {results['best_score']:.8f} (lower = better)")
    print(f"🧮 Mathematical Accuracy:     {results['best_mathematical_accuracy']:.8f}")
    print(f"🔑 Best Key:                  {results['best_key_int']}")
    print(f"⚡ Total Evaluations:         {results['total_evaluations']:,}")
    print(f"📈 Improvements:              {results['improvements']}")
    print(f"🧮 Mathematical Discoveries:  {results['mathematical_discoveries']}")
    print(f"⏱️  Total Time:                {results['total_time']:.1f} seconds")
    print(f"🚀 Speed:                     {results['evals_per_second']:,.0f} evals/second")
    print(f"🧬 Elite Mean Fitness:        {results['elite_mean_fitness']:.6f}")
    
    # Show final adaptive fitness weights
    if 'final_weights' in results:
        decimal_w, math_w = results['final_weights']
        print(f"💪 Final Adaptive Weights:    Decimal={decimal_w:.3f}, Mathematical={math_w:.3f}")
    
    # Show micro-refinement usage
    if results.get('micro_refinement_used', False):
        print(f"🔬 Micro-Refinement:          Activated (99.9%+ accuracy achieved)")
    else:
        print(f"🔬 Micro-Refinement:          Not triggered")
    
    if 'final_mathematical_analysis' in results:
        math_analysis = results['final_mathematical_analysis']
        print(f"\n🧮 FINAL MATHEMATICAL ANALYSIS:")
        print(f"   Best Mathematical Pattern:  {math_analysis['best_pattern']}")
        print(f"   Pattern Accuracy:           {math_analysis['max_accuracy']:.8f}")
        print(f"   Total Relationships Found: {math_analysis['total_relationships']}")
        
        if math_analysis['max_accuracy'] > 0.9999:
            print("   🚨 MATHEMATICAL BREAKTHROUGH: 99.99%+ ACCURACY!")
        elif math_analysis['max_accuracy'] > 0.999:
            print("   🔥 EXTREME MATHEMATICAL PRECISION: 99.9%+ ACCURACY!")
        elif math_analysis['max_accuracy'] > 0.99:
            print("   ⚡ HIGH MATHEMATICAL PRECISION: 99%+ ACCURACY!")
        elif math_analysis['max_accuracy'] > 0.95:
            print("   📊 STRONG MATHEMATICAL RELATIONSHIPS: 95%+ ACCURACY!")
    
    # Show adaptive fitness learning results
    if 'final_fitness_analysis' in results:
        fitness_analysis = results['final_fitness_analysis']
        print(f"\n🎯 ADAPTIVE FITNESS LEARNING RESULTS:")
        print(f"   Decimal Component Average:  {fitness_analysis['decimal_avg']:.6f}")
        print(f"   Mathematical Component Avg: {fitness_analysis['mathematical_avg']:.6f}")
        print(f"   Decimal Trend:              {fitness_analysis['decimal_trend']}")
        print(f"   Mathematical Trend:         {fitness_analysis['mathematical_trend']}")
        print(f"   Weight Adjustments Made:    {fitness_analysis['adjustments_made']}")
        
        # Show improvement attribution
        if 'improvement_attribution' in fitness_analysis:
            attr = fitness_analysis['improvement_attribution']
            total_improvements = attr['decimal'] + attr['mathematical']
            if total_improvements > 0:
                decimal_percent = (attr['decimal'] / total_improvements) * 100
                math_percent = (attr['mathematical'] / total_improvements) * 100
                print(f"   Improvement Attribution:    Decimal={decimal_percent:.1f}%, Mathematical={math_percent:.1f}%")
    
    if 'final_hex_stats' in results:
        hex_stats = results['final_hex_stats']
        print(f"\n🧠 ADAPTIVE HEX LEARNING RESULTS:")
        print(f"   Final Active Bytes:         {hex_stats['current_active_bytes']}")
        print(f"   Mathematical Patterns:      {hex_stats['mathematical_patterns_discovered']}")
        print(f"   Best Constants:             {hex_stats['best_mathematical_constants']}")
        print(f"   Learning Events:            {hex_stats['learning_events']}")
    
    # Performance analysis with adaptive insights
    current_accuracy = results['best_mathematical_accuracy']
    print(f"\n🎯 PERFORMANCE ANALYSIS:")
    
    if current_accuracy > 0.9999:
        print(f"   Status: BREAKTHROUGH - 99.99%+ mathematical accuracy!")
        print(f"   Implication: Exact mathematical relationship discovered!")
        print(f"   Next step: Fine-tune to achieve exact hash160 match")
    elif current_accuracy > 0.999:
        print(f"   Status: EXCELLENT - 99.9%+ mathematical accuracy")
        print(f"   Implication: Very strong mathematical relationship found")
        print(f"   Progress: Extremely close to breakthrough")
    elif current_accuracy > 0.99:
        print(f"   Status: STRONG - 99%+ mathematical accuracy")
        print(f"   Implication: Clear mathematical structure detected")
        print(f"   Progress: On track for breakthrough")
    elif current_accuracy > 0.95:
        print(f"   Status: GOOD - 95%+ mathematical accuracy")
        print(f"   Implication: Mathematical relationships present")
        print(f"   Progress: Building toward strong patterns")
    else:
        print(f"   Status: EXPLORING - Below 95% mathematical accuracy")
        print(f"   Implication: Still discovering mathematical structure")
        print(f"   Progress: Early exploration phase")
    
    # Adaptive fitness insights
    if 'final_fitness_analysis' in results:
        fitness_analysis = results['final_fitness_analysis']
        print(f"\n🧠 ADAPTIVE FITNESS INSIGHTS:")
        
        if fitness_analysis['decimal_trend'] == 'improving':
            print(f"   🔥 Decimal proximity learning is working!")
        
        if fitness_analysis['mathematical_trend'] == 'improving':
            print(f"   🧮 Mathematical relationship learning is working!")
        
        if fitness_analysis['adjustments_made'] > 50:
            print(f"   ⚡ High learning activity - GA actively adapting fitness weights")
        elif fitness_analysis['adjustments_made'] > 10:
            print(f"   📊 Moderate learning activity - some fitness adaptation occurring")
        else:
            print(f"   🔍 Low learning activity - weights remained relatively stable")
    
    print(f"\n💡 NEXT STEPS:")
    if current_accuracy > 0.999:
        print(f"   🎯 Continue optimization - you're extremely close!")
        print(f"   🔍 Both compressed AND uncompressed being checked automatically")
        print(f"   🔬 Micro-refinement will auto-trigger at 99.9%+ accuracy")
        print(f"   ⚡ Mathematical + decimal proximity guiding toward solution")
    elif current_accuracy > 0.99:
        print(f"   📈 Excellent progress - mathematical patterns strong")
        print(f"   🔧 Adaptive learning optimizing the balance automatically")
        print(f"   🔬 Approaching micro-refinement threshold (99.9%)")
    else:
        print(f"   🧮 Keep building mathematical understanding")
        print(f"   📊 Adaptive fitness will optimize component weights as patterns emerge")
        print(f"   🎯 Target: Get to 99.9%+ accuracy to trigger micro-refinement")
    
    print("="*100)

def run_mathematical_test():
    """Run the mathematical hash160 GA test"""
    if not TARGET_HASH160 or len(TARGET_HASH160.replace('0x', '')) != 40:
        print("❌ Please set a valid 40-character hex TARGET_HASH160 at the top of the script")
        return
    
    config = MathematicalGAConfig()
    engine = MathematicalHashGA(config)
    
    print(f"🔥 MATHEMATICAL HASH160 GA - UNIVERSAL RELATIONSHIP EXPLOITER")
    print(f"🎯 Target: {TARGET_HASH160}")
    print(f"🧮 Discovering mathematical patterns unique to this hash160...")
    
    results = engine.run_optimization(TARGET_HASH160)
    print_mathematical_analysis(results)
    
    return results

# Main execution
if __name__ == "__main__":
    print("🔥 ADAPTIVE FITNESS MATHEMATICAL GA - DECIMAL + MATH + MICRO-REFINEMENT")
    print("="*90)
    print("🧮 Adaptive fitness: Learns optimal balance between decimal & mathematical")
    print("🎯 Checks BOTH compressed AND uncompressed formats automatically")
    print("📊 Fitness: Decimal proximity + Mathematical relationships (NO HAMMING!)")
    print("🔬 Micro-refinement: Automatically triggers at 99.9%+ accuracy for final precision")
    print("⚡ Mathematical accuracy: 0-100% precision for constant relationships")
    print("🧠 Keeps ALL your original adaptive hex magic + position learning")
    print("🎯 Goal: Perfect 0.000000 score (exact hash160 match)")
    print("🔧 CHANGE TARGET_HASH160 variable at top of script to your target")
    print("="*90)
    
    run_mathematical_test()
#!/usr/bin/env python3
"""
DeathNote Pure Match - Mathematical Hash160 Hunter with Resonance Scanner
Finds ANY private key that produces target hash160 (collision or true key)
Scans target to find which mathematical constants it resonates with
"""

import time
import random
import math
import hashlib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import threading
from collections import deque
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
    from multiprocessing import Value, Array
    
except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "ecdsa", "pycryptodome"])
    
    import numpy as np
    from ecdsa import SECP256k1, SigningKey
    from Crypto.Hash import RIPEMD160
    from multiprocessing import Value, Array
    CRYPTO_ENGINE = 'ecdsa'

print(f"✅ DeathNote Pure Match loaded with {CRYPTO_ENGINE} engine")

@dataclass
class DeathNoteConfig:
    """Config for mathematical hash160 hunter"""
    # Population
    K_POOL: int = 8000
    ELITE_SIZE: int = 400
    
    # Always use full 32 bytes - let GA decide what's zero
    INITIAL_ACTIVE_BYTES: int = 32
    MAX_ACTIVE_BYTES: int = 32
    EXPANSION_THRESHOLD: float = 0.05
    RANGE_ADAPTATION_FREQ: int = 2
    
    # Position learning (keep the magic)
    POSITION_LEARNING_RATE: float = 0.08
    POSITION_DECAY: float = 0.98
    GLOBAL_WEIGHT_DECAY: float = 0.998
    MIN_POSITION_WEIGHT: float = 0.05
    MAX_POSITION_WEIGHT: float = 0.75
    
    # Mutation
    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MUTATION_INCREASE: float = 1.3
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 1.2
    
    # Mathematical constants to test
    MATHEMATICAL_CONSTANTS: Dict[str, float] = None
    
    # Fitness weights - dynamic based on mathematical discovery
    INITIAL_DECIMAL_WEIGHT: float = 0.35
    INITIAL_MATHEMATICAL_WEIGHT: float = 0.65
    
    # When perfect math found, switch to pure decimal
    MATH_PERFECT_THRESHOLD: float = 0.999
    PURE_DECIMAL_MODE: bool = False
    
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
            }

class MathematicalRelationshipFinder:
    """Finds mathematical relationships between hash160s with resonance scanning"""
    
    def __init__(self, target_hash160_int: int, config: DeathNoteConfig):
        self.target_hash160_int = target_hash160_int
        self.config = config
        self.constants = config.MATHEMATICAL_CONSTANTS.copy()
        
        # Track discovered patterns
        self.discovered_patterns = []
        self.pattern_performance = {}
        self.resonance_profile = None
        
        print(f"🧮 Mathematical finder initialized for target: {target_hash160_int}")
        
        # Scan for resonance
        self.scan_target_resonance()
    
    def scan_target_resonance(self) -> Dict:
        """Scan target hash160 to find which mathematical constants it resonates with"""
        print(f"\n🔍 Scanning target hash160 for mathematical resonance...")
        
        resonance_scores = {}
        target_float = self.target_hash160_int / (2**160)  # Normalize to 0-1
        
        # Test each constant at different scales
        for const_name, const_val in self.constants.items():
            best_resonance = 0.0
            best_scale = 0
            
            # Test different scales/powers
            for power in range(-10, 10):
                scaled_const = const_val * (2 ** power)
                
                # Test different resonance patterns
                # 1. Direct ratio resonance
                ratio = target_float / scaled_const
                ratio_resonance = 1.0 - abs(ratio - round(ratio))
                
                # 2. Multiplicative resonance
                mult = (self.target_hash160_int * scaled_const) % (2**160)
                mult_float = mult / (2**160)
                mult_resonance = 1.0 - abs(mult_float - 0.5)  # How close to middle
                
                # 3. Harmonic resonance
                harmonic = abs(math.sin(self.target_hash160_int * scaled_const))
                
                # Combined resonance score
                total_resonance = max(ratio_resonance, mult_resonance, harmonic)
                
                if total_resonance > best_resonance:
                    best_resonance = total_resonance
                    best_scale = power
            
            resonance_scores[const_name] = {
                'resonance': best_resonance,
                'best_scale': best_scale,
                'scaled_value': const_val * (2 ** best_scale)
            }
        
        # Sort by resonance strength
        sorted_resonances = sorted(resonance_scores.items(), 
                                 key=lambda x: x[1]['resonance'], 
                                 reverse=True)
        
        print(f"\n📊 TARGET RESONANCE PROFILE:")
        print(f"   Target: {self.target_hash160_int}")
        print(f"\n   🎵 Strongest resonances:")
        for const_name, data in sorted_resonances[:5]:
            print(f"      {const_name}: {data['resonance']:.4f} (scale: 2^{data['best_scale']})")
        
        # Store the resonance profile
        self.resonance_profile = {
            'primary': sorted_resonances[0][0],
            'primary_scale': sorted_resonances[0][1]['best_scale'],
            'secondary': sorted_resonances[1][0] if len(sorted_resonances) > 1 else None,
            'top_resonances': dict(sorted_resonances[:5])
        }
        
        return self.resonance_profile
    
    def analyze_relationships(self, candidate_hash160_int: int, 
                            private_key_int: int = None) -> Dict:
        """Find mathematical relationships"""
        if candidate_hash160_int == 0 or self.target_hash160_int == 0:
            return {'max_accuracy': 0.0, 'best_pattern': None}
        
        relationships = []
        max_accuracy = 0.0
        best_pattern = None
        
        # Direct hash160 relationships
        ratio = candidate_hash160_int / self.target_hash160_int
        
        for const_name, const_val in self.constants.items():
            # Test multiply relationships
            for power in range(0, 8):
                expected_ratio = const_val * (2 ** power)
                if expected_ratio > 0:
                    accuracy = self._calculate_accuracy(ratio, expected_ratio)
                    if accuracy > max_accuracy:
                        max_accuracy = accuracy
                        best_pattern = f"{const_name} * 2^{power}"
        
        # Simple ratios
        simple_ratios = [0.5, 1.5, 2.0, 3.0, 4.0, 5.0, 0.25, 0.75, 1.25]
        for simple_ratio in simple_ratios:
            accuracy = self._calculate_accuracy(ratio, simple_ratio)
            if accuracy > max_accuracy:
                max_accuracy = accuracy
                best_pattern = f"simple: {simple_ratio:.2f}x"
        
        return {
            'max_accuracy': max_accuracy,
            'best_pattern': best_pattern
        }
    
    def _calculate_accuracy(self, actual: float, expected: float) -> float:
        """Calculate accuracy between values"""
        if expected == 0 or actual == 0:
            return 0.0
        error = abs(actual - expected) / expected
        return max(0.0, 1.0 - error)
    
    def generate_mathematical_target(self) -> int:
        """Generate a mathematically-informed target hash160 using resonance profile"""
        strategies = []
        
        # Prioritize resonant constants
        if self.resonance_profile:
            # Use primary resonant constant most often
            primary = self.resonance_profile['primary']
            primary_scale = self.resonance_profile['primary_scale']
            primary_val = self.constants[primary] * (2 ** primary_scale)
            
            # Generate using primary resonance
            for i in range(5):  # Multiple variations
                factor = 1 + (random.random() - 0.5) * 0.1  # ±5% variation
                target_candidate = int(self.target_hash160_int * primary_val * factor)
                if 0 < target_candidate < 2**160:
                    strategies.append(target_candidate)
            
            # Also use secondary resonances
            for const_name, data in self.resonance_profile['top_resonances'].items():
                scaled_val = data['scaled_value']
                target_candidate = int(self.target_hash160_int * scaled_val)
                if 0 < target_candidate < 2**160:
                    strategies.append(target_candidate)
        
        # Fallback to original method
        if not strategies:
            for const_name, const_val in self.constants.items():
                for power in range(0, 6):
                    # Target * constant * 2^N
                    target_candidate = int(self.target_hash160_int * const_val * (2 ** power))
                    if 0 < target_candidate < 2**160:
                        strategies.append(target_candidate)
                    
                    # Target / (constant * 2^N)
                    if power > 0:
                        target_candidate = int(self.target_hash160_int / (const_val * (2 ** power)))
                        if target_candidate > 0:
                            strategies.append(target_candidate)
        
        if strategies:
            return random.choice(strategies)
        return random.randint(1, 2**160 - 1)

class AdaptiveHexManager:
    """Simplified adaptive hex manager with mathematical generation"""
    
    def __init__(self, config: DeathNoteConfig, math_finder: MathematicalRelationshipFinder):
        self.config = config
        self.math_finder = math_finder
        
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.position_weights = np.ones(32, dtype=np.float32)
        self.generation_count = 0
        self.range_performance = {}
        
        print(f"🧠 Adaptive hex manager with mathematical generation")
    
    def generate_key(self) -> bytes:
        """Generate key using mathematical insights"""
        self.generation_count += 1
        
        # 60% mathematical, 40% adaptive hex
        if random.random() < 0.6:
            return self._generate_mathematical_key()
        else:
            return self._generate_adaptive_key()
    
    def _generate_mathematical_key(self) -> bytes:
        """Generate based on mathematical relationships and resonance"""
        # Get a mathematical target hash160
        target_hash160 = self.math_finder.generate_mathematical_target()
        
        # Convert to a reasonable private key range
        key_int = random.randint(1, 2**256 - 1)
        
        # Use resonance profile to guide key generation
        if self.math_finder.resonance_profile:
            primary = self.math_finder.resonance_profile['primary']
            primary_val = self.math_finder.constants[primary]
            
            # Try resonance-guided generation
            for power in range(20, 60):
                # Use the resonant constant
                potential_key = int(target_hash160 * primary_val * (2 ** power))
                if 1 <= potential_key <= 2**256 - 1:
                    # Add variation based on resonance strength
                    resonance_strength = self.math_finder.resonance_profile['top_resonances'][primary]['resonance']
                    variation_range = int(1000000 * (1 - resonance_strength))  # Less variation for stronger resonance
                    variation = random.randint(-variation_range, variation_range)
                    key_int = max(1, min(potential_key + variation, 2**256 - 1))
                    break
        else:
            # Original method if no resonance profile
            for const_name, const_val in self.math_finder.constants.items():
                for power in range(20, 60):
                    potential_key = int(target_hash160 * const_val * (2 ** power))
                    if 1 <= potential_key <= 2**256 - 1:
                        variation = random.randint(-1000000, 1000000)
                        key_int = max(1, min(potential_key + variation, 2**256 - 1))
                        break
        
        return key_int.to_bytes(32, 'big')
    
    def _generate_adaptive_key(self) -> bytes:
        """Standard adaptive generation - always 32 bytes"""
        key_bytes = [0] * 32
        
        # Always fill all 32 bytes - GA decides which should be zero
        for pos in range(32):
            if random.random() < self.position_weights[pos]:
                key_bytes[pos] = random.randint(0, 255)
            else:
                # Include 0 as a pattern option
                patterns = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF]
                key_bytes[pos] = random.choice(patterns)
        
        key_int = int.from_bytes(bytes(key_bytes), 'big')
        return max(1, key_int).to_bytes(32, 'big')
    
    def learn_from_improvement(self, old_key: bytes, new_key: bytes, improvement: float):
        """Learn which positions are important - all 32 bytes"""
        if improvement <= 0:
            return
        
        for byte_pos in range(32):
            if old_key[byte_pos] != new_key[byte_pos]:
                self.position_weights[byte_pos] = min(
                    self.config.MAX_POSITION_WEIGHT,
                    self.position_weights[byte_pos] + improvement * self.config.POSITION_LEARNING_RATE
                )
    
    def expand_range(self):
        """Expand active bytes"""
        if self.current_active_bytes < self.config.MAX_ACTIVE_BYTES:
            self.current_active_bytes += 1
            print(f"    📈 Expanded to {self.current_active_bytes} active bytes")

class CryptoOps:
    """Crypto operations"""
    def __init__(self):
        self.engine = CRYPTO_ENGINE
    
    def private_key_to_hash160_both(self, private_key: bytes) -> Tuple[bytes, bytes]:
        """Return both compressed and uncompressed hash160s"""
        try:
            if self.engine == 'coincurve':
                privkey = coincurve.PrivateKey(private_key)
                pubkey_compressed = privkey.public_key.format(compressed=True)
                pubkey_uncompressed = privkey.public_key.format(compressed=False)
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
                
                # Compressed
                prefix = 0x02 if (y % 2 == 0) else 0x03
                x_bytes = x.to_bytes(32, 'big')
                pubkey_compressed = bytes([prefix]) + x_bytes
                
                # Uncompressed
                y_bytes = y.to_bytes(32, 'big')
                pubkey_uncompressed = bytes([0x04]) + x_bytes + y_bytes
            
            # Hash160 both
            hash160_compressed = self.hash160(pubkey_compressed)
            hash160_uncompressed = self.hash160(pubkey_uncompressed)
            
            return hash160_compressed, hash160_uncompressed
            
        except Exception:
            dummy = b'\x00' * 20
            return dummy, dummy
    
    def hash160(self, data: bytes) -> bytes:
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()

class DeathNotePureMatch:
    """Main GA engine - mathematical hunter for hash160 matches"""
    
    def __init__(self, config: DeathNoteConfig):
        self.config = config
        self.crypto = CryptoOps()
        
        # Will be initialized when target is set
        self.math_finder = None
        self.hex_manager = None
        
        # Atomics
        self.best_score = Value('f', 1.0, lock=True)
        self.exact_match_found = Value('i', 0, lock=True)
        self.total_evals = Value('L', 0, lock=True)
        self.best_key_bytes = Array('B', 32, lock=True)
        
        # Population
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.elite_scores = []
        
        self.target_hash = None
        
        # Dynamic fitness weights
        self.decimal_weight = config.INITIAL_DECIMAL_WEIGHT
        self.mathematical_weight = config.INITIAL_MATHEMATICAL_WEIGHT
        self.pure_decimal_mode = False
        self.best_math_pattern = None
        self.best_math_accuracy = 0.0
    
    def mathematical_fitness(self, private_key: bytes) -> Tuple[float, Dict]:
        """Calculate fitness using decimal + mathematical (NO HAMMING!)"""
        hash160_comp, hash160_uncomp = self.crypto.private_key_to_hash160_both(private_key)
        
        # Check for EXACT MATCH first
        if hash160_comp == self.target_hash or hash160_uncomp == self.target_hash:
            match_format = "compressed" if hash160_comp == self.target_hash else "uncompressed"
            return 0.0, {'exact_match': True, 'format': match_format}
        
        # Calculate fitness for both formats
        target_int = int.from_bytes(self.target_hash, 'big')
        comp_int = int.from_bytes(hash160_comp, 'big')
        uncomp_int = int.from_bytes(hash160_uncomp, 'big')
        private_key_int = int.from_bytes(private_key, 'big')
        
        # Decimal proximity (normalized) with full precision
        max_hash160 = 2**160
        comp_decimal_raw = abs(comp_int - target_int) / max_hash160
        uncomp_decimal_raw = abs(uncomp_int - target_int) / max_hash160
        
        # Use 1 - raw for fitness (closer to 1 is better)
        comp_decimal = 1.0 - comp_decimal_raw
        uncomp_decimal = 1.0 - uncomp_decimal_raw
        
        # Mathematical relationships (skip if in pure decimal mode)
        if not self.pure_decimal_mode:
            comp_math = self.math_finder.analyze_relationships(comp_int, private_key_int)
            uncomp_math = self.math_finder.analyze_relationships(uncomp_int, private_key_int)
            
            # Check if we found perfect math relationship
            max_math = max(comp_math['max_accuracy'], uncomp_math['max_accuracy'])
            if max_math >= self.config.MATH_PERFECT_THRESHOLD:
                self.pure_decimal_mode = True
                self.best_math_pattern = comp_math['best_pattern'] if comp_math['max_accuracy'] >= uncomp_math['max_accuracy'] else uncomp_math['best_pattern']
                self.best_math_accuracy = max_math
                print(f"\n🎯 PERFECT MATH FOUND! Switching to PURE DECIMAL mode")
                print(f"   Pattern: {self.best_math_pattern} (accuracy: {max_math:.6f})")
                print(f"   Now optimizing decimal proximity only...")
                # Update weights for pure decimal
                self.decimal_weight = 1.0
                self.mathematical_weight = 0.0
        else:
            # In pure decimal mode - don't calculate math
            comp_math = {'max_accuracy': self.best_math_accuracy, 'best_pattern': self.best_math_pattern}
            uncomp_math = {'max_accuracy': self.best_math_accuracy, 'best_pattern': self.best_math_pattern}
        
        # Combined fitness
        comp_fitness = (self.decimal_weight * comp_decimal + 
                       self.mathematical_weight * comp_math['max_accuracy'])
        uncomp_fitness = (self.decimal_weight * uncomp_decimal + 
                         self.mathematical_weight * uncomp_math['max_accuracy'])
        
        # Use best format
        if comp_fitness >= uncomp_fitness:
            final_score = 1.0 - comp_fitness
            details = {
                'exact_match': False,
                'format': 'compressed',
                'decimal_fitness': comp_decimal,
                'math_fitness': comp_math['max_accuracy'],
                'math_pattern': comp_math['best_pattern'],
                'decimal_diff': abs(comp_int - target_int)
            }
        else:
            final_score = 1.0 - uncomp_fitness
            details = {
                'exact_match': False,
                'format': 'uncompressed', 
                'decimal_fitness': uncomp_decimal,
                'math_fitness': uncomp_math['max_accuracy'],
                'math_pattern': uncomp_math['best_pattern'],
                'decimal_diff': abs(uncomp_int - target_int)
            }
        
        return final_score, details
    
    def score_key(self, private_key: bytes) -> float:
        """Score a key"""
        with self.total_evals.get_lock():
            self.total_evals.value += 1
        
        score, details = self.mathematical_fitness(private_key)
        
        if details['exact_match']:
            with self.exact_match_found.get_lock():
                self.exact_match_found.value = 1
            with self.best_key_bytes.get_lock():
                for i, b in enumerate(private_key):
                    self.best_key_bytes[i] = b
            
            print(f"\n🎉🎉🎉 EXACT MATCH FOUND ({details['format']})! 🎉🎉🎉")
            print(f"🔑 Private Key: 0x{int.from_bytes(private_key, 'big'):064X}")
            return 0.0
        
        # Update best
        with self.best_score.get_lock():
            if score < self.best_score.value:
                self.best_score.value = score
                with self.best_key_bytes.get_lock():
                    for i, b in enumerate(private_key):
                        self.best_key_bytes[i] = b
                
                key_int = int.from_bytes(private_key, 'big')
                if self.pure_decimal_mode:
                    # In pure decimal mode - show decimal difference with full precision
                    decimal_diff = details['decimal_diff']
                    
                    # Format based on size of difference
                    if decimal_diff == 0:
                        diff_str = "ZERO! 🎯 EXACT MATCH!"
                    elif decimal_diff < 1000:
                        diff_str = f"{decimal_diff}"
                    elif decimal_diff < 1e10:
                        diff_str = f"{decimal_diff:,}"
                    else:
                        # Scientific notation for very large numbers
                        diff_str = f"{decimal_diff:.6e}"
                    
                    # Show full precision score (up to 50 decimal places for hash160)
                    # This is needed because 2^160 ≈ 1.46 × 10^48
                    print(f"    ⭐ NEW BEST:")
                    print(f"       Score: {score:.50f}")
                    print(f"       Decimal diff: {diff_str}")
                    print(f"       Format: {details['format']} - PURE DECIMAL MODE")
                    
                    # If very close, show how many values away
                    if decimal_diff < 1000000:
                        print(f"       🎯 Only {decimal_diff:,} values away from target!")
                else:
                    print(f"    ⭐ NEW BEST: {score:.6f} "
                          f"(D:{details['decimal_fitness']:.4f}, M:{details['math_fitness']:.4f}) "
                          f"{details['format']} - {details['math_pattern']}")
        
        return score
    
    def mutate_key(self, key: bytes, strength: float) -> bytes:
        """Mutate with mathematical awareness - let it wrap naturally"""
        if random.random() < 0.3:
            # Mathematical mutation
            return self.hex_manager.generate_key()
        
        # Standard mutation
        key_int = int.from_bytes(key, 'big')
        
        # Multiple mutation types
        mutations = []
        
        # Bit flips - anywhere in the 256-bit space
        for _ in range(random.randint(1, 3)):
            bit_pos = random.randint(0, 255)
            new_int = key_int ^ (1 << bit_pos)
            mutations.append(new_int)
        
        # Integer deltas - scale to full key space
        delta_range = int(2**256 * strength * 0.001)  # 0.1% of key space
        for _ in range(3):
            delta = random.randint(-delta_range, delta_range)
            new_int = key_int + delta
            # Let it wrap naturally with modulo
            new_int = new_int % (2**256)
            # Ensure non-zero
            if new_int == 0:
                new_int = 1
            mutations.append(new_int)
        
        if mutations:
            chosen = random.choice(mutations)
            # Wrap with modulo to ensure it fits in 32 bytes
            chosen = chosen % (2**256)
            if chosen == 0:
                chosen = 1
            return chosen.to_bytes(32, 'big')
        return key
    
    def evolve_population(self):
        """Evolve the population"""
        new_population = []
        new_scores = []
        
        for key, score in zip(self.population, self.scores):
            candidates = [key]
            
            # Mutations
            for _ in range(3):
                mutated = self.mutate_key(key, self.config.MUTATION_STRENGTH)
                candidates.append(mutated)
            
            # Crossover with elite
            if self.elite_keys and random.random() < 0.3:
                elite = random.choice(self.elite_keys)
                child = bytearray(32)
                for i in range(self.hex_manager.current_active_bytes):
                    child[i] = key[i] if random.random() < 0.5 else elite[i]
                candidates.append(bytes(child))
            
            # Fresh mathematical generation
            if random.random() < 0.2:
                candidates.append(self.hex_manager.generate_key())
            
            # Find best candidate
            best_candidate = key
            best_score = score
            
            for candidate in candidates:
                cand_score = self.score_key(candidate)
                
                if self.exact_match_found.value:
                    return True  # Found match!
                
                if cand_score < best_score:
                    improvement = best_score - cand_score
                    self.hex_manager.learn_from_improvement(key, candidate, improvement)
                    best_candidate = candidate
                    best_score = cand_score
            
            new_population.append(best_candidate)
            new_scores.append(best_score)
        
        self.population = new_population
        self.scores = new_scores
        return False
    
    def update_elite_pool(self):
        """Update elite pool"""
        combined = list(zip(self.scores, self.population))
        combined.sort(key=lambda x: x[0])
        
        self.elite_scores = []
        self.elite_keys = []
        
        seen = set()
        for score, key in combined[:self.config.ELITE_SIZE]:
            if bytes(key) not in seen:
                self.elite_keys.append(key)
                self.elite_scores.append(score)
                seen.add(bytes(key))
    
    def run_optimization(self, target_hash_hex: str, max_rounds: int) -> Dict:
        """Run the optimization"""
        try:
            self.target_hash = bytes.fromhex(target_hash_hex.replace('0x', ''))
            if len(self.target_hash) != 20:
                raise ValueError("Target must be 40 hex characters")
        except Exception as e:
            return {'error': str(e)}
        
        # Initialize components
        target_int = int.from_bytes(self.target_hash, 'big')
        self.math_finder = MathematicalRelationshipFinder(target_int, self.config)
        self.hex_manager = AdaptiveHexManager(self.config, self.math_finder)
        
        print(f"🎯 Target: {target_hash_hex}")
        print(f"🧮 Starting DeathNote mathematical hunt...")
        print(f"🎵 Using resonance-guided search based on target's mathematical profile")
        
        start_time = time.time()
        
        # Initialize population
        print(f"🧬 Initializing {self.config.K_POOL} mathematically-informed keys...")
        for _ in range(self.config.K_POOL):
            key = self.hex_manager.generate_key()
            score = self.score_key(key)
            
            if self.exact_match_found.value:
                return self._create_results(start_time, True)
            
            self.population.append(key)
            self.scores.append(score)
        
        self.update_elite_pool()
        print(f"🎯 Initial best: {min(self.scores):.6f}")
        
        # Main loop
        for round_num in range(max_rounds):
            print(f"\n🔄 Round {round_num + 1}/{max_rounds}")
            
            # Evolve
            found_match = self.evolve_population()
            if found_match:
                return self._create_results(start_time, True)
            
            # Update components
            self.update_elite_pool()
            
            # Show stats
            with self.best_score.get_lock():
                global_best = self.best_score.value
            
            elite_fitness = statistics.mean([1.0 - s for s in self.elite_scores[:50]])
            
            if self.pure_decimal_mode:
                # Show current decimal difference for tracking
                with self.best_key_bytes.get_lock():
                    current_best_key = bytes(self.best_key_bytes[:32])
                
                # Get current best's actual decimal difference
                hash160_comp, hash160_uncomp = self.crypto.private_key_to_hash160_both(current_best_key)
                target_int = int.from_bytes(self.target_hash, 'big')
                comp_diff = abs(int.from_bytes(hash160_comp, 'big') - target_int)
                uncomp_diff = abs(int.from_bytes(hash160_uncomp, 'big') - target_int)
                best_diff = min(comp_diff, uncomp_diff)
                
                # Show with appropriate precision (up to 50 decimals for hash160)
                print(f"   Best score: {global_best:.50f} | Mode: PURE DECIMAL")
                print(f"   Decimal diff: {best_diff if best_diff < 1e10 else f'{best_diff:.6e}'}")
                if best_diff < 1000000:
                    print(f"   🎯 Distance: Only {best_diff:,} values away!")
                print(f"   Elite fitness: {elite_fitness:.6f}")
                print(f"   Math pattern locked: {self.best_math_pattern}")
            else:
                print(f"   Best: {global_best:.6f} | Mode: Math+Decimal")
                print(f"   Elite fitness: {elite_fitness:.4f}")
                print(f"   Weights: D={self.decimal_weight:.2f}, M={self.mathematical_weight:.2f}")
            
            # No need to expand range - always using 32 bytes
            # Just show periodic mathematical discoveries
            if round_num % 10 == 0 and not self.pure_decimal_mode:
                patterns = self.math_finder.discovered_patterns[-5:]
                if patterns:
                    print(f"   🧮 Recent patterns: {[p['pattern'] for p in patterns]}")
        
        return self._create_results(start_time, False)
    
    def _create_results(self, start_time: float, found_match: bool) -> Dict:
        """Create results"""
        total_time = time.time() - start_time
        
        with self.best_score.get_lock():
            final_score = self.best_score.value
        with self.total_evals.get_lock():
            total_evals = self.total_evals.value
        with self.best_key_bytes.get_lock():
            best_key = bytes(self.best_key_bytes[:32])
        
        return {
            'target_hash': self.target_hash.hex(),
            'exact_match_found': found_match,
            'best_score': final_score,
            'best_key_hex': best_key.hex(),
            'best_key_int': f"0x{int.from_bytes(best_key, 'big'):064X}",
            'total_evaluations': total_evals,
            'total_time': total_time,
            'evals_per_second': total_evals / total_time if total_time > 0 else 0,
            'active_bytes': self.hex_manager.current_active_bytes
        }

def run_deathnote_pure():
    """Run DeathNote Pure Match"""
    print(f"💀 DEATHNOTE PURE MATCH - MATHEMATICAL HASH160 HUNTER")
    print(f"="*60)
    print(f"🧮 Uses mathematical relationships to find matches")
    print(f"🎯 Decimal proximity + Mathematical patterns")
    print(f"⚡ Any match wins - collision or true key!")
    print(f"="*60)
    
    # Get inputs
    target_hash = input("\n🎯 Enter target hash160 (40 hex chars): ").strip()
    if not target_hash:
        print("❌ No target provided")
        return
    
    max_rounds_str = input("🔄 Max rounds (default 100): ").strip()
    max_rounds = int(max_rounds_str) if max_rounds_str else 100
    
    print(f"\n🚀 Starting mathematical hunt...")
    
    # Run
    config = DeathNoteConfig()
    engine = DeathNotePureMatch(config)
    results = engine.run_optimization(target_hash, max_rounds)
    
    # Results
    print(f"\n{'='*60}")
    print(f"📊 RESULTS")
    print(f"{'='*60}")
    
    if results.get('exact_match_found'):
        print(f"🎉🎉🎉 EXACT MATCH FOUND! 🎉🎉🎉")
        print(f"🔑 Private Key: {results['best_key_int']}")
        print(f"🎯 Target Hash160: {results['target_hash']}")
        print(f"✅ PUZZLE SOLVED!")
    else:
        print(f"❌ No exact match found")
        print(f"📊 Best score: {results['best_score']:.8f}")
        print(f"🔑 Best key: {results['best_key_int']}")
    
    print(f"\n⚡ Total evaluations: {results['total_evaluations']:,}")
    print(f"⏱️  Time: {results['total_time']:.1f} seconds")
    print(f"🚀 Speed: {results['evals_per_second']:,.0f} keys/second")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    run_deathnote_pure()
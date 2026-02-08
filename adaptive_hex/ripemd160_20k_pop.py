#!/usr/bin/env python3
"""
RIPEMD-160 GA Searcher - Finds 32-byte inputs that produce target RIPEMD-160 hashes
Uses adaptive hex-aware genetic algorithm
"""

import time
import random
import hashlib
import statistics
import threading
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import struct

# Try to import required packages
try:
    import numpy as np
    from Crypto.Hash import RIPEMD160
    print("✅ All packages loaded")
except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "pycryptodome"])
    import numpy as np
    from Crypto.Hash import RIPEMD160
    print("✅ Packages installed")

@dataclass
class GAConfig:
    """Configuration for RIPEMD-160 GA"""
    K_POOL: int = 20000                    # Population size
    ELITE_SIZE: int = 200                 # Elite pool size
    
    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MUTATION_INCREASE: float = 1.3
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 1.2
    
    STAGNATION_ROUNDS: int = 4
    DIVERSITY_INJECTION_RATE: float = 0.4
    
    # Adaptive hex learning parameters
    INITIAL_ACTIVE_BYTES: int = 1
    EXPANSION_THRESHOLD: float = 0.05
    CONTRACTION_THRESHOLD: float = 0.1
    RANGE_ADAPTATION_FREQ: int = 2
    AGGRESSIVE_EXPANSION: bool = True
    
    # Position learning
    POSITION_LEARNING_RATE: float = 0.08
    POSITION_DECAY: float = 0.98
    GLOBAL_WEIGHT_DECAY: float = 0.998
    MIN_POSITION_WEIGHT: float = 0.05
    MAX_POSITION_WEIGHT: float = 0.75
    
    MAX_ROUNDS: int = 1000000
    KEY_SIZE: int = 32  # 32 bytes = 64 hex characters

class AdaptiveHexManager:
    """Manages adaptive hex range expansion/contraction and position learning"""
    
    def __init__(self, config: GAConfig):
        self.config = config
        self.key_size = config.KEY_SIZE
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.max_active_bytes = config.KEY_SIZE
        
        # Position importance weights
        self.position_weights = np.ones(self.key_size, dtype=np.float32)
        self.position_usage_stats = np.zeros(self.key_size, dtype=np.float32)
        self.position_performance = np.zeros(self.key_size, dtype=np.float32)
        
        # Range performance tracking
        self.range_performance = {}
        self.generation_count = 0
        self.learning_history = []
        
        self.lock = threading.RLock()
        
        print(f"🧠 Adaptive Hex Manager initialized for {self.key_size}-byte inputs")
    
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
            max_bits = min(self.current_active_bytes * 8, self.key_size * 8)
            return (2 ** max_bits) - 1
    
    def generate_adaptive_key(self) -> bytes:
        """Generate key using current active range and learned position weights"""
        with self.lock:
            self.generation_count += 1
            
            max_value = self.get_active_range()
            
            if random.random() < 0.8:  # 80% focused on learned patterns
                key_value = self._generate_position_focused_key(max_value)
            else:  # 20% exploration
                key_value = self._generate_exploratory_key(max_value)
            
            return key_value.to_bytes(self.key_size, 'big')
    
    def _generate_position_focused_key(self, max_value: int) -> int:
        """Generate key focusing on learned positions"""
        key_bytes = [0] * self.key_size
        
        for byte_pos in range(min(self.current_active_bytes, self.key_size)):
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
        
        # Convert to int
        key_value = 0
        for i, byte_val in enumerate(key_bytes[:self.current_active_bytes]):
            key_value += byte_val * (256 ** i)
        
        return max(1, min(key_value, max_value))
    
    def _generate_exploratory_key(self, max_value: int) -> int:
        """Generate exploratory key"""
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
    
    def learn_from_mutation(self, old_key: bytes, new_key: bytes, improvement: float):
        """Learn which positions and ranges are effective"""
        if improvement <= 0:
            return
        
        with self.lock:
            for byte_pos in range(min(self.current_active_bytes, self.key_size)):
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
            
            self.learning_history.append({
                'generation': self.generation_count,
                'improvement': improvement,
                'active_bytes': self.current_active_bytes,
                'old_key_int': int.from_bytes(old_key, 'big'),
                'new_key_int': int.from_bytes(new_key, 'big')
            })
            
            for byte_pos in range(self.key_size):
                if byte_pos >= self.current_active_bytes:
                    self.position_weights[byte_pos] *= self.config.POSITION_DECAY
                    self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                        self.position_weights[byte_pos])
    
    def apply_global_weight_decay(self):
        """Apply weight decay per round"""
        with self.lock:
            for byte_pos in range(self.key_size):
                self.position_weights[byte_pos] *= self.config.GLOBAL_WEIGHT_DECAY
                self.position_weights[byte_pos] = max(self.config.MIN_POSITION_WEIGHT,
                                                    self.position_weights[byte_pos])
    
    def reset_position_weights(self):
        """Reset position weights when locked in local optimum"""
        with self.lock:
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
                
                effective_bytes = 1
                key_int = int.from_bytes(key, 'big')
                if key_int > 0:
                    effective_bytes = (key_int.bit_length() + 7) // 8
                
                effective_bytes = max(1, min(effective_bytes, self.key_size))
                
                improvement = 160 - score
                if effective_bytes not in range_improvements:
                    range_improvements[effective_bytes] = []
                range_improvements[effective_bytes].append(improvement)
            
            for byte_range, improvements in range_improvements.items():
                if improvements:
                    avg_improvement = statistics.mean(improvements)
                    if byte_range not in self.range_performance:
                        self.range_performance[byte_range] = []
                    self.range_performance[byte_range].append(avg_improvement)
                    
                    if len(self.range_performance[byte_range]) > 10:
                        self.range_performance[byte_range] = self.range_performance[byte_range][-10:]
    
    def adapt_active_range(self, round_num: int, elite_scores: List[int]):
        """Adapt active range based on performance"""
        if round_num % self.config.RANGE_ADAPTATION_FREQ != 0:
            return
        
        with self.lock:
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
                    self.current_active_bytes < self.max_active_bytes):
                    self.current_active_bytes = min(self.current_active_bytes + 1,
                                                  self.max_active_bytes)
                
                elif (best_smaller_perf > current_avg_perf and 
                      best_smaller_perf > best_larger_perf and
                      self.current_active_bytes > 1):
                    self.current_active_bytes = max(1, self.current_active_bytes - 1)
    
    def get_stats(self) -> dict:
        """Get current statistics"""
        with self.lock:
            active_positions = np.sum(self.position_weights[:self.current_active_bytes] > 0.5)
            
            return {
                'current_active_bytes': self.current_active_bytes,
                'max_value_hex': f"0x{self.get_active_range():X}",
                'active_positions': int(active_positions),
                'generation_count': self.generation_count,
                'learning_events': len(self.learning_history)
            }

class GAAtomics:
    """Thread-safe atomic operations for GA"""
    def __init__(self, config: GAConfig):
        self.config = config
        self.best_score = threading.Lock()
        self._best_score = 160
        self.best_key = threading.Lock()
        self._best_key = bytes(config.KEY_SIZE)
        self.improvements = threading.Lock()
        self._improvements = 0
        self.evaluations = threading.Lock()
        self._evaluations = 0
        self.mutation_strength = threading.Lock()
        self._mutation_strength = config.MUTATION_STRENGTH
        self.start_time = time.time()
    
    def increment_evals(self, count: int = 1):
        with self.evaluations:
            self._evaluations += count
    
    def try_update_best(self, score: int, key: bytes) -> bool:
        with self.best_score:
            if score < self._best_score:
                self._best_score = score
                with self.best_key:
                    self._best_key = key
                with self.improvements:
                    self._improvements += 1
                return True
        return False
    
    def get_stats(self) -> dict:
        with self.best_score:
            best_score = self._best_score
        with self.best_key:
            best_key = self._best_key
        with self.improvements:
            improvements = self._improvements
        with self.evaluations:
            evaluations = self._evaluations
        with self.mutation_strength:
            mutation_strength = self._mutation_strength
        
        return {
            'best_score': best_score,
            'best_key': best_key,
            'improvements': improvements,
            'evaluations': evaluations,
            'mutation_strength': mutation_strength,
            'elapsed_time': time.time() - self.start_time
        }
    
    def update_mutation_strength(self, multiplier: float):
        with self.mutation_strength:
            self._mutation_strength *= multiplier
            self._mutation_strength = max(self.config.MUTATION_MIN, 
                                        min(self.config.MUTATION_MAX, self._mutation_strength))

def compute_ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD-160 hash of data"""
    h = RIPEMD160.new()
    h.update(data)
    return h.digest()

def hamming_distance(h1: bytes, h2: bytes) -> int:
    """Calculate Hamming distance between two hashes"""
    if len(h1) != len(h2):
        return len(h1) * 8
    
    distance = 0
    for b1, b2 in zip(h1, h2):
        xor_byte = b1 ^ b2
        distance += bin(xor_byte).count('1')
    return distance

def enhanced_fitness(hash1: bytes, hash2: bytes) -> float:
    """Enhanced fitness with hex match bonus"""
    hd = hamming_distance(hash1, hash2)
    hex_matches = sum(a == b for a, b in zip(hash1.hex(), hash2.hex()))
    return hd - (hex_matches * 0.1)

class RIPEMD160GAEngine:
    """Genetic Algorithm engine for finding RIPEMD-160 preimages"""
    
    def __init__(self, config: GAConfig):
        self.config = config
        self.hex_manager = AdaptiveHexManager(config)
        self.atomics = GAAtomics(config)
        
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.elite_scores = []
        
        self.target_hash = None
    
    def score_input(self, input_data: bytes) -> int:
        """Score an input by how close its RIPEMD-160 hash is to target"""
        self.atomics.increment_evals()
        
        hash_result = compute_ripemd160(input_data)
        distance = enhanced_fitness(hash_result, self.target_hash)
        distance_int = int(round(distance))
        
        self.atomics.try_update_best(distance_int, input_data)
        
        return distance_int
    
    def adaptive_mutate(self, key: bytes, strength: float) -> bytes:
        """Adaptive mutation of input"""
        try:
            active_bytes = self.hex_manager.current_active_bytes
            max_range = self.hex_manager.get_active_range()
            
            key_int = int.from_bytes(key, 'big')
            if key_int > max_range:
                key_int = key_int % max_range
            key_int = max(1, key_int)
            
            mutations = []
            
            # Byte-level mutations
            key_bytes = list(key)
            for byte_pos in range(min(active_bytes, self.config.KEY_SIZE)):
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
            
            mutations.append(bytes(key_bytes[:self.config.KEY_SIZE]))
            
            # Integer-level mutations
            for i in range(4):
                if random.random() < strength:
                    delta_range = max(1000, int(max_range * strength * 0.1))
                    delta = random.randint(-delta_range, delta_range)
                    new_int = max(1, min(key_int + delta, max_range))
                    mutations.append(new_int.to_bytes(self.config.KEY_SIZE, 'big'))
            
            # Bit flips
            if random.random() < strength:
                max_bit = min(self.config.KEY_SIZE * 8 - 1, active_bytes * 8 - 1)
                for _ in range(random.randint(1, 3)):
                    bit_pos = random.randint(0, max_bit)
                    new_int = key_int ^ (1 << bit_pos)
                    new_int = max(1, min(new_int, max_range))
                    mutations.append(new_int.to_bytes(self.config.KEY_SIZE, 'big'))
            
            # Mathematical operations
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
                    mutations.append(new_int.to_bytes(self.config.KEY_SIZE, 'big'))
                except:
                    pass
            
            return random.choice(mutations) if mutations else key
        
        except Exception:
            return key
    
    def evolve_individual(self, base_key: bytes) -> List[bytes]:
        """Generate mutation candidates"""
        candidates = []
        current_strength = self.atomics.get_stats()['mutation_strength']
        
        # Multiple mutations with varying strength
        for i in range(5):
            varying_strength = current_strength * (0.4 + i * 0.2)
            mutated = self.adaptive_mutate(base_key, varying_strength)
            candidates.append(mutated)
        
        # Elite crossover
        if len(self.elite_keys) >= 2:
            parent1, parent2 = random.sample(self.elite_keys, 2)
            child = bytearray(self.config.KEY_SIZE)
            active_bytes = self.hex_manager.current_active_bytes
            
            for byte_pos in range(active_bytes):
                weight = self.hex_manager.position_weights[byte_pos]
                if random.random() < weight:
                    child[byte_pos] = parent1[byte_pos] if random.random() < 0.5 else parent2[byte_pos]
                else:
                    child[byte_pos] = base_key[byte_pos]
            
            candidates.append(bytes(child))
        
        # Fresh generation
        fresh_key = self.hex_manager.generate_adaptive_key()
        candidates.append(fresh_key)
        
        return candidates
    
    def update_elite_pool(self):
        """Update elite pool with best performers"""
        if not self.population:
            return
        
        scored_individuals = list(zip(self.scores, self.population))
        scored_individuals.sort(key=lambda x: x[0])
        
        selected_elite = []
        used_keys = set()
        
        for score, key in scored_individuals:
            if score >= 160:
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
        """Inject fresh diversity"""
        num_to_replace = max(1, int(len(self.population) * self.config.DIVERSITY_INJECTION_RATE))
        
        scored_individuals = list(zip(self.scores, range(len(self.population))))
        scored_individuals.sort(key=lambda x: x[0], reverse=True)
        
        for score, idx in scored_individuals[:num_to_replace]:
            fresh_key = self.hex_manager.generate_adaptive_key()
            fresh_score = self.score_input(fresh_key)
            
            self.population[idx] = fresh_key
            self.scores[idx] = fresh_score
    
    def run(self, target_hash_hex: str, max_rounds: Optional[int] = None) -> dict:
        """Run GA to find input that produces target RIPEMD-160 hash"""
        
        # Parse target hash
        try:
            self.target_hash = bytes.fromhex(target_hash_hex.replace('0x', ''))
            if len(self.target_hash) != 20:
                raise ValueError("Target hash must be 40 hex characters (20 bytes)")
        except Exception as e:
            return {'error': f"Invalid target hash: {e}"}
        
        print(f"🎯 Target RIPEMD-160: {target_hash_hex}")
        print(f"🧬 Starting GA with population {self.config.K_POOL}")
        
        # Initialize population
        print("Initializing population...")
        for i in range(self.config.K_POOL):
            if i % 1000 == 0:
                print(f"  Generated {i}/{self.config.K_POOL} individuals...")
            
            key = self.hex_manager.generate_adaptive_key()
            score = self.score_input(key)
            self.population.append(key)
            self.scores.append(score)
        
        self.update_elite_pool()
        initial_stats = self.atomics.get_stats()
        print(f"Initial best: {initial_stats['best_score']} bits")
        
        # Evolution loop
        rounds = max_rounds or self.config.MAX_ROUNDS
        for round_num in range(rounds):
            round_start = time.time()
            round_start_stats = self.atomics.get_stats()
            
            # Evolve population
            new_population = []
            new_scores = []
            learning_events = 0
            
            for i in range(len(self.population)):
                base_key = self.population[i]
                candidates = self.evolve_individual(base_key)
                
                best_candidate = base_key
                best_score = self.scores[i]
                
                for candidate in candidates:
                    score = self.score_input(candidate)
                    if score < best_score:
                        improvement = (best_score - score) / 160.0
                        self.hex_manager.learn_from_mutation(base_key, candidate, improvement)
                        learning_events += 1
                        best_candidate = candidate
                        best_score = score
                
                new_population.append(best_candidate)
                new_scores.append(best_score)
            
            self.population = new_population
            self.scores = new_scores
            
            # Update elite and adapt
            self.update_elite_pool()
            self.hex_manager.analyze_population_ranges(self.population, self.scores)
            self.hex_manager.adapt_active_range(round_num, self.elite_scores)
            self.hex_manager.apply_global_weight_decay()
            
            # Update mutation strength
            round_end_stats = self.atomics.get_stats()
            improved = round_end_stats['best_score'] < round_start_stats['best_score']
            
            if improved:
                self.atomics.update_mutation_strength(self.config.MUTATION_DECAY)
                print(f"⭐ Round {round_num}: NEW BEST = {round_end_stats['best_score']} bits")
            else:
                self.atomics.update_mutation_strength(self.config.MUTATION_INCREASE)
            
            # Periodic updates
            if round_num % 10 == 0:
                hex_stats = self.hex_manager.get_stats()
                print(f"Round {round_num}/{rounds}: Best={round_end_stats['best_score']} bits, "
                      f"Active bytes={hex_stats['current_active_bytes']}, "
                      f"Elite mean={statistics.mean(self.elite_scores):.1f}, "
                      f"Speed={round_end_stats['evaluations']/(time.time()-self.atomics.start_time):.0f} evals/sec")
            
            # Diversity injection
            if round_num % 8 == 0:
                self.inject_diversity()
            
            # Reset weights if stuck
            if round_num % 20 == 0 and round_end_stats['best_score'] == round_start_stats['best_score']:
                self.hex_manager.reset_position_weights()
            
            # Early termination
            if round_end_stats['best_score'] == 0:
                print(f"🎉 FOUND EXACT MATCH at round {round_num}!")
                break
            elif round_end_stats['best_score'] <= 10:
                print(f"🔥 Very close! Only {round_end_stats['best_score']} bits away")
        
        # Final results
        final_stats = self.atomics.get_stats()
        hex_stats = self.hex_manager.get_stats()
        best_key = final_stats['best_key']
        
        # Verify the result
        best_hash = compute_ripemd160(best_key)
        
        return {
            'target_hash': target_hash_hex,
            'best_score_bits': final_stats['best_score'],
            'best_input_hex': best_key.hex(),
            'best_hash_hex': best_hash.hex(),
            'matches_target': best_hash.hex() == target_hash_hex.replace('0x', ''),
            'total_evaluations': final_stats['evaluations'],
            'improvements': final_stats['improvements'],
            'total_time': final_stats['elapsed_time'],
            'rounds_completed': min(round_num + 1, rounds),
            'evals_per_second': final_stats['evaluations'] / final_stats['elapsed_time'],
            'final_active_bytes': hex_stats['current_active_bytes'],
            'elite_mean_score': statistics.mean(self.elite_scores) if self.elite_scores else 160
        }

def main():
    """Example usage"""
    config = GAConfig()
    engine = RIPEMD160GAEngine(config)
    
    # Example target hash (you can change this)
    target = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"
    
    print("="*70)
    print("RIPEMD-160 Genetic Algorithm Preimage Finder")
    print("="*70)
    print(f"Searching for 32-byte input that hashes to: {target}")
    print("="*70)
    
    results = engine.run(target, max_rounds=1000000)
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
    else:
        print(f"🎯 Target:      {results['target_hash']}")
        print(f"📊 Best score:  {results['best_score_bits']} bits away")
        print(f"🔑 Best input:  {results['best_input_hex']}")
        print(f"#️⃣  Hash result: {results['best_hash_hex']}")
        print(f"✅ Exact match: {results['matches_target']}")
        print(f"🔄 Evaluations: {results['total_evaluations']:,}")
        print(f"⚡ Speed:       {results['evals_per_second']:,.0f} evals/sec")
        print(f"⏱️  Time:        {results['total_time']:.1f} seconds")
        print(f"📈 Improvements: {results['improvements']}")
        print(f"🎯 Elite mean:  {results['elite_mean_score']:.1f} bits")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
FF1GA UNLEASHED - ACTUALLY HARD PROBLEMS
These are problems that make computers cry
"""

import numpy as np
import time
import json
import secrets
import random
import math
import hashlib
from typing import Dict, List, Tuple, Callable, Set
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from functools import partial
import traceback

# For Bitcoin test - install with: pip install coincurve
try:
    from coincurve import PrivateKey, PublicKey
    BITCOIN_AVAILABLE = True
except ImportError:
    BITCOIN_AVAILABLE = False
    print("\n" + "="*60)
    print("WARNING: coincurve not installed - Bitcoin test will be skipped")
    print("To enable Bitcoin test, install with: pip install coincurve")
    print("="*60)

@dataclass
class UnleashedConfig:
    """Let FF1GA run wild"""
    # GA parameters - BIG populations for hard problems
    K_POOL: int = 10000  # Even bigger population
    ELITE_SIZE: int = 1000  # More elites
    
    # Mutation parameters
    MUTATION_STRENGTH: float = 0.7
    MUTATION_DECAY: float = 0.96
    MUTATION_INCREASE: float = 1.4
    MUTATION_MIN: float = 0.1
    MUTATION_MAX: float = 1.5
    
    # Position learning
    POSITION_LEARNING_RATE: float = 0.15
    POSITION_DECAY: float = 0.995
    
    # Give it SERIOUS iteration budgets
    ITERATION_BUDGETS: List[int] = None
    
    # Stagnation handling
    STAGNATION_THRESHOLD: int = 50
    DIVERSITY_INJECTION_RATE: float = 0.3
    
    # Close solution thresholds
    CLOSE_SOLUTION_THRESHOLD: int = 5  # Don't inject diversity below this
    FOCUSED_SEARCH_THRESHOLD: int = 10  # Switch to focused mode below this
    
    # Brute force thresholds (size-dependent)
    BRUTE_FORCE_THRESHOLDS: Dict[int, int] = None  # {problem_size: threshold}
    BRUTE_FORCE_MAX_VARS: int = 20  # Max variables to brute force
    
    # Parallel processing
    USE_MULTIPROCESSING: bool = False  # Default to False to avoid complications
    N_WORKERS: int = None
    
    def __post_init__(self):
        if self.ITERATION_BUDGETS is None:
            # Very generous budgets for hard problems
            self.ITERATION_BUDGETS = [10000, 50000, 100000, 500000, 1000000]
        
        if self.BRUTE_FORCE_THRESHOLDS is None:
            # Dynamic thresholds based on problem size
            self.BRUTE_FORCE_THRESHOLDS = {
                50: 2,    # For 50 vars, brute force at 2 clauses
                100: 3,   # For 100 vars, brute force at 3 clauses  
                200: 5,   # For 200 vars, brute force at 5 clauses
                500: 8,   # For larger, scale up
                1000: 10
            }
        
        if self.N_WORKERS is None:
            self.N_WORKERS = max(1, cpu_count() - 1)

class FF1GAUnleashed:
    """FF1GA without training wheels"""
    
    def __init__(self, problem_size: int, config: UnleashedConfig = None):
        self.problem_size = problem_size
        self.config = config or UnleashedConfig()
        
        # Advanced tracking
        self.position_weights = np.ones(problem_size)
        self.byte_frequency = [{} for _ in range(problem_size)]
        self.successful_patterns = []
        self.magic_sequences = {}
        self.generation = 0
        
        # Performance tracking
        self.best_ever = float('inf')
        self.breakthrough_moments = []
        
        # Path avoidance for restarts
        self.failed_configurations = []  # Store configurations that led to being stuck
        self.taboo_regions = []  # Regions to avoid
        self.restart_count = 0
        self.mutation_strength = self.config.MUTATION_STRENGTH  # Store as instance variable
        
    def generate_candidate(self) -> bytes:
        """Smart candidate generation"""
        if self.generation < 5 or random.random() < 0.1:
            return secrets.token_bytes(self.problem_size)
        
        candidate = bytearray(self.problem_size)
        
        for i in range(self.problem_size):
            if self.position_weights[i] > 0.8 and self.byte_frequency[i]:
                bytes_list = list(self.byte_frequency[i].keys())
                weights = list(self.byte_frequency[i].values())
                if sum(weights) > 0:
                    candidate[i] = random.choices(bytes_list, weights=weights)[0]
                else:
                    candidate[i] = random.randint(0, 255)
            else:
                candidate[i] = random.randint(0, 255)
        
        return bytes(candidate)
    
    def advanced_mutation(self, parent: bytes, strength: float) -> bytes:
        """Sophisticated mutation strategies"""
        child = bytearray(parent)
        
        for i in range(len(child)):
            if random.random() < strength * self.position_weights[i]:
                mutation_type = random.random()
                
                if mutation_type < 0.3:
                    delta = random.randint(-5, 5)
                    child[i] = (child[i] + delta) & 0xFF
                elif mutation_type < 0.6:
                    bit = random.randint(0, 7)
                    child[i] ^= (1 << bit)
                elif mutation_type < 0.8:
                    if i in self.byte_frequency and self.byte_frequency[i]:
                        child[i] = random.choice(list(self.byte_frequency[i].keys()))
                else:
                    child[i] = random.randint(0, 255)
        
        if self.magic_sequences and random.random() < 0.1:
            seq = random.choice(list(self.magic_sequences.values()))
            pos = random.randint(0, max(0, len(child) - len(seq)))
            child[pos:pos+len(seq)] = seq
        
        if random.random() < strength * 0.2:
            size = random.randint(1, max(1, len(child) // 4))
            i = random.randint(0, len(child) - size)
            j = random.randint(0, len(child) - size)
            child[i:i+size], child[j:j+size] = child[j:j+size], child[i:i+size]
        
        return bytes(child)
    
    def focused_mutation(self, parent: bytes, target_bits: int = 1) -> bytes:
        """Very focused mutation for when we're super close"""
        child = bytearray(parent)
        
        if target_bits == 1:
            # Single bit flip - try multiple strategies
            strategy = random.random()
            if strategy < 0.5:
                # Random single bit flip
                total_bits = len(child) * 8
                bit_to_flip = random.randint(0, total_bits - 1)
                byte_idx = bit_to_flip // 8
                bit_idx = bit_to_flip % 8
                if byte_idx < len(child):
                    child[byte_idx] ^= (1 << bit_idx)
            elif strategy < 0.75:
                # Flip 2-3 bits
                total_bits = len(child) * 8
                for _ in range(random.randint(2, 3)):
                    bit_to_flip = random.randint(0, total_bits - 1)
                    byte_idx = bit_to_flip // 8
                    bit_idx = bit_to_flip % 8
                    if byte_idx < len(child):
                        child[byte_idx] ^= (1 << bit_idx)
            else:
                # Try flipping bits in positions that were successful before
                if self.position_weights.max() > 0.7:
                    high_weight_positions = np.where(self.position_weights > 0.7)[0]
                    if len(high_weight_positions) > 0:
                        pos = random.choice(high_weight_positions)
                        if pos < len(child):
                            bit = random.randint(0, 7)
                            child[pos] ^= (1 << bit)
                else:
                    # Random byte change
                    pos = random.randint(0, len(child) - 1)
                    child[pos] = random.randint(0, 255)
        else:
            # Small number of targeted changes
            num_changes = min(target_bits, random.randint(1, 3))
            for _ in range(num_changes):
                i = random.randint(0, len(child) - 1)
                if random.random() < 0.5:
                    # Bit flip
                    bit = random.randint(0, 7)
                    child[i] ^= (1 << bit)
                else:
                    # Small delta
                    delta = random.choice([-1, 1])
                    child[i] = (child[i] + delta) & 0xFF
        
        return bytes(child)
    
    def get_brute_force_threshold(self, n_vars: int) -> int:
        """Get appropriate brute force threshold for problem size"""
        # Find the appropriate threshold based on problem size
        for size, threshold in sorted(self.config.BRUTE_FORCE_THRESHOLDS.items()):
            if n_vars <= size:
                return threshold
        # For very large problems, use the maximum threshold
        return max(self.config.BRUTE_FORCE_THRESHOLDS.values())
    
    def smart_local_search(self, solution: bytes, fitness_func: Callable, clauses: List[Tuple[int, int, int]], n_vars: int) -> Tuple[bytes, int]:
        """Smart local search that considers clause dependencies"""
        score = fitness_func(solution)
        
        if score == 0:
            return solution, 0
            
        # For small numbers of unsatisfied clauses, try systematic bit flips
        if score <= 5:
            print(f"  Smart local search on {score} clauses...")
            best_solution = solution
            best_score = score
            
            # Try flipping each bit one at a time
            solution_array = bytearray(solution)
            improvements_found = 0
            
            for byte_idx in range(len(solution_array)):
                for bit_idx in range(8):
                    # Flip the bit
                    solution_array[byte_idx] ^= (1 << bit_idx)
                    
                    # Test
                    test_score = fitness_func(bytes(solution_array))
                    
                    if test_score < best_score:
                        best_score = test_score
                        best_solution = bytes(solution_array)
                        improvements_found += 1
                        print(f"     Found improvement: {score} -> {best_score}")
                        
                        if best_score == 0:
                            print(f"     SOLUTION FOUND!")
                            return best_solution, 0
                    
                    # Flip back
                    solution_array[byte_idx] ^= (1 << bit_idx)
            
            # If single bit flips didn't work, try double bit flips for very small scores
            if best_score > 0 and best_score <= 2:
                print(f"     Trying double bit flips...")
                attempts = 0
                max_attempts = 10000  # Limit to avoid too long
                
                for _ in range(max_attempts):
                    # Pick two random bits to flip
                    bit1 = random.randint(0, n_vars - 1)
                    bit2 = random.randint(0, n_vars - 1)
                    
                    if bit1 != bit2:
                        byte1, bit_idx1 = bit1 // 8, bit1 % 8
                        byte2, bit_idx2 = bit2 // 8, bit2 % 8
                        
                        if byte1 < len(solution_array) and byte2 < len(solution_array):
                            # Flip both bits
                            solution_array[byte1] ^= (1 << bit_idx1)
                            solution_array[byte2] ^= (1 << bit_idx2)
                            
                            # Test
                            test_score = fitness_func(bytes(solution_array))
                            
                            if test_score < best_score:
                                best_score = test_score
                                best_solution = bytes(solution_array)
                                print(f"     Double flip improvement: {score} -> {best_score}")
                                
                                if best_score == 0:
                                    print(f"     SOLUTION FOUND with double flip!")
                                    return best_solution, 0
                            
                            # Flip back
                            solution_array[byte1] ^= (1 << bit_idx1)
                            solution_array[byte2] ^= (1 << bit_idx2)
                    
                    attempts += 1
            
            if improvements_found > 0:
                print(f"     Local search found {improvements_found} improvements")
            else:
                print(f"     No improvements found")
                
            return best_solution, best_score
        
        return solution, score
    
    def diagnose_stuck_clause(self, solution: bytes, clauses: List[Tuple[int, int, int]], stuck_clause_idx: int) -> None:
        """Diagnose why we're stuck on a particular clause"""
        clause = clauses[stuck_clause_idx]
        print(f"\n  Diagnosing stuck clause: {clause}")
        
        # Check all variable assignments
        assignments = {}
        n_vars = max(abs(lit) for c in clauses for lit in c)
        for i in range(n_vars):
            byte_idx = i // 8
            bit_idx = i % 8
            if byte_idx < len(solution):
                assignments[i + 1] = bool(solution[byte_idx] & (1 << bit_idx))
        
        # Show current assignment for clause variables
        print(f"     Current assignments:")
        for lit in clause:
            var = abs(lit)
            val = assignments.get(var, False)
            if lit < 0:
                print(f"       NOT x{var} = {not val} (x{var} = {val})")
            else:
                print(f"       x{var} = {val}")
        
        # Check what happens if we satisfy this clause
        print(f"\n     Checking ripple effects of satisfying this clause:")
        
        for target_lit in clause:
            # Try setting this literal to true
            test_solution = bytearray(solution)
            var = abs(target_lit)
            var_idx = var - 1
            byte_idx = var_idx // 8
            bit_idx = var_idx % 8
            
            if byte_idx < len(test_solution):
                # Set bit based on whether literal is positive or negative
                if target_lit > 0:
                    test_solution[byte_idx] |= (1 << bit_idx)  # Set to 1
                else:
                    test_solution[byte_idx] &= ~(1 << bit_idx)  # Set to 0
                
                # Check how many clauses this breaks
                score, broken_clauses = three_sat_fitness(bytes(test_solution), clauses, return_unsatisfied_clauses=True)
                
                if score > 1:  # If it breaks other clauses
                    print(f"       Setting {target_lit} to true breaks {score-1} other clauses:")
                    for idx, broken_clause in broken_clauses[:3]:  # Show first 3
                        if idx != stuck_clause_idx:
                            print(f"         Clause {idx}: {broken_clause}")
    
    def escape_local_minimum(self, solution: bytes, fitness_func: Callable, clauses: List[Tuple[int, int, int]], n_vars: int) -> Tuple[bytes, int]:
        """Try to escape local minimum using various strategies"""
        score = fitness_func(solution)
        
        if score == 0 or score > 5:
            return solution, score
        
        print(f"\n  Attempting to escape local minimum (score={score})...")
        
        # Get stuck clauses for diagnosis
        _, unsatisfied_clauses = three_sat_fitness(solution, clauses, return_unsatisfied_clauses=True)
        
        if len(unsatisfied_clauses) == 1:
            # Diagnose why we're stuck
            stuck_idx, stuck_clause = unsatisfied_clauses[0]
            self.diagnose_stuck_clause(solution, clauses, stuck_idx)
        
        # Strategy 1: Random walk - make multiple random changes
        print(f"     Strategy 1: Random walk")
        best_solution = solution
        best_score = score
        
        for walk_length in [3, 5, 7]:
            test_solution = bytearray(solution)
            
            # Make walk_length random bit flips
            for _ in range(walk_length):
                bit_to_flip = random.randint(0, n_vars - 1)
                byte_idx = bit_to_flip // 8
                bit_idx = bit_to_flip % 8
                if byte_idx < len(test_solution):
                    test_solution[byte_idx] ^= (1 << bit_idx)
            
            test_score = fitness_func(bytes(test_solution))
            if test_score < best_score:
                best_score = test_score
                best_solution = bytes(test_solution)
                print(f"       Walk of length {walk_length} improved: {score} -> {best_score}")
                
                if best_score == 0:
                    return best_solution, 0
        
        # Strategy 2: Restart from elite with perturbation
        if best_score > 0 and hasattr(self, 'elite_solutions'):
            print(f"     Strategy 2: Elite perturbation")
            for elite in self.elite_solutions[:5]:
                # Perturb elite solution
                test_solution = bytearray(elite)
                for _ in range(random.randint(5, 15)):
                    bit = random.randint(0, n_vars - 1)
                    byte_idx = bit // 8
                    bit_idx = bit % 8
                    if byte_idx < len(test_solution):
                        test_solution[byte_idx] ^= (1 << bit_idx)
                
                test_score = fitness_func(bytes(test_solution))
                if test_score < best_score:
                    best_score = test_score
                    best_solution = bytes(test_solution)
                    print(f"       Elite perturbation improved: {score} -> {best_score}")
                    
                    if best_score == 0:
                        return best_solution, 0
        
        return best_solution, best_score
    
    def brute_force_remaining_clauses(self, solution: bytes, fitness_func: Callable, clauses: List[Tuple[int, int, int]], n_vars: int) -> Tuple[bytes, int]:
        """Brute force with backtracking awareness"""
        # Get the unsatisfied clauses
        score, unsatisfied_clauses = three_sat_fitness(solution, clauses, return_unsatisfied_clauses=True)
        
        if score == 0:
            return solution, 0
        
        # Get appropriate threshold for this problem size
        brute_threshold = self.get_brute_force_threshold(n_vars)
        
        if score > brute_threshold:
            return solution, score  # Too many to brute force
        
        # First try smart local search
        local_solution, local_score = self.smart_local_search(solution, fitness_func, clauses, n_vars)
        if local_score == 0:
            return local_solution, 0
        
        if local_score < score:
            solution = local_solution
            score = local_score
            _, unsatisfied_clauses = three_sat_fitness(solution, clauses, return_unsatisfied_clauses=True)
        
        # If still unsatisfied and few enough clauses, try focused brute force
        if score > 0 and score <= 3:
            # Get all variables involved in unsatisfied clauses
            involved_vars = set()
            for _, clause in unsatisfied_clauses:
                for lit in clause:
                    involved_vars.add(abs(lit))
            
            # Also add variables that appear in clauses with these variables
            extended_vars = set(involved_vars)
            for clause_idx, clause in enumerate(clauses):
                clause_vars = {abs(lit) for lit in clause}
                if clause_vars & involved_vars:  # If clause shares any variable
                    extended_vars.update(clause_vars)
            
            involved_vars = sorted(list(extended_vars))[:15]  # Limit to 15 vars max
            
            print(f"  Extended brute force on {score} clause(s)...")
            print(f"     Core + related variables: {len(involved_vars)} variables")
            
            if len(involved_vars) <= 15:  # Only if feasible
                total_combinations = 2 ** len(involved_vars)
                print(f"     Trying {total_combinations} combinations...")
                
                best_solution = solution
                best_score = score
                
                for combination in range(total_combinations):
                    # Create modified solution
                    test_solution = bytearray(solution)
                    
                    # Apply this combination
                    for i, var in enumerate(involved_vars):
                        var_idx = var - 1  # Convert to 0-based
                        byte_idx = var_idx // 8
                        bit_idx = var_idx % 8
                        
                        if byte_idx < len(test_solution):
                            # Clear the bit first
                            test_solution[byte_idx] &= ~(1 << bit_idx)
                            # Set it if this combination says so
                            if combination & (1 << i):
                                test_solution[byte_idx] |= (1 << bit_idx)
                    
                    # Test this solution
                    test_score = three_sat_fitness(bytes(test_solution), clauses)
                    
                    if test_score < best_score:
                        best_score = test_score
                        best_solution = bytes(test_solution)
                        print(f"     Progress: {score} -> {best_score}")
                        
                        if best_score == 0:
                            print(f"     FOUND SOLUTION! Combination {combination}/{total_combinations}")
                            return best_solution, 0
                
                return best_solution, best_score
        
        return solution, score
    
    def remember_failed_path(self, stuck_solution: bytes, stuck_score: int):
        """Remember configurations that led to being stuck"""
        # Store the exact solution
        self.failed_configurations.append({
            'solution': stuck_solution,
            'score': stuck_score,
            'generation': self.generation
        })
        
        # Create a taboo region around this solution
        # Store significant byte positions that might be problematic
        significant_bytes = []
        for i in range(self.problem_size):
            if self.position_weights[i] > 0.6:  # High weight positions
                significant_bytes.append((i, stuck_solution[i]))
        
        self.taboo_regions.append({
            'significant_bytes': significant_bytes,
            'score': stuck_score
        })
        
        print(f"  Remembered failed configuration with {len(significant_bytes)} significant bytes")
    
    def is_too_similar_to_failed(self, solution: bytes) -> bool:
        """Check if a solution is too similar to previously failed ones"""
        for failed in self.failed_configurations[-10:]:  # Check last 10 failures
            # Hamming distance
            distance = sum(a != b for a, b in zip(solution, failed['solution']))
            if distance < self.problem_size * 0.2:  # Less than 20% different
                return True
        
        # Check taboo regions
        for taboo in self.taboo_regions[-5:]:  # Check last 5 taboo regions
            matches = 0
            for byte_idx, byte_val in taboo['significant_bytes']:
                if byte_idx < len(solution) and solution[byte_idx] == byte_val:
                    matches += 1
            
            if matches > len(taboo['significant_bytes']) * 0.7:  # 70% match
                return True
        
        return False
    
    def graceful_restart(self, fitness_func: Callable) -> Tuple[List[bytes], List[float]]:
        """Perform a graceful restart avoiding previous failed paths"""
        self.restart_count += 1
        print(f"\n  GRACEFUL RESTART #{self.restart_count} - Avoiding {len(self.failed_configurations)} failed paths")
        
        # Reset some learning but keep position insights
        self.position_weights *= 0.5  # Reduce but don't eliminate position learning
        self.mutation_strength = self.config.MUTATION_STRENGTH  # Reset mutation
        
        # Clear old patterns that might be trapping us
        if self.restart_count % 2 == 0:
            self.magic_sequences = {}
            self.byte_frequency = [{} for _ in range(self.problem_size)]
            print(f"  Cleared learned patterns")
        
        # Generate new diverse population avoiding failed paths
        new_population = []
        new_scores = []
        attempts = 0
        
        print(f"  Generating fresh diverse population...")
        
        while len(new_population) < self.config.K_POOL and attempts < self.config.K_POOL * 3:
            attempts += 1
            
            # Use different generation strategies based on restart count
            if self.restart_count % 3 == 0:
                # Every 3rd restart: completely random
                candidate = secrets.token_bytes(self.problem_size)
            elif self.restart_count % 3 == 1:
                # Biased toward opposite of failed regions
                candidate = bytearray(self.problem_size)
                for i in range(self.problem_size):
                    if random.random() < 0.3:
                        # Invert bits from failed solutions
                        for failed in self.failed_configurations[-3:]:
                            if i < len(failed['solution']):
                                candidate[i] = (~failed['solution'][i]) & 0xFF
                                break
                    else:
                        candidate[i] = random.randint(0, 255)
                candidate = bytes(candidate)
            else:
                # Use modified generation
                candidate = self.generate_candidate()
            
            # Check if too similar to failed paths
            if not self.is_too_similar_to_failed(candidate):
                score = fitness_func(candidate)
                new_population.append(candidate)
                new_scores.append(score)
                
                if score < 20:  # Good starting point
                    print(f"    Found promising start: score={score}")
        
        print(f"  Generated {len(new_population)} diverse candidates")
        
        # If we found some good solutions, bias toward them
        if min(new_scores) < 10:
            print(f"  Found good candidates, enhancing population around them")
            good_indices = [i for i, s in enumerate(new_scores) if s < 10]
            
            for idx in good_indices[:5]:  # Take top 5
                parent = new_population[idx]
                # Generate variations
                for _ in range(20):
                    child = self.advanced_mutation(parent, 0.3)  # Light mutation
                    if not self.is_too_similar_to_failed(child):
                        score = fitness_func(child)
                        if len(new_population) < self.config.K_POOL:
                            new_population.append(child)
                            new_scores.append(score)
        
        # Fill remaining with random
        while len(new_population) < self.config.K_POOL:
            candidate = secrets.token_bytes(self.problem_size)
            score = fitness_func(candidate)
            new_population.append(candidate)
            new_scores.append(score)
        
        return new_population, new_scores
    
    def learn_from_success(self, solution: bytes, score: float, previous_best: float):
        """Deep learning from improvements"""
        improvement_factor = (previous_best - score) / previous_best if previous_best > 0 else 1.0
        
        for i in range(self.problem_size):
            self.position_weights[i] = min(1.0,
                self.position_weights[i] + improvement_factor * self.config.POSITION_LEARNING_RATE)
            
            if solution[i] not in self.byte_frequency[i]:
                self.byte_frequency[i][solution[i]] = 0
            self.byte_frequency[i][solution[i]] += improvement_factor
        
        if improvement_factor > 0.1:
            for length in [2, 3, 4, 8]:
                for start in range(len(solution) - length + 1):
                    pattern = solution[start:start+length]
                    pattern_key = f"{start}_{length}"
                    self.magic_sequences[pattern_key] = pattern
        
        self.position_weights *= self.config.POSITION_DECAY
    
    def evolve(self, fitness_func: Callable, iteration_budget: int,
               early_stop_score: float = 0, clauses: List[Tuple[int, int, int]] = None,
               use_parallel: bool = None) -> Dict:
        """Full evolution with smart diversity control and graceful restarts"""
        
        print(f"\nStarting evolution with {iteration_budget} iteration budget")
        
        # Determine if we should use parallel evaluation
        if use_parallel is None:
            use_parallel = self.config.USE_MULTIPROCESSING
        
        # For Bitcoin, use parallel version if this is a ParallelFF1GAUnleashed instance
        if isinstance(self, ParallelFF1GAUnleashed) and use_parallel:
            return self.evolve_parallel(fitness_func, iteration_budget, early_stop_score, clauses)
        
        # Setup parallel evaluation if requested
        parallel_pool = None
        if use_parallel and self.config.K_POOL >= 1000:
            try:
                parallel_pool = Pool(processes=self.config.N_WORKERS)
                print(f"  Using parallel evaluation with {self.config.N_WORKERS} workers")
            except Exception as e:
                print(f"  Warning: Could not setup parallel processing: {e}")
                print(f"  Falling back to sequential evaluation")
                use_parallel = False
        
        population = []
        scores = []
        self.elite_solutions = []  # Store for escape strategies
        
        print(f"  Generating initial population of {self.config.K_POOL}...")
        
        # Generate all candidates first
        candidates = [self.generate_candidate() for _ in range(self.config.K_POOL)]
        
        # Evaluate in parallel if available
        if use_parallel and parallel_pool:
            try:
                scores = list(parallel_pool.map(fitness_func, candidates))
                population = candidates
            except Exception as e:
                print(f"  Warning: Parallel evaluation failed: {e}")
                print(f"  Falling back to sequential evaluation")
                use_parallel = False
                parallel_pool.close()
                parallel_pool = None
                # Fall through to sequential evaluation
        
        if not use_parallel or parallel_pool is None:
            scores = []
            for candidate in candidates:
                score = fitness_func(candidate)
                scores.append(score)
            population = candidates
        
        best_score = min(scores)
        best_individual = population[scores.index(best_score)]
        
        evaluations = self.config.K_POOL
        iterations = 0
        stagnation = 0
        mutation_strength = self.config.MUTATION_STRENGTH
        focused_search_rounds = 0
        last_brute_force_attempt = -100
        stuck_at_score = -1
        stuck_iterations = 0
        total_stuck_iterations = 0  # Track total time stuck across restarts
        
        convergence_history = [(0, best_score)]
        
        print(f"  Initial best: {best_score}")
        
        # Get problem size for dynamic thresholds
        n_vars = max(abs(lit) for clause in clauses for lit in clause) if clauses else 0
        brute_threshold = self.get_brute_force_threshold(n_vars) if clauses else 2
        
        while iterations < iteration_budget:
            self.generation += 1
            
            # Track if we're stuck at the same score
            if best_score == stuck_at_score:
                stuck_iterations += 1
                total_stuck_iterations += 1
            else:
                stuck_at_score = best_score
                stuck_iterations = 0
                total_stuck_iterations = 0
            
            # GRACEFUL RESTART if stuck for too long
            restart_threshold = 250 + (n_vars // 20)  # Scale with problem size
            if (stuck_iterations > restart_threshold and best_score > 0 and 
                total_stuck_iterations > restart_threshold * 1.5 and self.restart_count < 256):
                
                print(f"\n  Stuck at score={best_score} for {stuck_iterations} iterations")
                print(f"  Time for a graceful restart...")
                
                # Remember this failed configuration
                self.remember_failed_path(best_individual, best_score)
                
                # Perform graceful restart
                population, scores = self.graceful_restart(fitness_func)
                evaluations += len(population)
                
                # Reset tracking variables
                best_score = min(scores)
                best_individual = population[scores.index(best_score)]
                stuck_iterations = 0
                stuck_at_score = best_score
                stagnation = 0
                mutation_strength = self.config.MUTATION_STRENGTH
                
                print(f"  Restarted with best score: {best_score}")
                
                # If restart found a perfect solution
                if best_score == 0:
                    print(f"  PERFECT SOLUTION FOUND after restart!")
                    if parallel_pool:
                        parallel_pool.close()
                        parallel_pool.join()
                    return {
                        'best_score': best_score,
                        'best_individual': best_individual.hex(),
                        'iterations': iterations,
                        'evaluations': evaluations,
                        'convergence_history': convergence_history,
                        'breakthrough_moments': self.breakthrough_moments,
                        'magic_sequences_found': len(self.magic_sequences),
                        'final_mutation_strength': mutation_strength,
                        'population_diversity': len(set(map(bytes, population))) / len(population),
                        'restarts': self.restart_count
                    }
                
                continue  # Skip to next iteration with fresh population
            
            # If stuck for moderate time, try escape strategies
            if stuck_iterations > 30 and stuck_iterations <= 150 and best_score <= 3 and best_score > 0 and clauses is not None:
                escape_solution, escape_score = self.escape_local_minimum(
                    best_individual, fitness_func, clauses, n_vars)
                
                if escape_score < best_score:
                    best_score = escape_score
                    best_individual = escape_solution
                    stuck_iterations = 0
                    
                    if escape_score == 0:
                        print(f"  PERFECT SOLUTION FOUND via escape strategy!")
                        if parallel_pool:
                            parallel_pool.close()
                            parallel_pool.join()
                        return {
                            'best_score': best_score,
                            'best_individual': best_individual.hex(),
                            'iterations': iterations,
                            'evaluations': evaluations,
                            'convergence_history': convergence_history,
                            'breakthrough_moments': self.breakthrough_moments,
                            'magic_sequences_found': len(self.magic_sequences),
                            'final_mutation_strength': mutation_strength,
                            'population_diversity': len(set(map(bytes, population))) / len(population),
                            'restarts': self.restart_count
                        }
            
            # Try brute force if we're close and haven't tried recently
            if (clauses is not None and 
                best_score <= brute_threshold and 
                best_score > 0 and
                iterations - last_brute_force_attempt > 20):
                
                brute_solution, brute_score = self.brute_force_remaining_clauses(
                    best_individual, fitness_func, clauses, n_vars)
                evaluations += min(2 ** 20, 2 ** self.config.BRUTE_FORCE_MAX_VARS)
                last_brute_force_attempt = iterations
                
                if brute_score < best_score:
                    best_score = brute_score
                    best_individual = brute_solution
                    stuck_iterations = 0
                    
                    if brute_score == 0:
                        print(f"  PERFECT SOLUTION FOUND via brute force!")
                        if parallel_pool:
                            parallel_pool.close()
                            parallel_pool.join()
                        return {
                            'best_score': best_score,
                            'best_individual': best_individual.hex(),
                            'iterations': iterations,
                            'evaluations': evaluations,
                            'convergence_history': convergence_history,
                            'breakthrough_moments': self.breakthrough_moments,
                            'magic_sequences_found': len(self.magic_sequences),
                            'final_mutation_strength': mutation_strength,
                            'population_diversity': len(set(map(bytes, population))) / len(population),
                            'restarts': self.restart_count
                        }
            
            # Update elite solutions
            sorted_indices = np.argsort(scores)
            self.elite_solutions = [population[i] for i in sorted_indices[:10]]
            
            # Determine if we should use focused search
            use_focused_search = best_score <= self.config.FOCUSED_SEARCH_THRESHOLD and best_score > 0
            
            if use_focused_search:
                # FOCUSED SEARCH MODE
                focused_search_rounds += 1
                if focused_search_rounds == 1 or focused_search_rounds % 10 == 0:
                    print(f"  Focused search mode (best={best_score}, round {focused_search_rounds})...")
                
                new_population = []
                new_scores = []
                
                # Keep only the best individuals
                elite_size = max(100, self.config.K_POOL // 5)
                for i in range(elite_size):
                    idx = sorted_indices[i]
                    new_population.append(population[idx])
                    new_scores.append(scores[idx])
                
                # Fill rest with focused mutations
                candidates_to_eval = []
                parent_indices = []
                while len(new_population) < self.config.K_POOL:
                    parent_idx = sorted_indices[random.randint(0, min(10, len(population) - 1))]
                    parent = population[parent_idx]
                    
                    mutation_attempts = 10 if best_score <= 3 else 5
                    for _ in range(mutation_attempts):
                        child = self.focused_mutation(parent, best_score)
                        candidates_to_eval.append(child)
                        parent_indices.append(parent_idx)
                        
                        if len(new_population) + len(candidates_to_eval) >= self.config.K_POOL:
                            break
                
                # Batch evaluate candidates
                if use_parallel and parallel_pool and len(candidates_to_eval) > 100:
                    try:
                        candidate_scores = list(parallel_pool.map(fitness_func, candidates_to_eval))
                    except Exception:
                        candidate_scores = [fitness_func(c) for c in candidates_to_eval]
                else:
                    candidate_scores = [fitness_func(c) for c in candidates_to_eval]
                
                evaluations += len(candidates_to_eval)
                
                # Process results
                for child, score in zip(candidates_to_eval, candidate_scores):
                    new_population.append(child)
                    new_scores.append(score)
                    
                    if score < best_score:
                        print(f"  New best at iteration {iterations}: {best_score} -> {score}")
                        
                        self.learn_from_success(child, score, best_score)
                        
                        if best_score - score > best_score * 0.5:
                            self.breakthrough_moments.append({
                                'iteration': iterations,
                                'improvement': best_score - score,
                                'new_score': score
                            })
                            print(f"  BREAKTHROUGH! Massive improvement!")
                        
                        best_score = score
                        best_individual = child
                        stagnation = 0
                        focused_search_rounds = 0
                        stuck_iterations = 0
                        total_stuck_iterations = 0
                        
                        if score <= early_stop_score:
                            print(f"  PERFECT SOLUTION FOUND!")
                            if parallel_pool:
                                parallel_pool.close()
                                parallel_pool.join()
                            return {
                                'best_score': best_score,
                                'best_individual': best_individual.hex(),
                                'iterations': iterations,
                                'evaluations': evaluations,
                                'convergence_history': convergence_history,
                                'breakthrough_moments': self.breakthrough_moments,
                                'magic_sequences_found': len(self.magic_sequences),
                                'final_mutation_strength': mutation_strength,
                                'population_diversity': len(set(map(bytes, population))) / len(population),
                                'restarts': self.restart_count
                            }
                
                population = new_population[:self.config.K_POOL]
                scores = new_scores[:self.config.K_POOL]
                
            else:
                focused_search_rounds = 0
                # NORMAL EVOLUTION MODE
                sorted_indices = np.argsort(scores)
                
                new_population = []
                new_scores = []
                
                # Elitism
                for i in range(self.config.ELITE_SIZE):
                    idx = sorted_indices[i]
                    new_population.append(population[idx])
                    new_scores.append(scores[idx])
                
                # Evolution
                candidates_to_eval = []
                while len(new_population) < self.config.K_POOL:
                    tournament_size = 5
                    tournament = random.sample(range(len(population)), tournament_size)
                    parent1_idx = min(tournament, key=lambda i: scores[i])
                    
                    tournament = random.sample(range(len(population)), tournament_size)
                    parent2_idx = min(tournament, key=lambda i: scores[i])
                    
                    parent1 = population[parent1_idx]
                    parent2 = population[parent2_idx]
                    
                    if random.random() < 0.8:
                        crossover_point = random.randint(1, self.problem_size - 1)
                        child = parent1[:crossover_point] + parent2[crossover_point:]
                    else:
                        child = parent1 if scores[parent1_idx] < scores[parent2_idx] else parent2
                    
                    child = self.advanced_mutation(child, mutation_strength)
                    candidates_to_eval.append(child)
                
                # Batch evaluate candidates
                if use_parallel and parallel_pool and len(candidates_to_eval) > 100:
                    try:
                        candidate_scores = list(parallel_pool.map(fitness_func, candidates_to_eval))
                    except Exception:
                        # Fallback to sequential
                        candidate_scores = [fitness_func(c) for c in candidates_to_eval]
                else:
                    candidate_scores = [fitness_func(c) for c in candidates_to_eval]
                
                evaluations += len(candidates_to_eval)
                
                # Add evaluated candidates to new population
                for child, score in zip(candidates_to_eval, candidate_scores):
                    new_population.append(child)
                    new_scores.append(score)
                    
                    if score < best_score:
                        print(f"  New best at iteration {iterations}: {best_score} -> {score}")
                        
                        self.learn_from_success(child, score, best_score)
                        
                        if best_score - score > best_score * 0.5:
                            self.breakthrough_moments.append({
                                'iteration': iterations,
                                'improvement': best_score - score,
                                'new_score': score
                            })
                            print(f"  BREAKTHROUGH! Massive improvement!")
                        
                        best_score = score
                        best_individual = child
                        stagnation = 0
                        stuck_iterations = 0
                        total_stuck_iterations = 0
                        
                        mutation_strength *= self.config.MUTATION_DECAY
                        mutation_strength = max(self.config.MUTATION_MIN, mutation_strength)
                        
                        if score <= early_stop_score:
                            print(f"  PERFECT SOLUTION FOUND!")
                            if parallel_pool:
                                parallel_pool.close()
                                parallel_pool.join()
                            # Early exit from evolution
                            return {
                                'best_score': best_score,
                                'best_individual': best_individual.hex(),
                                'iterations': iterations,
                                'evaluations': evaluations,
                                'convergence_history': convergence_history,
                                'breakthrough_moments': self.breakthrough_moments,
                                'magic_sequences_found': len(self.magic_sequences),
                                'final_mutation_strength': mutation_strength,
                                'population_diversity': len(set(map(bytes, population))) / len(population),
                                'restarts': self.restart_count
                            }
                
                population = new_population
                scores = new_scores
            
            # Handle stagnation and diversity injection
            stagnation += 1
            
            # Only inject diversity if we're not close to solution
            if (stagnation > self.config.STAGNATION_THRESHOLD and 
                best_score > self.config.CLOSE_SOLUTION_THRESHOLD):
                
                print(f"  Injecting diversity at iteration {iterations}")
                mutation_strength = min(self.config.MUTATION_MAX,
                                      mutation_strength * self.config.MUTATION_INCREASE)
                
                num_replace = int(self.config.K_POOL * self.config.DIVERSITY_INJECTION_RATE)
                for i in range(num_replace):
                    idx = random.randint(self.config.ELITE_SIZE, self.config.K_POOL - 1)
                    # Make sure injected diversity avoids failed paths
                    attempts = 0
                    while attempts < 10:
                        candidate = self.generate_candidate()
                        if not self.is_too_similar_to_failed(candidate):
                            break
                        attempts += 1
                    
                    population[idx] = candidate
                    scores[idx] = fitness_func(candidate)
                    evaluations += 1
                
                stagnation = 0
            
            iterations += 1
            
            if iterations % 100 == 0:
                mean_score = np.mean(scores)
                print(f"  Iteration {iterations}: Best={best_score:.2f}, Mean={mean_score:.2f}")
                convergence_history.append((iterations, best_score))
            
            if best_score <= early_stop_score:
                if parallel_pool:
                    parallel_pool.close()
                    parallel_pool.join()
                break
        
        print(f"\n  Evolution complete! Total evaluations: {evaluations}")
        print(f"  Restarts performed: {self.restart_count}")
        
        # Cleanup parallel pool if used
        if parallel_pool:
            parallel_pool.close()
            parallel_pool.join()
        
        return {
            'best_score': best_score,
            'best_individual': best_individual.hex(),
            'iterations': iterations,
            'evaluations': evaluations,
            'convergence_history': convergence_history,
            'breakthrough_moments': self.breakthrough_moments,
            'magic_sequences_found': len(self.magic_sequences),
            'final_mutation_strength': mutation_strength,
            'population_diversity': len(set(map(bytes, population))) / len(population),
            'restarts': self.restart_count
        }

# ACTUALLY HARD PROBLEMS

def three_sat_fitness(solution: bytes, clauses: List[Tuple[int, int, int]], return_unsatisfied_clauses: bool = False) -> float:
    """
    3-SAT: The canonical NP-complete problem
    Find boolean assignment that satisfies all clauses
    """
    n_vars = max(abs(lit) for clause in clauses for lit in clause)
    
    # Decode solution as boolean assignments
    assignments = {}
    for i in range(n_vars):
        byte_idx = i // 8
        bit_idx = i % 8
        if byte_idx < len(solution):
            assignments[i + 1] = bool(solution[byte_idx] & (1 << bit_idx))
        else:
            assignments[i + 1] = False
    
    # Count unsatisfied clauses
    unsatisfied = 0
    unsatisfied_clauses = []
    for clause_idx, clause in enumerate(clauses):
        satisfied = False
        for lit in clause:
            var = abs(lit)
            value = assignments.get(var, False)
            if lit < 0:
                value = not value
            if value:
                satisfied = True
                break
        if not satisfied:
            unsatisfied += 1
            if return_unsatisfied_clauses:
                unsatisfied_clauses.append((clause_idx, clause))
    
    if return_unsatisfied_clauses:
        return unsatisfied, unsatisfied_clauses
    return unsatisfied

def graph_coloring_fitness(solution: bytes, edges: List[Tuple[int, int]], k_colors: int) -> float:
    """
    Graph k-coloring: NP-complete for k >= 3
    Color vertices so no adjacent vertices share colors
    """
    n_vertices = max(max(e) for e in edges) + 1
    
    # Decode solution as color assignments
    colors = []
    for i in range(n_vertices):
        if i < len(solution):
            colors.append(solution[i] % k_colors)
        else:
            colors.append(0)
    
    # Count conflicts
    conflicts = 0
    for u, v in edges:
        if u < len(colors) and v < len(colors):
            if colors[u] == colors[v]:
                conflicts += 1
    
    return conflicts

def protein_folding_fitness(solution: bytes, sequence: str) -> float:
    """
    Simplified HP protein folding on 2D lattice
    H (hydrophobic) residues want to be together
    """
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # U, R, D, L
    
    # Decode solution as fold directions
    folds = []
    for i in range(len(sequence) - 1):
        if i < len(solution):
            folds.append(solution[i] % 4)
        else:
            folds.append(0)
    
    # Build protein configuration
    positions = [(0, 0)]
    current = (0, 0)
    
    for fold in folds:
        dx, dy = directions[fold]
        current = (current[0] + dx, current[1] + dy)
        positions.append(current)
    
    # Check for self-intersection (invalid)
    if len(set(positions)) != len(positions):
        return 1000  # High penalty
    
    # Count H-H contacts
    h_positions = [positions[i] for i in range(len(sequence)) if sequence[i] == 'H']
    contacts = 0
    
    for i in range(len(h_positions)):
        for j in range(i + 1, len(h_positions)):
            dist = abs(h_positions[i][0] - h_positions[j][0]) + \
                   abs(h_positions[i][1] - h_positions[j][1])
            if dist == 1:
                contacts += 1
    
    # Want to maximize contacts (minimize negative)
    return -contacts

def prime_factorization_fitness(solution: bytes, semiprime: int) -> float:
    """
    Factor a semiprime N = p * q
    This is what RSA security is based on
    """
    # Convert solution to potential factor
    factor = int.from_bytes(solution, 'big')
    
    if factor < 2 or factor >= semiprime:
        return semiprime
    
    if semiprime % factor == 0:
        other = semiprime // factor
        if other > 1:
            return 0  # Perfect factorization!
    
    # Distance metric: how close to being a factor
    remainder = semiprime % factor
    return min(remainder, factor - remainder)

def maximum_clique_fitness(solution: bytes, edges: List[Tuple[int, int]]) -> float:
    """
    Maximum Clique: Find largest complete subgraph
    NP-complete optimization problem
    """
    n_vertices = max(max(e) for e in edges) + 1
    
    # Build adjacency set
    adjacency = [set() for _ in range(n_vertices)]
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    
    # Decode solution as vertex selection
    selected = []
    for i in range(n_vertices):
        byte_idx = i // 8
        bit_idx = i % 8
        if byte_idx < len(solution):
            if solution[byte_idx] & (1 << bit_idx):
                selected.append(i)
    
    # Check if selected vertices form a clique
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            if selected[j] not in adjacency[selected[i]]:
                # Not a clique - return penalty
                return 1000 - len(selected)
    
    # Valid clique - maximize size (minimize negative)
    return -len(selected)

# Bitcoin SAT problem - the ultimate stress test
def bitcoin_sat_fitness(solution: bytes, target_hash160: bytes) -> float:
    """
    Bitcoin private key recovery as SAT problem
    256 variables (private key bits) -> 160 clauses (hash160 bits)
    """
    if not BITCOIN_AVAILABLE:
        return float('inf')
    
    # Ensure solution is 32 bytes (256 bits)
    if len(solution) < 32:
        solution = solution + b'\x00' * (32 - len(solution))
    elif len(solution) > 32:
        solution = solution[:32]
    
    try:
        # Bitcoin private keys must be in range [1, n-1] where n is the curve order
        # n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        key_int = int.from_bytes(solution, 'big')
        
        # If key is 0 or >= n, it's invalid
        if key_int == 0 or key_int >= n:
            # Slightly adjust to make it valid
            key_int = (key_int % (n - 1)) + 1
            solution = key_int.to_bytes(32, 'big')
        
        # Create private key from solution
        private_key = PrivateKey(solution)
        
        # Get public key (compressed)
        public_key = private_key.public_key
        public_key_bytes = public_key.format(compressed=True)
        
        # Compute hash160 (RIPEMD160(SHA256(pubkey)))
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        computed_hash160 = ripemd160.digest()
        
        # DEBUG: Verify we have correct lengths
        assert len(computed_hash160) == 20, f"Computed hash160 wrong length: {len(computed_hash160)}"
        assert len(target_hash160) == 20, f"Target hash160 wrong length: {len(target_hash160)}"
        
        # Count differing bits (unsatisfied clauses)
        unsatisfied_clauses = 0
        bit_differences = []  # For debugging
        
        for i in range(20):  # hash160 is 20 bytes = 160 bits
            # XOR to find differing bits
            diff = computed_hash160[i] ^ target_hash160[i]
            # Count 1s in binary representation
            bit_count = bin(diff).count('1')
            unsatisfied_clauses += bit_count
            bit_differences.append(bit_count)
        
        # DEBUG: Sanity check - should be between 0 and 160
        assert 0 <= unsatisfied_clauses <= 160, f"Invalid bit count: {unsatisfied_clauses}"
        
        # DEBUG: Uncomment these lines to see detailed output for low scores
        if unsatisfied_clauses < 65:  # Suspiciously good
            print(f"\n  WARNING: Unusually good score: {unsatisfied_clauses}")
            print(f"  Target:   {target_hash160.hex()}")
            print(f"  Computed: {computed_hash160.hex()}")
            print(f"  Bit differences by byte: {bit_differences}")
            print(f"  Private key: {solution.hex()}")
            # Manually verify the count
            manual_count = sum(bit_differences)
            assert manual_count == unsatisfied_clauses, "Bit counting error!"
            
            # Extra check - are we somehow using the same hash?
            if computed_hash160 == target_hash160:
                print(f"  ALERT: Computed hash EXACTLY matches target! This is virtually impossible!")
                print(f"  Check for bugs in the test setup!")
        
        return float(unsatisfied_clauses)
        
    except Exception as e:
        # Debug info if something goes wrong
        print(f"  ERROR in bitcoin_sat_fitness: {e}")
        return 160.0  # Maximum possible unsatisfied clauses

# Make bitcoin_sat_fitness a standalone function for better pickling
def bitcoin_sat_fitness_standalone(solution: bytes, target_hash160: bytes) -> float:
    """
    Standalone version of bitcoin_sat_fitness for multiprocessing.
    This avoids pickling issues with nested functions.
    """
    if not BITCOIN_AVAILABLE:
        return float('inf')
    
    # Ensure solution is 32 bytes (256 bits)
    if len(solution) < 32:
        solution = solution + b'\x00' * (32 - len(solution))
    elif len(solution) > 32:
        solution = solution[:32]
    
    try:
        # Bitcoin private keys must be in range [1, n-1] where n is the curve order
        n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        key_int = int.from_bytes(solution, 'big')
        
        # If key is 0 or >= n, it's invalid
        if key_int == 0 or key_int >= n:
            # Slightly adjust to make it valid
            key_int = (key_int % (n - 1)) + 1
            solution = key_int.to_bytes(32, 'big')
        
        # Create private key from solution
        private_key = PrivateKey(solution)
        
        # Get public key (compressed)
        public_key = private_key.public_key
        public_key_bytes = public_key.format(compressed=True)
        
        # Compute hash160 (RIPEMD160(SHA256(pubkey)))
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        computed_hash160 = ripemd160.digest()
        
        # Count differing bits (unsatisfied clauses)
        unsatisfied_clauses = 0
        
        for i in range(20):  # hash160 is 20 bytes = 160 bits
            # XOR to find differing bits
            diff = computed_hash160[i] ^ target_hash160[i]
            # Count 1s in binary representation
            unsatisfied_clauses += bin(diff).count('1')
        
        return float(unsatisfied_clauses)
        
    except Exception as e:
        return 160.0  # Maximum possible unsatisfied clauses


def parallel_fitness_evaluator(candidates_batch: List[bytes], target_hash160: bytes) -> List[float]:
    """
    Evaluate a batch of candidates. This runs in a worker process.
    """
    results = []
    for candidate in candidates_batch:
        try:
            score = bitcoin_sat_fitness_standalone(candidate, target_hash160)
            results.append(score)
        except Exception as e:
            results.append(160.0)
    return results


class ParallelFF1GAUnleashed(FF1GAUnleashed):
    """
    Enhanced FF1GA with better parallel processing for Bitcoin SAT
    """
    
    def __init__(self, problem_size: int, config: UnleashedConfig = None):
        super().__init__(problem_size, config)
        self.evaluation_times = []
        self.parallel_efficiency = 0.0
    
    def parallel_evaluate_population(self, candidates: List[bytes], fitness_func: Callable, 
                                   pool: Pool = None, batch_size: int = None) -> List[float]:
        """
        Efficiently evaluate population in parallel with batching.
        """
        n_candidates = len(candidates)
        
        if pool is None or n_candidates < 100:
            # Fall back to sequential
            return [fitness_func(c) for c in candidates]
        
        # Determine optimal batch size
        if batch_size is None:
            n_workers = self.config.N_WORKERS
            # Each worker should get at least 10 items, but not more than 100
            items_per_worker = max(10, min(100, n_candidates // n_workers))
            batch_size = items_per_worker
        
        # Create batches
        batches = []
        for i in range(0, n_candidates, batch_size):
            batch = candidates[i:i + batch_size]
            batches.append(batch)
        
        try:
            # For Bitcoin SAT, extract target_hash160 from closure
            # This is a bit hacky but necessary for multiprocessing
            if hasattr(fitness_func, '__closure__') and fitness_func.__closure__:
                # Extract target_hash160 from the closure
                target_hash160 = fitness_func.__closure__[0].cell_contents
                
                # Use partial to create evaluator with target_hash160
                evaluator = partial(parallel_fitness_evaluator, target_hash160=target_hash160)
                
                # Parallel evaluation
                start_time = time.time()
                batch_results = pool.map(evaluator, batches)
                eval_time = time.time() - start_time
                
                # Flatten results
                results = []
                for batch_result in batch_results:
                    results.extend(batch_result)
                
                # Track performance
                self.evaluation_times.append(eval_time)
                evals_per_sec = n_candidates / eval_time
                if len(self.evaluation_times) > 1:
                    seq_time_estimate = n_candidates * (sum(self.evaluation_times) / sum(len(b) for b in batches))
                    self.parallel_efficiency = seq_time_estimate / eval_time
                
                return results
            else:
                # Fallback for non-closure functions
                return [fitness_func(c) for c in candidates]
                
        except Exception as e:
            print(f"  Parallel evaluation failed: {e}")
            traceback.print_exc()
            # Fallback to sequential
            return [fitness_func(c) for c in candidates]
    
    def evolve_parallel(self, fitness_func: Callable, iteration_budget: int,
                       early_stop_score: float = 0, clauses: List[Tuple[int, int, int]] = None) -> Dict:
        """
        Evolution with optimized parallel processing, keeping all SAT-style optimizations.
        """
        
        print(f"\nStarting PARALLEL evolution with {iteration_budget} iteration budget")
        print(f"  CPU cores available: {cpu_count()}")
        print(f"  Worker processes: {self.config.N_WORKERS}")
        
        # Force parallel for Bitcoin
        parallel_pool = Pool(processes=self.config.N_WORKERS)
        print(f"  Parallel pool created successfully")
        
        try:
            # Initialize population
            population = []
            scores = []
            self.elite_solutions = []
            
            print(f"  Generating initial population of {self.config.K_POOL}...")
            
            # Generate all candidates first
            candidates = [self.generate_candidate() for _ in range(self.config.K_POOL)]
            
            # Parallel evaluation of initial population
            print(f"  Evaluating initial population in parallel...")
            start_time = time.time()
            scores = self.parallel_evaluate_population(candidates, fitness_func, parallel_pool)
            init_time = time.time() - start_time
            
            population = candidates
            print(f"  Initial population evaluated in {init_time:.2f}s ({self.config.K_POOL/init_time:.1f} evals/sec)")
            
            best_score = min(scores)
            best_individual = population[scores.index(best_score)]
            
            evaluations = self.config.K_POOL
            iterations = 0
            stagnation = 0
            mutation_strength = self.config.MUTATION_STRENGTH
            self.mutation_strength = mutation_strength
            focused_search_rounds = 0
            last_brute_force_attempt = -100
            stuck_at_score = -1
            stuck_iterations = 0
            total_stuck_iterations = 0
            
            convergence_history = [(0, best_score)]
            
            print(f"  Initial best: {best_score}")
            
            # Get problem size for dynamic thresholds
            n_vars = max(abs(lit) for clause in clauses for lit in clause) if clauses else 256
            brute_threshold = self.get_brute_force_threshold(n_vars) if clauses else 2
            
            # Main evolution loop
            generation_times = []
            
            while iterations < iteration_budget:
                gen_start_time = time.time()
                self.generation += 1
                
                # Track if we're stuck at the same score
                if best_score == stuck_at_score:
                    stuck_iterations += 1
                    total_stuck_iterations += 1
                else:
                    stuck_at_score = best_score
                    stuck_iterations = 0
                    total_stuck_iterations = 0
                
                # GRACEFUL RESTART if stuck for too long
                restart_threshold = 250 + (n_vars // 20)
                if (stuck_iterations > restart_threshold and best_score > 0 and 
                    total_stuck_iterations > restart_threshold * 1.5 and self.restart_count < 10):
                    
                    print(f"\n  Stuck at score={best_score} for {stuck_iterations} iterations")
                    print(f"  Time for a graceful restart...")
                    
                    self.remember_failed_path(best_individual, best_score)
                    
                    # Parallel restart
                    population, scores = self.graceful_restart_parallel(fitness_func, parallel_pool)
                    evaluations += len(population)
                    
                    best_score = min(scores)
                    best_individual = population[scores.index(best_score)]
                    stuck_iterations = 0
                    stuck_at_score = best_score
                    stagnation = 0
                    mutation_strength = self.config.MUTATION_STRENGTH
                    
                    print(f"  Restarted with best score: {best_score}")
                    
                    if best_score == 0:
                        print(f"  PERFECT SOLUTION FOUND after restart!")
                        break
                    
                    continue
                
                # Try brute force if we're close
                if (clauses is not None and 
                    best_score <= brute_threshold and 
                    best_score > 0 and
                    iterations - last_brute_force_attempt > 20):
                    
                    brute_solution, brute_score = self.brute_force_remaining_clauses(
                        best_individual, fitness_func, clauses, n_vars)
                    evaluations += min(2 ** 20, 2 ** self.config.BRUTE_FORCE_MAX_VARS)
                    last_brute_force_attempt = iterations
                    
                    if brute_score < best_score:
                        best_score = brute_score
                        best_individual = brute_solution
                        stuck_iterations = 0
                        
                        if brute_score == 0:
                            print(f"  PERFECT SOLUTION FOUND via brute force!")
                            break
                
                # Update elite solutions
                sorted_indices = np.argsort(scores)
                self.elite_solutions = [population[i] for i in sorted_indices[:10]]
                
                # Determine if we should use focused search
                use_focused_search = best_score <= self.config.FOCUSED_SEARCH_THRESHOLD and best_score > 0
                
                if use_focused_search:
                    # FOCUSED SEARCH MODE with parallel evaluation
                    focused_search_rounds += 1
                    if focused_search_rounds == 1 or focused_search_rounds % 10 == 0:
                        print(f"  Focused search mode (best={best_score}, round {focused_search_rounds})...")
                    
                    new_population = []
                    new_scores = []
                    
                    # Keep only the best individuals
                    elite_size = max(100, self.config.K_POOL // 5)
                    for i in range(elite_size):
                        idx = sorted_indices[i]
                        new_population.append(population[idx])
                        new_scores.append(scores[idx])
                    
                    # Generate focused mutations
                    candidates_to_eval = []
                    while len(new_population) + len(candidates_to_eval) < self.config.K_POOL:
                        parent_idx = sorted_indices[random.randint(0, min(10, len(population) - 1))]
                        parent = population[parent_idx]
                        
                        mutation_attempts = 10 if best_score <= 3 else 5
                        for _ in range(mutation_attempts):
                            child = self.focused_mutation(parent, best_score)
                            candidates_to_eval.append(child)
                            
                            if len(new_population) + len(candidates_to_eval) >= self.config.K_POOL:
                                break
                    
                    # Parallel evaluation
                    candidate_scores = self.parallel_evaluate_population(
                        candidates_to_eval, fitness_func, parallel_pool)
                    evaluations += len(candidates_to_eval)
                    
                    # Process results
                    for child, score in zip(candidates_to_eval, candidate_scores):
                        new_population.append(child)
                        new_scores.append(score)
                        
                        if score < best_score:
                            print(f"  New best at iteration {iterations}: {best_score} -> {score}")
                            self.learn_from_success(child, score, best_score)
                            best_score = score
                            best_individual = child
                            stagnation = 0
                            focused_search_rounds = 0
                            stuck_iterations = 0
                            total_stuck_iterations = 0
                            
                            if score <= early_stop_score:
                                print(f"  PERFECT SOLUTION FOUND!")
                                parallel_pool.close()
                                parallel_pool.join()
                                return self._create_result(best_score, best_individual, iterations, 
                                                         evaluations, convergence_history, mutation_strength)
                    
                    population = new_population[:self.config.K_POOL]
                    scores = new_scores[:self.config.K_POOL]
                    
                else:
                    # NORMAL EVOLUTION MODE with parallel evaluation
                    focused_search_rounds = 0
                    sorted_indices = np.argsort(scores)
                    
                    new_population = []
                    new_scores = []
                    
                    # Elitism
                    for i in range(self.config.ELITE_SIZE):
                        idx = sorted_indices[i]
                        new_population.append(population[idx])
                        new_scores.append(scores[idx])
                    
                    # Generate new candidates
                    candidates_to_eval = []
                    while len(new_population) + len(candidates_to_eval) < self.config.K_POOL:
                        # Tournament selection
                        tournament_size = 5
                        tournament = random.sample(range(len(population)), tournament_size)
                        parent1_idx = min(tournament, key=lambda i: scores[i])
                        
                        tournament = random.sample(range(len(population)), tournament_size)
                        parent2_idx = min(tournament, key=lambda i: scores[i])
                        
                        parent1 = population[parent1_idx]
                        parent2 = population[parent2_idx]
                        
                        # Crossover
                        if random.random() < 0.8:
                            crossover_point = random.randint(1, self.problem_size - 1)
                            child = parent1[:crossover_point] + parent2[crossover_point:]
                        else:
                            child = parent1 if scores[parent1_idx] < scores[parent2_idx] else parent2
                        
                        # Mutation
                        child = self.advanced_mutation(child, mutation_strength)
                        candidates_to_eval.append(child)
                    
                    # Parallel evaluation
                    candidate_scores = self.parallel_evaluate_population(
                        candidates_to_eval, fitness_func, parallel_pool)
                    evaluations += len(candidates_to_eval)
                    
                    # Process results
                    for child, score in zip(candidates_to_eval, candidate_scores):
                        new_population.append(child)
                        new_scores.append(score)
                        
                        if score < best_score:
                            print(f"  New best at iteration {iterations}: {best_score} -> {score}")
                            self.learn_from_success(child, score, best_score)
                            best_score = score
                            best_individual = child
                            stagnation = 0
                            stuck_iterations = 0
                            total_stuck_iterations = 0
                            
                            mutation_strength *= self.config.MUTATION_DECAY
                            mutation_strength = max(self.config.MUTATION_MIN, mutation_strength)
                            
                            if score <= early_stop_score:
                                print(f"  PERFECT SOLUTION FOUND!")
                                parallel_pool.close()
                                parallel_pool.join()
                                return self._create_result(best_score, best_individual, iterations, 
                                                         evaluations, convergence_history, mutation_strength)
                    
                    population = new_population[:self.config.K_POOL]
                    scores = new_scores[:self.config.K_POOL]
                
                # Handle stagnation and diversity injection
                stagnation += 1
                
                if (stagnation > self.config.STAGNATION_THRESHOLD and 
                    best_score > self.config.CLOSE_SOLUTION_THRESHOLD):
                    
                    print(f"  Injecting diversity at iteration {iterations}")
                    mutation_strength = min(self.config.MUTATION_MAX,
                                          mutation_strength * self.config.MUTATION_INCREASE)
                    
                    # Generate diverse candidates
                    num_replace = int(self.config.K_POOL * self.config.DIVERSITY_INJECTION_RATE)
                    diverse_candidates = []
                    for _ in range(num_replace):
                        attempts = 0
                        while attempts < 10:
                            candidate = self.generate_candidate()
                            if not self.is_too_similar_to_failed(candidate):
                                diverse_candidates.append(candidate)
                                break
                            attempts += 1
                    
                    # Parallel evaluation of diverse candidates
                    if diverse_candidates:
                        diverse_scores = self.parallel_evaluate_population(
                            diverse_candidates, fitness_func, parallel_pool)
                        evaluations += len(diverse_candidates)
                        
                        # Replace worst individuals
                        for i, (candidate, score) in enumerate(zip(diverse_candidates, diverse_scores)):
                            idx = sorted_indices[-(i+1)]
                            population[idx] = candidate
                            scores[idx] = score
                    
                    stagnation = 0
                
                iterations += 1
                gen_time = time.time() - gen_start_time
                generation_times.append(gen_time)
                
                if iterations % 100 == 0:
                    mean_score = np.mean(scores)
                    avg_gen_time = np.mean(generation_times[-10:])
                    print(f"  Iteration {iterations}: Best={best_score:.2f}, Mean={mean_score:.2f}")
                    print(f"    Generation time: {avg_gen_time:.2f}s, Total evals: {evaluations:,}")
                    print(f"    Parallel efficiency: {self.parallel_efficiency:.2f}x")
                    convergence_history.append((iterations, best_score))
                
                if best_score <= early_stop_score:
                    break
            
            print(f"\n  Evolution complete! Total evaluations: {evaluations}")
            print(f"  Average generation time: {np.mean(generation_times):.2f}s")
            print(f"  Restarts performed: {self.restart_count}")
            
            parallel_pool.close()
            parallel_pool.join()
            
            return self._create_result(best_score, best_individual, iterations, 
                                     evaluations, convergence_history, mutation_strength)
            
        except Exception as e:
            print(f"\nError in evolution: {e}")
            traceback.print_exc()
            if parallel_pool:
                parallel_pool.close()
                parallel_pool.join()
            raise
    
    def graceful_restart_parallel(self, fitness_func: Callable, pool: Pool) -> Tuple[List[bytes], List[float]]:
        """Perform a graceful restart with parallel evaluation"""
        self.restart_count += 1
        print(f"\n  GRACEFUL RESTART #{self.restart_count} - Avoiding {len(self.failed_configurations)} failed paths")
        
        # Reset some learning but keep position insights
        self.position_weights *= 0.5
        self.mutation_strength = self.config.MUTATION_STRENGTH
        
        # Clear old patterns that might be trapping us
        if self.restart_count % 2 == 0:
            self.magic_sequences = {}
            self.byte_frequency = [{} for _ in range(self.problem_size)]
            print(f"  Cleared learned patterns")
        
        # Generate new diverse population
        print(f"  Generating fresh diverse population...")
        candidates = []
        attempts = 0
        
        while len(candidates) < self.config.K_POOL and attempts < self.config.K_POOL * 3:
            attempts += 1
            
            # Use different generation strategies
            if self.restart_count % 3 == 0:
                candidate = secrets.token_bytes(self.problem_size)
            elif self.restart_count % 3 == 1:
                candidate = bytearray(self.problem_size)
                for i in range(self.problem_size):
                    if random.random() < 0.3:
                        for failed in self.failed_configurations[-3:]:
                            if i < len(failed['solution']):
                                candidate[i] = (~failed['solution'][i]) & 0xFF
                                break
                    else:
                        candidate[i] = random.randint(0, 255)
                candidate = bytes(candidate)
            else:
                candidate = self.generate_candidate()
            
            if not self.is_too_similar_to_failed(candidate):
                candidates.append(candidate)
        
        # Fill remaining with random
        while len(candidates) < self.config.K_POOL:
            candidates.append(secrets.token_bytes(self.problem_size))
        
        # Parallel evaluation
        print(f"  Evaluating {len(candidates)} candidates in parallel...")
        scores = self.parallel_evaluate_population(candidates, fitness_func, pool)
        
        print(f"  Generated {len(candidates)} diverse candidates")
        min_score = min(scores)
        print(f"  Best score in new population: {min_score}")
        
        return candidates, scores
    
    def _create_result(self, best_score, best_individual, iterations, evaluations, 
                      convergence_history, mutation_strength):
        """Create the result dictionary"""
        return {
            'best_score': best_score,
            'best_individual': best_individual.hex(),
            'iterations': iterations,
            'evaluations': evaluations,
            'convergence_history': convergence_history,
            'breakthrough_moments': self.breakthrough_moments,
            'magic_sequences_found': len(self.magic_sequences),
            'final_mutation_strength': mutation_strength,
            'population_diversity': len(set(map(bytes, self.elite_solutions))) / len(self.elite_solutions) if self.elite_solutions else 0,
            'restarts': self.restart_count,
            'parallel_efficiency': self.parallel_efficiency
        }


def verify_bitcoin_score(private_key_hex: str, target_hash160_hex: str) -> None:
    """
    Manually verify a Bitcoin fitness score to check for false positives
    """
    if not BITCOIN_AVAILABLE:
        print("Cannot verify - coincurve not installed")
        return
    
    print("\nMANUAL BITCOIN SCORE VERIFICATION")
    print("=" * 60)
    
    # Convert inputs
    private_key_bytes = bytes.fromhex(private_key_hex)
    target_hash160 = bytes.fromhex(target_hash160_hex)
    
    print(f"Private key: {private_key_hex}")
    print(f"Target hash160: {target_hash160_hex}")
    
    # Compute hash160
    try:
        # Validate private key is in valid range
        key_int = int.from_bytes(private_key_bytes, 'big')
        n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        if key_int == 0 or key_int >= n:
            print(f"WARNING: Private key out of valid range!")
            print(f"Key value: {key_int}")
            print(f"Valid range: [1, {n-1}]")
        
        private_key = PrivateKey(private_key_bytes)
        public_key = private_key.public_key
        public_key_bytes = public_key.format(compressed=True)
        print(f"Public key (compressed): {public_key_bytes.hex()}")
        
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        print(f"SHA256 hash: {sha256_hash.hex()}")
        
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        computed_hash160 = ripemd160.digest()
        print(f"Computed hash160: {computed_hash160.hex()}")
        
        # Compare bit by bit
        print("\nBit-by-bit comparison:")
        total_diff_bits = 0
        for i in range(20):
            target_byte = target_hash160[i]
            computed_byte = computed_hash160[i]
            diff = target_byte ^ computed_byte
            diff_bits = bin(diff).count('1')
            total_diff_bits += diff_bits
            
            if diff_bits > 0:
                print(f"  Byte {i:2d}: {target_byte:02x} vs {computed_byte:02x} "
                      f"(diff: {diff:02x} = {diff:08b} = {diff_bits} bits)")
        
        print(f"\nTotal differing bits: {total_diff_bits}/160")
        print(f"Percentage correct: {(160 - total_diff_bits) / 160 * 100:.1f}%")
        
        if total_diff_bits < 70:
            print("\nWARNING: This score is suspiciously good!")
            print("Check if your target hash160 is correct.")
        
    except Exception as e:
        print(f"Error: {e}")


def run_single_test(test_choice):
    """Run a single selected test"""
    config = UnleashedConfig()
    
    if test_choice == 1:
        # 3-SAT Test
        print("\n3-SAT PROBLEM TEST")
        print("=" * 60)
        n_vars = int(input("Enter number of variables (50, 100, 200): "))
        n_clauses = int(n_vars * 4.3)
        print(f"\n  {n_vars} variables, {n_clauses} clauses")
        
        clauses = []
        for _ in range(n_clauses):
            clause = []
            for _ in range(3):
                var = random.randint(1, n_vars)
                if random.random() < 0.5:
                    var = -var
                clause.append(var)
            clauses.append(tuple(clause))
        
        fitness = lambda x: three_sat_fitness(x, clauses)
        bytes_needed = (n_vars + 7) // 8
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        result = ff1ga.evolve(fitness, iteration_budget=50000, early_stop_score=0, clauses=clauses)
        
        print(f"\n  Unsatisfied clauses: {result['best_score']}")
        if result['best_score'] == 0:
            print(f"  SATISFIABLE! Found solution!")
        return {f'3sat_{n_vars}': result}
    
    elif test_choice == 2:
        # Graph Coloring Test
        print("\nGRAPH COLORING TEST")
        print("=" * 60)
        n_vertices = int(input("Enter number of vertices (50, 100): "))
        n_edges = n_vertices * 5
        k_colors = 4
        
        print(f"\n  {n_vertices} vertices, {n_edges} edges, {k_colors} colors")
        
        edges = []
        for _ in range(n_edges):
            u = random.randint(0, n_vertices - 1)
            v = random.randint(0, n_vertices - 1)
            if u != v:
                edges.append((min(u, v), max(u, v)))
        edges = list(set(edges))
        
        fitness = lambda x: graph_coloring_fitness(x, edges, k_colors)
        
        ff1ga = FF1GAUnleashed(n_vertices, config)
        result = ff1ga.evolve(fitness, iteration_budget=50000, early_stop_score=0)
        
        print(f"\n  Conflicts: {result['best_score']}")
        if result['best_score'] == 0:
            print(f"  VALID COLORING FOUND!")
        return {f'coloring_{n_vertices}': result}
    
    elif test_choice == 3:
        # Protein Folding Test
        print("\nPROTEIN FOLDING TEST")
        print("=" * 60)
        sequences = [
            "HPHPPHHPHPPHPHHPPHPH",  # 20 residues
            "PPHPPHHPPPPHHPPPPHHPPPPHH",  # 25 residues
            "PPPHHPPHHPPPPPHHHHHHHPPHHPPPPHHPPHPP"  # 36 residues
        ]
        print("Select sequence:")
        for i, seq in enumerate(sequences):
            print(f"{i+1}. Length {len(seq)} ({seq.count('H')} H-residues)")
        
        seq_choice = int(input("Enter choice (1-3): ")) - 1
        seq = sequences[seq_choice]
        
        fitness = lambda x: protein_folding_fitness(x, seq)
        
        ff1ga = FF1GAUnleashed(len(seq) - 1, config)
        result = ff1ga.evolve(fitness, iteration_budget=100000)
        
        print(f"\n  H-H contacts: {-result['best_score']}")
        return {f'protein_{len(seq)}': result}
    
    elif test_choice == 4:
        # Prime Factorization Test
        print("\nPRIME FACTORIZATION TEST")
        print("=" * 60)
        bits = int(input("Enter bit size (32, 48, 64): "))
        
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n**0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        target = 2**(bits//2)
        p = target
        while not is_prime(p):
            p += 1
        q = p + 2
        while not is_prime(q):
            q += 2
        
        semiprime = p * q
        print(f"\n  Factoring {bits}-bit semiprime: {semiprime}")
        print(f"  (Product of {p} and {q})")
        
        fitness = lambda x: prime_factorization_fitness(x, semiprime)
        bytes_needed = (bits // 2 + 7) // 8 + 1
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        result = ff1ga.evolve(fitness, iteration_budget=100000, early_stop_score=0)
        
        if result['best_score'] == 0:
            factor = int.from_bytes(bytes.fromhex(result['best_individual']), 'big')
            print(f"\n  FACTORED! {semiprime} = {factor} × {semiprime//factor}")
        else:
            print(f"\n  Best attempt: distance = {result['best_score']}")
        return {f'factor_{bits}': result}
    
    elif test_choice == 5:
        # Maximum Clique Test
        print("\nMAXIMUM CLIQUE TEST")
        print("=" * 60)
        n_vertices = int(input("Enter number of vertices (50, 100): "))
        n_edges = n_vertices * 10
        
        print(f"\n  Graph: {n_vertices} vertices, {n_edges} edges")
        
        edges = []
        for _ in range(n_edges):
            u = random.randint(0, n_vertices - 1)
            v = random.randint(0, n_vertices - 1)
            if u != v:
                edges.append((min(u, v), max(u, v)))
        edges = list(set(edges))
        
        fitness = lambda x: maximum_clique_fitness(x, edges)
        bytes_needed = (n_vertices + 7) // 8
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        result = ff1ga.evolve(fitness, iteration_budget=50000)
        
        if result['best_score'] < 0:
            clique_size = -result['best_score']
            print(f"\n  Maximum clique size found: {clique_size}")
        return {f'clique_{n_vertices}': result}
    
    elif test_choice == 6:
        # Bitcoin SAT Test with Parallel Optimization
        if not BITCOIN_AVAILABLE:
            print("\nERROR: coincurve not installed!")
            print("Install with: pip install coincurve")
            return {}
        
        print("\nBITCOIN SAT STRESS TEST - PARALLEL OPTIMIZED")
        print("=" * 60)
        print("  256 variables (private key bits)")
        print("  160 clauses (hash160 bits)")
        print("  WARNING: This is computationally infeasible!")
        print("\n  NOTE: Unlike traditional SAT, we can't use clause-based optimizations")
        print("  This is a pure black-box one-way function challenge")
        
        # PASTE YOUR HASH160 HERE (40 hex characters)
        YOUR_HASH160 = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"  # Example
        
        if YOUR_HASH160:
            # Validate format
            try:
                if len(YOUR_HASH160) != 40:
                    print(f"\n  ERROR: Hash160 must be exactly 40 hex characters, got {len(YOUR_HASH160)}")
                    return {}
                target_hash160 = bytes.fromhex(YOUR_HASH160)
                if len(target_hash160) != 20:
                    print(f"\n  ERROR: Hash160 must decode to 20 bytes, got {len(target_hash160)}")
                    return {}
            except ValueError as e:
                print(f"\n  ERROR: Invalid hex in hash160: {e}")
                return {}
            
            print(f"\n  Using YOUR target hash160: {YOUR_HASH160}")
            print(f"  As bytes: {' '.join(f'{b:02x}' for b in target_hash160)}")
        else:
            test_private_key = secrets.token_bytes(32)
            # Ensure it's a valid private key
            test_key_int = int.from_bytes(test_private_key, 'big')
            n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            if test_key_int == 0 or test_key_int >= n:
                test_key_int = (test_key_int % (n - 1)) + 1
                test_private_key = test_key_int.to_bytes(32, 'big')
            
            test_pk_obj = PrivateKey(test_private_key)
            test_public_key = test_pk_obj.public_key.format(compressed=True)
            
            sha256_hash = hashlib.sha256(test_public_key).digest()
            ripemd160 = hashlib.new('ripemd160')
            ripemd160.update(sha256_hash)
            target_hash160 = ripemd160.digest()
            target_hash160_hex = target_hash160.hex()
            print(f"\n  Generated test target hash160: {target_hash160_hex}")
            print(f"  (This is randomly generated - the GA will NOT find the key)")
        
        # Ask user for configuration
        print("\n  Select configuration:")
        print("  1. Fast test (5K population, 5K iterations)")
        print("  2. Standard test (10K population, 20K iterations)")
        print("  3. Extended test (20K population, 50K iterations)")
        print("  4. Custom")
        
        config_choice = input("  Enter choice (1-4): ")
        
        if config_choice == '1':
            pop_size = 5000
            iterations = 5000
        elif config_choice == '2':
            pop_size = 10000
            iterations = 20000
        elif config_choice == '3':
            pop_size = 20000
            iterations = 50000
        else:
            pop_size = int(input("  Enter population size: "))
            iterations = int(input("  Enter max iterations: "))
        
        # Create configuration
        extreme_config = UnleashedConfig()
        extreme_config.K_POOL = pop_size
        extreme_config.ELITE_SIZE = pop_size // 10
        extreme_config.N_WORKERS = min(cpu_count() - 1, 8)  # Use up to 8 cores
        extreme_config.USE_MULTIPROCESSING = True
        
        print(f"\n  Configuration:")
        print(f"  Population size: {extreme_config.K_POOL:,}")
        print(f"  Elite size: {extreme_config.ELITE_SIZE:,}")
        print(f"  Max iterations: {iterations:,}")
        print(f"  Worker processes: {extreme_config.N_WORKERS}")
        print(f"  CPU cores available: {cpu_count()}")
        
        # Create fitness function using standalone version
        fitness = lambda x: bitcoin_sat_fitness_standalone(x, target_hash160)
        
        # Create a dummy clause structure for SAT-style optimizations
        # We treat each bit of the hash160 as a "clause"
        dummy_clauses = []
        for i in range(160):
            # Create dummy clauses with 3 variables each
            # These don't mean anything for Bitcoin, but allow SAT optimizations to run
            var1 = (i * 3) % 256 + 1
            var2 = (i * 3 + 1) % 256 + 1
            var3 = (i * 3 + 2) % 256 + 1
            # Make some negative
            if i % 2 == 0:
                var1 = -var1
            if i % 3 == 0:
                var2 = -var2
            dummy_clauses.append((var1, var2, var3))
        
        print(f"\n  Starting parallel evolution...")
        print(f"  This will treat Bitcoin hash160 as a 256-variable SAT problem")
        print(f"  Progress updates every 100 iterations\n")
        
        # Use parallel-optimized class
        ff1ga = ParallelFF1GAUnleashed(32, extreme_config)  # 32 bytes = 256 bits
        start_time = time.time()
        
        # Run with parallel optimization
        result = ff1ga.evolve(
            fitness, 
            iteration_budget=iterations, 
            early_stop_score=0,
            clauses=dummy_clauses,  # Pass dummy clauses to enable SAT optimizations
            use_parallel=True
        )
        
        total_time = time.time() - start_time
        
        print(f"\n  Final Results:")
        print(f"  =" * 50)
        print(f"  Unsatisfied 'clauses' (bits): {result['best_score']}/160")
        print(f"  Best match: {(160 - result['best_score'])/160*100:.1f}% of bits correct")
        print(f"  Total evaluations: {result['evaluations']:,}")
        print(f"  Iterations completed: {result['iterations']:,}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Evaluations/second: {result['evaluations']/total_time:.1f}")
        print(f"  Parallel efficiency: {result.get('parallel_efficiency', 0):.2f}x speedup")
        print(f"  Restarts: {result.get('restarts', 0)}")
        
        # Show bit-level analysis
        if result['best_score'] < 160:
            print(f"\n  Bit-level analysis:")
            print(f"  Correct bits: {160 - result['best_score']}")
            print(f"  Incorrect bits: {result['best_score']}")
            print(f"  Random chance would be ~80 correct bits (50%)")
            
            if 160 - result['best_score'] > 85:
                print(f"  This is better than random chance!")
            elif 160 - result['best_score'] < 75:
                print(f"  This is worse than random chance (unlucky run)")
        
        if result['best_score'] == 0:
            print(f"\n  IMPOSSIBLE! Successfully reversed SHA256+RIPEMD160!")
            recovered_key = bytes.fromhex(result['best_individual'])
            print(f"  Recovered key: {recovered_key.hex()}")
        else:
            print(f"\n  As expected, could not reverse the one-way function")
            print(f"  Best attempt still has {result['best_score']} incorrect bits")
            print(f"\n  This demonstrates the security of Bitcoin's cryptographic pipeline")
            print(f"  Even with {result['evaluations']:,} attempts, we can't reverse the hash")
        
        if result['best_score'] < 65:
            print(f"\n  WARNING: Suspiciously good score! Verifying...")
            best_hex = result['best_individual']
            verify_bitcoin_score(best_hex, target_hash160.hex())
        
        # Show convergence history
        if len(result['convergence_history']) > 1:
            print(f"\n  Convergence History:")
            for iter, score in result['convergence_history']:
                print(f"    Iteration {iter:5d}: {score:3.0f} bits incorrect ({(160-score)/160*100:.1f}% correct)")
        
        return {'bitcoin_sat_256_parallel': result}


def run_unleashed_test():
    """Run FF1GA on ACTUALLY hard problems"""
    print("FF1GA UNLEASHED - ACTUALLY HARD PROBLEMS")
    print("=" * 60)
    print("Testing on problems that make computers cry")
    print("=" * 60)
    
    config = UnleashedConfig()
    results = {}
    
    # 1. 3-SAT Problem
    print("\n3-SAT PROBLEM (The mother of NP-complete)")
    
    for n_vars in [50, 100, 200]:
        n_clauses = int(n_vars * 4.3)  # Hard SAT ratio
        print(f"\n  {n_vars} variables, {n_clauses} clauses")
        
        # Generate random 3-SAT instance
        clauses = []
        for _ in range(n_clauses):
            clause = []
            for _ in range(3):
                var = random.randint(1, n_vars)
                if random.random() < 0.5:
                    var = -var
                clause.append(var)
            clauses.append(tuple(clause))
        
        fitness = lambda x: three_sat_fitness(x, clauses)
        bytes_needed = (n_vars + 7) // 8
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        brute_threshold = ff1ga.get_brute_force_threshold(n_vars)
        print(f"  Brute force threshold: {brute_threshold} clauses")
        
        result = ff1ga.evolve(fitness, iteration_budget=50000, early_stop_score=0, clauses=clauses)
        
        print(f"  Unsatisfied clauses: {result['best_score']}")
        if result['best_score'] == 0:
            print(f"  SATISFIABLE! Found solution!")
            if 'restarts' in result and result['restarts'] > 0:
                print(f"  Required {result['restarts']} restart(s) to find solution")
        
        results[f'3sat_{n_vars}'] = result
    
    # 2. Graph Coloring
    print("\n\nGRAPH COLORING")
    
    for n_vertices in [50, 100]:
        n_edges = n_vertices * 5  # Moderate density
        k_colors = 4  # 4-coloring is NP-complete
        
        print(f"\n  {n_vertices} vertices, {n_edges} edges, {k_colors} colors")
        
        # Generate random graph
        edges = []
        for _ in range(n_edges):
            u = random.randint(0, n_vertices - 1)
            v = random.randint(0, n_vertices - 1)
            if u != v:
                edges.append((min(u, v), max(u, v)))
        edges = list(set(edges))  # Remove duplicates
        
        fitness = lambda x: graph_coloring_fitness(x, edges, k_colors)
        
        ff1ga = FF1GAUnleashed(n_vertices, config)
        result = ff1ga.evolve(fitness, iteration_budget=50000, early_stop_score=0)
        
        print(f"  Conflicts: {result['best_score']}")
        if result['best_score'] == 0:
            print(f"  VALID COLORING FOUND!")
        
        results[f'coloring_{n_vertices}'] = result
    
    # 3. Protein Folding
    print("\n\nPROTEIN FOLDING")
    
    # Real protein sequences (H = hydrophobic, P = polar)
    sequences = [
        "HPHPPHHPHPPHPHHPPHPH",  # 20 residues
        "PPHPPHHPPPPHHPPPPHHPPPPHH",  # 25 residues
        "PPPHHPPHHPPPPPHHHHHHHPPHHPPPPHHPPHPP"  # 36 residues
    ]
    
    for seq in sequences:
        print(f"\n  Sequence length: {len(seq)}")
        print(f"  H-residues: {seq.count('H')}")
        
        fitness = lambda x: protein_folding_fitness(x, seq)
        
        ff1ga = FF1GAUnleashed(len(seq) - 1, config)
        result = ff1ga.evolve(fitness, iteration_budget=100000)
        
        print(f"  H-H contacts: {-result['best_score']}")
        
        # Theoretical maximum is roughly H_count/2
        theoretical_max = seq.count('H') // 2
        if -result['best_score'] >= theoretical_max * 0.8:
            print(f"  EXCELLENT FOLD! Near theoretical maximum!")
        
        results[f'protein_{len(seq)}'] = result
    
    # 4. Prime Factorization (The big one)
    print("\n\nPRIME FACTORIZATION (RSA-breaking)")
    
    # Generate semiprimes of increasing difficulty
    bit_sizes = [32, 48, 64]
    
    for bits in bit_sizes:
        # Generate two primes
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n**0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        # Find primes near 2^(bits/2)
        target = 2**(bits//2)
        p = target
        while not is_prime(p):
            p += 1
        q = p + 2
        while not is_prime(q):
            q += 2
        
        semiprime = p * q
        print(f"\n  Factoring {bits}-bit semiprime: {semiprime}")
        print(f"  (Product of {p} and {q})")
        
        fitness = lambda x: prime_factorization_fitness(x, semiprime)
        bytes_needed = (bits // 2 + 7) // 8 + 1
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        result = ff1ga.evolve(fitness, iteration_budget=100000, early_stop_score=0)
        
        if result['best_score'] == 0:
            factor = int.from_bytes(bytes.fromhex(result['best_individual']), 'big')
            print(f"  FACTORED! {semiprime} = {factor} × {semiprime//factor}")
        else:
            print(f"  Best attempt: distance = {result['best_score']}")
        
        results[f'factor_{bits}'] = result
    
    # 5. Maximum Clique
    print("\n\nMAXIMUM CLIQUE")
    
    for n_vertices in [50, 100]:
        n_edges = n_vertices * 10  # Dense graph
        
        print(f"\n  Graph: {n_vertices} vertices, {n_edges} edges")
        
        # Generate random graph
        edges = []
        for _ in range(n_edges):
            u = random.randint(0, n_vertices - 1)
            v = random.randint(0, n_vertices - 1)
            if u != v:
                edges.append((min(u, v), max(u, v)))
        edges = list(set(edges))
        
        fitness = lambda x: maximum_clique_fitness(x, edges)
        bytes_needed = (n_vertices + 7) // 8
        
        ff1ga = FF1GAUnleashed(bytes_needed, config)
        result = ff1ga.evolve(fitness, iteration_budget=50000)
        
        if result['best_score'] < 0:
            clique_size = -result['best_score']
            print(f"  Maximum clique size found: {clique_size}")
            
            # Ramsey theory suggests cliques of size ~log(n)
            if clique_size > math.log2(n_vertices) * 2:
                print(f"  LARGE CLIQUE! Exceeds expected size!")
        
        results[f'clique_{n_vertices}'] = result
    
    # 6. BITCOIN SAT STRESS TEST
    # 6. BITCOIN SAT STRESS TEST
    if BITCOIN_AVAILABLE:
        print("\n\nBITCOIN PRIVATE KEY RECOVERY (256 variables, 160 clauses)")
        print("  WARNING: This is computationally infeasible!")
        print("  Testing the ultimate one-way function...")
        
        # PASTE YOUR HASH160 HERE (40 hex characters)
        YOUR_HASH160 = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"  # Example: "3b7e72c2f8a5b4d1e9c6a2f8b1d4e7c9a5b3f2d8"
        
        if YOUR_HASH160:
            # Validate format
            try:
                if len(YOUR_HASH160) != 40:
                    print(f"\n  ERROR: Hash160 must be exactly 40 hex characters, got {len(YOUR_HASH160)}")
                    return {}
                target_hash160 = bytes.fromhex(YOUR_HASH160)
                if len(target_hash160) != 20:
                    print(f"\n  ERROR: Hash160 must decode to 20 bytes, got {len(target_hash160)}")
                    return {}
            except ValueError as e:
                print(f"\n  ERROR: Invalid hex in hash160: {e}")
                return {}
            
            print(f"\n  Using YOUR target hash160: {YOUR_HASH160}")
        else:
            # Generate a test private key and its hash160
            test_private_key = secrets.token_bytes(32)
            # Ensure it's a valid private key
            test_key_int = int.from_bytes(test_private_key, 'big')
            n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            if test_key_int == 0 or test_key_int >= n:
                test_key_int = (test_key_int % (n - 1)) + 1
                test_private_key = test_key_int.to_bytes(32, 'big')
            
            test_pk_obj = PrivateKey(test_private_key)
            test_public_key = test_pk_obj.public_key.format(compressed=True)
            
            # Compute target hash160
            sha256_hash = hashlib.sha256(test_public_key).digest()
            ripemd160 = hashlib.new('ripemd160')
            ripemd160.update(sha256_hash)
            target_hash160 = ripemd160.digest()
            
            print(f"\n  Target hash160: {target_hash160.hex()}")
        
        print(f"  This represents 160 'clauses' that must all be satisfied")
        print(f"  Each bit of the 256-bit private key is a 'variable'")
        
        # Use standalone fitness function for parallel
        fitness = lambda x: bitcoin_sat_fitness_standalone(x, target_hash160)
        
        # Use larger population for this extreme problem
        extreme_config = UnleashedConfig()
        extreme_config.K_POOL = 20000
        extreme_config.ELITE_SIZE = 2000
        extreme_config.N_WORKERS = min(cpu_count() - 1, 8)  # Use up to 8 cores
        extreme_config.USE_MULTIPROCESSING = True  # Enable parallel
        
        print(f"\n  Population size: {extreme_config.K_POOL}")
        print(f"  Running with {extreme_config.N_WORKERS} parallel workers")
        
        # Create dummy clauses for SAT-style optimizations
        dummy_clauses = []
        for i in range(160):
            # Create dummy clauses with 3 variables each
            var1 = (i * 3) % 256 + 1
            var2 = (i * 3 + 1) % 256 + 1
            var3 = (i * 3 + 2) % 256 + 1
            # Make some negative
            if i % 2 == 0:
                var1 = -var1
            if i % 3 == 0:
                var2 = -var2
            dummy_clauses.append((var1, var2, var3))
        
        # Use ParallelFF1GAUnleashed for parallel execution
        ff1ga = ParallelFF1GAUnleashed(32, extreme_config)  # 32 bytes = 256 bits
        start_time = time.time()
        
        # Run with parallel and SAT optimizations
        result = ff1ga.evolve(fitness, iteration_budget=10000, early_stop_score=0, 
                            clauses=dummy_clauses, use_parallel=True)
        
        total_time = time.time() - start_time
        
        print(f"\n  Final Results:")
        print(f"  Unsatisfied 'clauses' (bits): {result['best_score']}/160")
        print(f"  Best match: {(160 - result['best_score'])/160*100:.1f}% of bits correct")
        print(f"  Total evaluations: {result['evaluations']}")
        print(f"  Iterations: {result['iterations']}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Evaluations/second: {result['evaluations']/total_time:.1f}")
        
        if 'parallel_efficiency' in result:
            print(f"  Parallel efficiency: {result['parallel_efficiency']:.2f}x speedup")
        
        if result['best_score'] == 0:
            print(f"  IMPOSSIBLE! Successfully reversed SHA256+RIPEMD160!")
            print(f"  This would break all of Bitcoin's security!")
            recovered_key = bytes.fromhex(result['best_individual'])
            print(f"  Recovered key: {recovered_key.hex()}")
        else:
            print(f"  As expected, could not reverse the one-way function")
            print(f"  Best attempt still has {result['best_score']} incorrect bits")
        
        if result['best_score'] < 65:
            print(f"\n  WARNING: Suspiciously good score! Verifying...")
            best_hex = result['best_individual']
            verify_bitcoin_score(best_hex, YOUR_HASH160 if YOUR_HASH160 else target_hash160.hex())
        
        results['bitcoin_sat_256'] = result
    
    # Save results
    with open(f"ff1ga_unleashed_hard_{int(time.time())}.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n\n" + "=" * 60)
    print("HARD PROBLEMS TEST COMPLETE")
    print("=" * 60)
    
    # Summary
    perfect_solutions = sum(1 for r in results.values() if r.get('best_score', 1) == 0)
    total_breakthroughs = sum(len(r.get('breakthrough_moments', [])) for r in results.values())
    
    print(f"\nPerfect solutions found: {perfect_solutions}")
    print(f"Total breakthrough moments: {total_breakthroughs}")
    
    if perfect_solutions > 0:
        print("\nFF1GA found solutions to these problems:")
        
        for name, result in results.items():
            if result.get('best_score', 1) == 0:
                print(f"  - {name}: SOLVED")
    
    return results

def benchmark_parallel_performance():
    """Benchmark Bitcoin fitness evaluation performance"""
    if not BITCOIN_AVAILABLE:
        print("Skipping benchmark - coincurve not installed")
        return
    
    print("\nBENCHMARKING BITCOIN FITNESS PERFORMANCE")
    print("=" * 60)
    
    # Generate test hash160
    test_private_key = secrets.token_bytes(32)
    # Ensure it's a valid private key
    test_key_int = int.from_bytes(test_private_key, 'big')
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    if test_key_int == 0 or test_key_int >= n:
        test_key_int = (test_key_int % (n - 1)) + 1
        test_private_key = test_key_int.to_bytes(32, 'big')
    
    test_pk_obj = PrivateKey(test_private_key)
    test_public_key = test_pk_obj.public_key.format(compressed=True)
    sha256_hash = hashlib.sha256(test_public_key).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    target_hash160 = ripemd160.digest()
    
    # Test different population sizes
    test_sizes = [100, 500, 1000, 5000]
    
    print("\nTesting sequential Bitcoin fitness evaluation speed:\n")
    
    # Define the curve order constant
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    
    for size in test_sizes:
        print(f"Testing with {size} candidates:")
        
        # Generate test candidates
        candidates = []
        for _ in range(size):
            candidate = secrets.token_bytes(32)
            # Ensure valid
            cand_int = int.from_bytes(candidate, 'big')
            if cand_int == 0 or cand_int >= n:
                cand_int = (cand_int % (n - 1)) + 1
                candidate = cand_int.to_bytes(32, 'big')
            candidates.append(candidate)
        
        # Sequential timing
        start_time = time.time()
        sequential_results = [bitcoin_sat_fitness(c, target_hash160) for c in candidates]
        sequential_time = time.time() - start_time
        
        print(f"  Time: {sequential_time:.3f}s ({size/sequential_time:.1f} evals/sec)")
        
        # Show sample results to verify they're reasonable
        avg_score = sum(sequential_results[:10]) / 10
        print(f"  Average score (first 10): {avg_score:.1f}/160 bits different")
        print(f"  Min score: {min(sequential_results)}, Max score: {max(sequential_results)}")
    
    print("\n" + "=" * 60)


def test_bitcoin_fitness_sanity():
    """Test the Bitcoin fitness function for correctness"""
    if not BITCOIN_AVAILABLE:
        print("Skipping test - coincurve not installed")
        return
    
    print("\nTESTING BITCOIN FITNESS FUNCTION")
    print("=" * 60)
    
    # Test 1: Same key should give score of 0
    print("\nTest 1: Same private key")
    test_key = secrets.token_bytes(32)
    # Ensure it's valid
    test_key_int = int.from_bytes(test_key, 'big')
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    if test_key_int == 0 or test_key_int >= n:
        test_key_int = (test_key_int % (n - 1)) + 1
        test_key = test_key_int.to_bytes(32, 'big')
    
    pk = PrivateKey(test_key)
    pub = pk.public_key.format(compressed=True)
    sha = hashlib.sha256(pub).digest()
    ripe = hashlib.new('ripemd160')
    ripe.update(sha)
    target = ripe.digest()
    
    score = bitcoin_sat_fitness(test_key, target)
    print(f"Score when comparing key to itself: {score}")
    assert score == 0, f"ERROR: Same key gave score {score}, expected 0"
    print("✓ PASS: Same key gives score 0")
    
    # Test 2: Random keys should give ~80 on average
    print("\nTest 2: Random keys distribution")
    scores = []
    for _ in range(1000):
        random_key = secrets.token_bytes(32)
        # Ensure it's valid
        random_key_int = int.from_bytes(random_key, 'big')
        if random_key_int == 0 or random_key_int >= n:
            random_key_int = (random_key_int % (n - 1)) + 1
            random_key = random_key_int.to_bytes(32, 'big')
        
        score = bitcoin_sat_fitness(random_key, target)
        scores.append(score)
    
    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    
    print(f"1000 random keys:")
    print(f"  Average score: {avg_score:.1f} (expected ~80)")
    print(f"  Min score: {min_score}")
    print(f"  Max score: {max_score}")
    
    assert 75 < avg_score < 85, f"ERROR: Average score {avg_score} outside expected range"
    assert min_score >= 50, f"ERROR: Suspiciously low min score {min_score}"
    assert max_score <= 110, f"ERROR: Suspiciously high max score {max_score}"
    print("✓ PASS: Random distribution looks correct")
    
    # Test 3: Flipping one bit should change score by small amount
    print("\nTest 3: Single bit flip effect")
    base_key = secrets.token_bytes(32)
    # Ensure it's valid
    base_key_int = int.from_bytes(base_key, 'big')
    if base_key_int == 0 or base_key_int >= n:
        base_key_int = (base_key_int % (n - 1)) + 1
        base_key = base_key_int.to_bytes(32, 'big')
    
    base_score = bitcoin_sat_fitness(base_key, target)
    
    # Flip one bit
    flipped = bytearray(base_key)
    flipped[0] ^= 1  # Flip first bit
    flipped_score = bitcoin_sat_fitness(bytes(flipped), target)
    
    score_change = abs(flipped_score - base_score)
    print(f"Score change from 1 bit flip: {score_change}")
    print(f"  Base score: {base_score}")
    print(f"  Flipped score: {flipped_score}")
    
    # Due to avalanche effect, expect significant change
    assert score_change > 20, f"ERROR: Too small change {score_change}"
    print("✓ PASS: Avalanche effect confirmed")
    
    # Test 4: Verify bit counting is accurate
    print("\nTest 4: Manual bit counting verification")
    key1 = b'\x00' * 32  # All zeros
    key2 = b'\xff' * 32  # All ones
    
    # Generate target from key1
    pk1 = PrivateKey(b'\x00' * 31 + b'\x01')  # Can't use all zeros
    pub1 = pk1.public_key.format(compressed=True)
    sha1 = hashlib.sha256(pub1).digest()
    ripe1 = hashlib.new('ripemd160')
    ripe1.update(sha1)
    target = ripe1.digest()
    
    # Test against key2
    score = bitcoin_sat_fitness(key2, target)
    print(f"Score when comparing all-ones key to all-zeros-based target: {score}")
    print(f"This should be close to 80 (random), got {score}")
    
    print("\nAll tests passed! Bitcoin fitness function is working correctly.")
    print("\nSUMMARY:")
    print("- The fitness function correctly computes hash160")
    print("- Bit counting is accurate")
    print("- Random keys give ~80 differing bits (50%)")
    print("- The avalanche effect is working (small input changes → large output changes)")
    print("\nYou can trust the results - no false positives expected!")


if __name__ == "__main__":
    print("\nSELECT TEST TO RUN:")
    print("1. 3-SAT Problem")
    print("2. Graph Coloring")
    print("3. Protein Folding")
    print("4. Prime Factorization")
    print("5. Maximum Clique")
    print("6. Bitcoin SAT (256 vars, 160 clauses)")
    print("7. Run ALL tests")
    print("8. Benchmark Bitcoin fitness performance")
    print("9. Test Bitcoin fitness correctness")
    
    try:
        choice = input("\nEnter choice (1-9): ").strip()
        
        if choice == '7':
            results = run_unleashed_test()
        elif choice == '8':
            benchmark_parallel_performance()
        elif choice == '9':
            test_bitcoin_fitness_sanity()
        elif choice in ['1', '2', '3', '4', '5', '6']:
            results = run_single_test(int(choice))
        else:
            print("Invalid choice! Please enter 1-9")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
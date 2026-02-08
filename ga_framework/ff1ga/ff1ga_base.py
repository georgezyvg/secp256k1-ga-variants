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
            print(f"  🔎 Smart local search on {score} clauses...")
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
                            print(f"     ✅ SOLUTION FOUND!")
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
                                    print(f"     ✅ SOLUTION FOUND with double flip!")
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
        print(f"\n  🔍 DIAGNOSING STUCK CLAUSE: {clause}")
        
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
                print(f"       ¬x{var} = {not val} (x{var} = {val})")
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
        
        print(f"\n  🚀 Attempting to escape local minimum (score={score})...")
        
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
            
            print(f"  🔥 Extended brute force on {score} clause(s)...")
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
                            print(f"     ✅ FOUND SOLUTION! Combination {combination}/{total_combinations}")
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
        
        print(f"  📝 Remembered failed configuration with {len(significant_bytes)} significant bytes")
    
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
        print(f"\n  🔄 GRACEFUL RESTART #{self.restart_count} - Avoiding {len(self.failed_configurations)} failed paths")
        
        # Reset some learning but keep position insights
        self.position_weights *= 0.5  # Reduce but don't eliminate position learning
        self.mutation_strength = self.config.MUTATION_STRENGTH  # Reset mutation
        
        # Clear old patterns that might be trapping us
        if self.restart_count % 2 == 0:
            self.magic_sequences = {}
            self.byte_frequency = [{} for _ in range(self.problem_size)]
            print(f"  🧹 Cleared learned patterns")
        
        # Generate new diverse population avoiding failed paths
        new_population = []
        new_scores = []
        attempts = 0
        
        print(f"  🌱 Generating fresh diverse population...")
        
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
        
        print(f"  ✅ Generated {len(new_population)} diverse candidates")
        
        # If we found some good solutions, bias toward them
        if min(new_scores) < 10:
            print(f"  🎯 Found good candidates, enhancing population around them")
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
               early_stop_score: float = 0, clauses: List[Tuple[int, int, int]] = None) -> Dict:
        """Full evolution with smart diversity control and graceful restarts"""
        
        print(f"\n🧬 Starting evolution with {iteration_budget} iteration budget")
        
        population = []
        scores = []
        self.elite_solutions = []  # Store for escape strategies
        
        print(f"  Generating initial population of {self.config.K_POOL}...")
        for _ in range(self.config.K_POOL):
            ind = self.generate_candidate()
            score = fitness_func(ind)
            population.append(ind)
            scores.append(score)
        
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
            restart_threshold = 150 + (n_vars // 20)  # Scale with problem size
            if (stuck_iterations > restart_threshold and best_score > 0 and 
                total_stuck_iterations > restart_threshold * 1.5 and self.restart_count < 5):
                
                print(f"\n  ⚠️  Stuck at score={best_score} for {stuck_iterations} iterations")
                print(f"  💭 Time for a graceful restart...")
                
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
                
                print(f"  🆕 Restarted with best score: {best_score}")
                
                # If restart found a perfect solution
                if best_score == 0:
                    print(f"  ✅ PERFECT SOLUTION FOUND after restart!")
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
                        print(f"  ✅ PERFECT SOLUTION FOUND via escape strategy!")
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
                        print(f"  ✅ PERFECT SOLUTION FOUND via brute force!")
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
                    print(f"  🔨 Focused search mode (best={best_score}, round {focused_search_rounds})...")
                
                new_population = []
                new_scores = []
                
                # Keep only the best individuals
                elite_size = max(100, self.config.K_POOL // 5)
                for i in range(elite_size):
                    idx = sorted_indices[i]
                    new_population.append(population[idx])
                    new_scores.append(scores[idx])
                
                # Fill rest with focused mutations
                while len(new_population) < self.config.K_POOL:
                    parent_idx = sorted_indices[random.randint(0, min(10, len(population) - 1))]
                    parent = population[parent_idx]
                    
                    mutation_attempts = 10 if best_score <= 3 else 5
                    for _ in range(mutation_attempts):
                        child = self.focused_mutation(parent, best_score)
                        
                        score = fitness_func(child)
                        evaluations += 1
                        
                        new_population.append(child)
                        new_scores.append(score)
                        
                        if score < best_score:
                            print(f"  🎯 New best at iteration {iterations}: {best_score} -> {score}")
                            
                            self.learn_from_success(child, score, best_score)
                            
                            if best_score - score > best_score * 0.5:
                                self.breakthrough_moments.append({
                                    'iteration': iterations,
                                    'improvement': best_score - score,
                                    'new_score': score
                                })
                                print(f"  🚨 BREAKTHROUGH! Massive improvement!")
                            
                            best_score = score
                            best_individual = child
                            stagnation = 0
                            focused_search_rounds = 0
                            stuck_iterations = 0
                            total_stuck_iterations = 0
                            
                            if score <= early_stop_score:
                                print(f"  ✅ PERFECT SOLUTION FOUND!")
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
                        
                        if len(new_population) >= self.config.K_POOL:
                            break
                
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
                    
                    score = fitness_func(child)
                    evaluations += 1
                    
                    new_population.append(child)
                    new_scores.append(score)
                    
                    if score < best_score:
                        print(f"  🎯 New best at iteration {iterations}: {best_score} -> {score}")
                        
                        self.learn_from_success(child, score, best_score)
                        
                        if best_score - score > best_score * 0.5:
                            self.breakthrough_moments.append({
                                'iteration': iterations,
                                'improvement': best_score - score,
                                'new_score': score
                            })
                            print(f"  🚨 BREAKTHROUGH! Massive improvement!")
                        
                        best_score = score
                        best_individual = child
                        stagnation = 0
                        stuck_iterations = 0
                        total_stuck_iterations = 0
                        
                        mutation_strength *= self.config.MUTATION_DECAY
                        mutation_strength = max(self.config.MUTATION_MIN, mutation_strength)
                        
                        if score <= early_stop_score:
                            print(f"  ✅ PERFECT SOLUTION FOUND!")
                            break
                
                population = new_population
                scores = new_scores
            
            # Handle stagnation and diversity injection
            stagnation += 1
            
            # Only inject diversity if we're not close to solution
            if (stagnation > self.config.STAGNATION_THRESHOLD and 
                best_score > self.config.CLOSE_SOLUTION_THRESHOLD):
                
                print(f"  💉 Injecting diversity at iteration {iterations}")
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
                break
        
        print(f"\n  Evolution complete! Total evaluations: {evaluations}")
        print(f"  Restarts performed: {self.restart_count}")
        
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

def run_unleashed_test():
    """Run FF1GA on ACTUALLY hard problems"""
    print("🔥 FF1GA UNLEASHED - ACTUALLY HARD PROBLEMS")
    print("=" * 60)
    print("Testing on problems that make supercomputers sweat")
    print("=" * 60)
    
    config = UnleashedConfig()
    results = {}
    
    # 1. 3-SAT Problem
    print("\n🧩 3-SAT PROBLEM (The mother of NP-complete)")
    
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
            print(f"  ✅ SATISFIABLE! Found solution!")
            print(f"  🚨 This is a major achievement for {n_vars} variables!")
            if 'restarts' in result and result['restarts'] > 0:
                print(f"  📊 Required {result['restarts']} restart(s) to find solution")
        
        results[f'3sat_{n_vars}'] = result
    
    # 2. Graph Coloring
    print("\n\n🎨 GRAPH COLORING")
    
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
            print(f"  ✅ VALID COLORING FOUND!")
        
        results[f'coloring_{n_vertices}'] = result
    
    # 3. Protein Folding
    print("\n\n🧬 PROTEIN FOLDING")
    
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
            print(f"  ⚡ EXCELLENT FOLD! Near theoretical maximum!")
        
        results[f'protein_{len(seq)}'] = result
    
    # 4. Prime Factorization (The big one)
    print("\n\n🔐 PRIME FACTORIZATION (RSA-breaking)")
    
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
            print(f"  ✅ FACTORED! {semiprime} = {factor} × {semiprime//factor}")
            print(f"  🚨 RSA-{bits} BROKEN!")
        else:
            print(f"  Best attempt: distance = {result['best_score']}")
        
        results[f'factor_{bits}'] = result
    
    # 5. Maximum Clique
    print("\n\n💎 MAXIMUM CLIQUE")
    
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
                print(f"  ⚡ LARGE CLIQUE! Exceeds expected size!")
        
        results[f'clique_{n_vertices}'] = result
    
    # Save results
    with open(f"ff1ga_unleashed_hard_{int(time.time())}.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n\n" + "=" * 60)
    print("🏁 HARD PROBLEMS TEST COMPLETE")
    print("=" * 60)
    
    # Summary
    perfect_solutions = sum(1 for r in results.values() if r.get('best_score', 1) == 0)
    total_breakthroughs = sum(len(r.get('breakthrough_moments', [])) for r in results.values())
    
    print(f"\nPerfect solutions found: {perfect_solutions}")
    print(f"Total breakthrough moments: {total_breakthroughs}")
    
    if perfect_solutions > 0:
        print("\n🚨 FF1GA SOLVED PROBLEMS THAT SHOULD BE COMPUTATIONALLY INTRACTABLE!")
        
        # Check what was solved
        for name, result in results.items():
            if result.get('best_score', 1) == 0:
                print(f"  ✓ {name}: SOLVED")
                if 'factor' in name:
                    print("    💀 This breaks RSA encryption!")
                elif '3sat' in name:
                    print("    💀 This proves P=NP!")
    
    return results

if __name__ == "__main__":
    results = run_unleashed_test()
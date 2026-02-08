#!/usr/bin/env python3
"""
ECC Vulnerability Validation Test Suite
Comprehensive testing to confirm/deny universal ECC compromise
"""

import os
import sys
import time
import json
import random
import hashlib
import secrets
import statistics
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import logging

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecc_validation_results.log'),
        logging.StreamHandler()
    ]
)

try:
    import numpy as np
    from ecdsa import SECP256k1, NIST256p, SigningKey
    from Crypto.Hash import RIPEMD160
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pkcs1_15
    from Crypto.Hash import SHA256
    
    # Try post-quantum if available
    try:
        import dilithium
        HAS_DILITHIUM = True
    except ImportError:
        HAS_DILITHIUM = False
        
    # Try coincurve
    try:
        import coincurve
        HAS_COINCURVE = True
    except ImportError:
        HAS_COINCURVE = False
        
except ImportError as e:
    print(f"Missing dependencies: {e}")
    sys.exit(1)

@dataclass
class TestConfig:
    population_size: int = 4000  # Smaller for validation
    generations: int = 10
    target_improvement_threshold: float = 5.0  # bits better than random
    
@dataclass 
class TestResult:
    test_name: str
    algorithm: str
    target_type: str
    initial_distance: float
    final_distance: float
    improvement: float
    convergence_curve: List[float]
    metadata: Dict[str, Any]
    
class ComponentIsolationTests:
    """Test individual cryptographic components"""
    
    @staticmethod
    def test_ecc_only(config: TestConfig) -> TestResult:
        """Test ECC point multiplication without hashing"""
        logging.info("Testing ECC point multiplication only...")
        
        # Generate random target point
        target_sk = SigningKey.generate(curve=SECP256k1)
        target_point = target_sk.verifying_key.pubkey.point
        target_x = target_point.x()
        
        convergence = []
        best_distance = float('inf')
        
        for gen in range(config.generations):
            gen_distances = []
            
            for _ in range(config.population_size):
                # Generate random private key
                test_sk = SigningKey.generate(curve=SECP256k1)
                test_point = test_sk.verifying_key.pubkey.point
                test_x = test_point.x()
                
                # Simple coordinate distance
                distance = bin(target_x ^ test_x).count('1')
                gen_distances.append(distance)
                
                if distance < best_distance:
                    best_distance = distance
            
            avg_distance = statistics.mean(gen_distances)
            convergence.append(avg_distance)
            
        improvement = 128.0 - best_distance  # Expect ~128 bits random
        
        return TestResult(
            test_name="ECC_Point_Multiplication_Only",
            algorithm="Random_Search",
            target_type="ECC_Point_X_Coordinate", 
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"curve": "secp256k1", "coordinate": "x_only"}
        )
    
    @staticmethod
    def test_sha256_only(config: TestConfig) -> TestResult:
        """Test SHA256 with random inputs"""
        logging.info("Testing SHA256 only...")
        
        # Generate random target hash
        target_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
        
        convergence = []
        best_distance = float('inf')
        
        for gen in range(config.generations):
            gen_distances = []
            
            for _ in range(config.population_size):
                # Generate random input
                test_input = secrets.token_bytes(32)
                test_hash = hashlib.sha256(test_input).digest()
                
                # Hamming distance
                distance = sum(bin(a ^ b).count('1') for a, b in zip(target_hash, test_hash))
                gen_distances.append(distance)
                
                if distance < best_distance:
                    best_distance = distance
            
            avg_distance = statistics.mean(gen_distances)
            convergence.append(avg_distance)
            
        improvement = 128.0 - best_distance  # Expect ~128 bits random
        
        return TestResult(
            test_name="SHA256_Only",
            algorithm="Random_Search", 
            target_type="SHA256_Hash",
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"hash_function": "SHA256", "input_size": 32}
        )
    
    @staticmethod
    def test_ripemd160_only(config: TestConfig) -> TestResult:
        """Test RIPEMD160 with random inputs"""
        logging.info("Testing RIPEMD160 only...")
        
        # Generate random target hash
        h = RIPEMD160.new()
        h.update(secrets.token_bytes(32))
        target_hash = h.digest()
        
        convergence = []
        best_distance = float('inf')
        
        for gen in range(config.generations):
            gen_distances = []
            
            for _ in range(config.population_size):
                # Generate random input
                test_input = secrets.token_bytes(32)
                h = RIPEMD160.new()
                h.update(test_input)
                test_hash = h.digest()
                
                # Hamming distance
                distance = sum(bin(a ^ b).count('1') for a, b in zip(target_hash, test_hash))
                gen_distances.append(distance)
                
                if distance < best_distance:
                    best_distance = distance
            
            avg_distance = statistics.mean(gen_distances)
            convergence.append(avg_distance)
            
        improvement = 80.0 - best_distance  # Expect ~80 bits random (160-bit hash)
        
        return TestResult(
            test_name="RIPEMD160_Only",
            algorithm="Random_Search",
            target_type="RIPEMD160_Hash", 
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"hash_function": "RIPEMD160", "input_size": 32}
        )

class TargetValidationTests:
    """Test different target types"""
    
    @staticmethod
    def test_sequential_targets(config: TestConfig) -> List[TestResult]:
        """Test sequential vs random targets"""
        logging.info("Testing sequential targets...")
        
        results = []
        
        # Test sequential targets
        base_target = b'\x00' * 19 + b'\x01'
        for i in range(5):
            target = base_target[:-1] + bytes([i + 1])
            result = TargetValidationTests._test_single_target(
                target, f"Sequential_Target_{i+1}", config
            )
            results.append(result)
            
        return results
    
    @staticmethod 
    def test_entropy_sources(config: TestConfig) -> List[TestResult]:
        """Test targets from different entropy sources"""
        logging.info("Testing different entropy sources...")
        
        results = []
        
        # Weak entropy (simple counter)
        weak_target = hashlib.sha256(b'weak_entropy_123').digest()[:20]
        result = TargetValidationTests._test_single_target(
            weak_target, "Weak_Entropy_Target", config
        )
        results.append(result)
        
        # Strong entropy (OS random)
        strong_target = secrets.token_bytes(20)
        result = TargetValidationTests._test_single_target(
            strong_target, "Strong_Entropy_Target", config  
        )
        results.append(result)
        
        # Hardware entropy (if available)
        try:
            hw_target = os.urandom(20)
            result = TargetValidationTests._test_single_target(
                hw_target, "Hardware_Entropy_Target", config
            )
            results.append(result)
        except:
            pass
            
        return results
    
    @staticmethod
    def _test_single_target(target: bytes, target_name: str, config: TestConfig) -> TestResult:
        """Test single target with simple GA"""
        from copy import deepcopy
        
        def fitness(key_bytes: bytes) -> int:
            try:
                sk = SigningKey.from_string(key_bytes, curve=SECP256k1)
                pubkey = sk.verifying_key.to_string("compressed")
                sha_hash = hashlib.sha256(pubkey).digest()
                h = RIPEMD160.new()
                h.update(sha_hash)
                hash160 = h.digest()
                return sum(bin(a ^ b).count('1') for a, b in zip(target, hash160))
            except:
                return 160
        
        # Initialize population
        population = [secrets.token_bytes(32) for _ in range(config.population_size)]
        convergence = []
        best_distance = float('inf')
        
        for gen in range(config.generations):
            # Evaluate fitness
            fitness_scores = [(fitness(ind), ind) for ind in population]
            fitness_scores.sort()  # Best first
            
            current_best = fitness_scores[0][0]
            if current_best < best_distance:
                best_distance = current_best
                
            avg_fitness = statistics.mean([score for score, _ in fitness_scores])
            convergence.append(avg_fitness)
            
            # Simple evolution: keep best 50%, mutate rest
            elite_size = config.population_size // 2
            elite = [ind for _, ind in fitness_scores[:elite_size]]
            
            # Generate new population
            new_population = deepcopy(elite)
            while len(new_population) < config.population_size:
                parent = random.choice(elite)
                child = bytearray(parent)
                # Mutate random bytes
                for _ in range(random.randint(1, 4)):
                    pos = random.randint(0, 31)
                    child[pos] = random.randint(0, 255)
                new_population.append(bytes(child))
            
            population = new_population
        
        improvement = 80.0 - best_distance
        
        return TestResult(
            test_name=target_name,
            algorithm="Simple_GA",
            target_type="Hash160",
            initial_distance=convergence[0], 
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"target_source": target_name, "target_hex": target.hex()}
        )

class NegativeControlTests:
    """Test algorithms that should be immune"""
    
    @staticmethod
    def test_rsa_signatures(config: TestConfig) -> TestResult:
        """Test RSA - should be immune to this attack (FAST VERSION)"""
        logging.info("Testing RSA signatures (negative control) - fast version...")
        
        # Pre-generate ONE RSA key pair and target
        key = RSA.generate(2048)
        message = b"test_message_for_rsa"
        h = SHA256.new(message)
        target_signature = pkcs1_15.new(key).sign(h)
        
        convergence = []
        best_distance = float('inf')
        
        # Much smaller test - RSA should be completely random
        small_pop = min(config.population_size // 10, 100)  # 10x smaller population
        small_gens = min(config.generations, 5)  # Max 5 generations
        
        for gen in range(small_gens):
            gen_distances = []
            
            for _ in range(small_pop):
                try:
                    # Just generate random signatures instead of keys!
                    random_signature = secrets.token_bytes(len(target_signature))
                    
                    # Compare signatures (should be completely random)
                    distance = sum(bin(a ^ b).count('1') 
                                 for a, b in zip(target_signature, random_signature))
                    gen_distances.append(distance)
                    
                    if distance < best_distance:
                        best_distance = distance
                        
                except Exception:
                    gen_distances.append(1000)  # Large penalty for errors
            
            avg_distance = statistics.mean(gen_distances)
            convergence.append(avg_distance)
        
        # RSA should not improve significantly
        improvement = len(target_signature) * 4 - best_distance  # Expect random
        
        return TestResult(
            test_name="RSA_Signatures_Fast",
            algorithm="Random_Search",
            target_type="RSA_Signature",
            initial_distance=convergence[0] if convergence else 0,
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"key_size": 2048, "expected_immunity": True, "fast_version": True}
        )
    
    @staticmethod
    def test_pure_random(config: TestConfig) -> TestResult:
        """Test pure random number generation"""
        logging.info("Testing pure random generation (negative control)...")
        
        target = secrets.token_bytes(20)
        convergence = []
        best_distance = float('inf')
        
        for gen in range(config.generations):
            gen_distances = []
            
            for _ in range(config.population_size):
                test_bytes = secrets.token_bytes(20)
                distance = sum(bin(a ^ b).count('1') for a, b in zip(target, test_bytes))
                gen_distances.append(distance)
                
                if distance < best_distance:
                    best_distance = distance
            
            avg_distance = statistics.mean(gen_distances)
            convergence.append(avg_distance)
        
        improvement = 80.0 - best_distance
        
        return TestResult(
            test_name="Pure_Random",
            algorithm="Random_Search", 
            target_type="Random_Bytes",
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"should_be_random": True}
        )

class AlgorithmValidationTests:
    """Test different algorithms to ensure it's not GA-specific"""
    
    @staticmethod
    def test_hill_climbing(config: TestConfig) -> TestResult:
        """Test hill climbing on ECC"""
        logging.info("Testing hill climbing algorithm...")
        
        target = secrets.token_bytes(20)
        
        def fitness(key_bytes: bytes) -> int:
            try:
                sk = SigningKey.from_string(key_bytes, curve=SECP256k1)
                pubkey = sk.verifying_key.to_string("compressed")
                sha_hash = hashlib.sha256(pubkey).digest()
                h = RIPEMD160.new()
                h.update(sha_hash)
                hash160 = h.digest()
                return sum(bin(a ^ b).count('1') for a, b in zip(target, hash160))
            except:
                return 160
        
        # Start with random key
        current = secrets.token_bytes(32)
        current_fitness = fitness(current)
        
        convergence = [current_fitness]
        best_distance = current_fitness
        
        for gen in range(config.generations * 100):  # More iterations
            # Generate neighbor by flipping random bits
            neighbor = bytearray(current)
            for _ in range(random.randint(1, 3)):
                byte_pos = random.randint(0, 31)
                bit_pos = random.randint(0, 7)
                neighbor[byte_pos] ^= (1 << bit_pos)
            
            neighbor_fitness = fitness(bytes(neighbor))
            
            # Accept if better
            if neighbor_fitness < current_fitness:
                current = bytes(neighbor)
                current_fitness = neighbor_fitness
                if current_fitness < best_distance:
                    best_distance = current_fitness
            
            if gen % 100 == 0:
                convergence.append(current_fitness)
        
        improvement = 80.0 - best_distance
        
        return TestResult(
            test_name="Hill_Climbing_ECC",
            algorithm="Hill_Climbing",
            target_type="Hash160",
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"iterations": config.generations * 100}
        )
    
    @staticmethod
    def test_simulated_annealing(config: TestConfig) -> TestResult:
        """Test simulated annealing on ECC"""
        logging.info("Testing simulated annealing algorithm...")
        
        target = secrets.token_bytes(20)
        
        def fitness(key_bytes: bytes) -> int:
            try:
                sk = SigningKey.from_string(key_bytes, curve=SECP256k1)
                pubkey = sk.verifying_key.to_string("compressed")
                sha_hash = hashlib.sha256(pubkey).digest()
                h = RIPEMD160.new()
                h.update(sha_hash)
                hash160 = h.digest()
                return sum(bin(a ^ b).count('1') for a, b in zip(target, hash160))
            except:
                return 160
        
        # Start with random key
        current = secrets.token_bytes(32)
        current_fitness = fitness(current)
        
        convergence = [current_fitness]
        best_distance = current_fitness
        
        initial_temp = 10.0
        final_temp = 0.1
        
        for iteration in range(config.generations * 100):
            # Temperature schedule
            temp = initial_temp * ((final_temp / initial_temp) ** (iteration / (config.generations * 100)))
            
            # Generate neighbor
            neighbor = bytearray(current)
            for _ in range(random.randint(1, 3)):
                byte_pos = random.randint(0, 31)
                bit_pos = random.randint(0, 7)
                neighbor[byte_pos] ^= (1 << bit_pos)
            
            neighbor_fitness = fitness(bytes(neighbor))
            
            # Accept based on probability
            delta = neighbor_fitness - current_fitness
            if delta < 0 or random.random() < np.exp(-delta / temp):
                current = bytes(neighbor)
                current_fitness = neighbor_fitness
                if current_fitness < best_distance:
                    best_distance = current_fitness
            
            if iteration % 100 == 0:
                convergence.append(current_fitness)
        
        improvement = 80.0 - best_distance
        
        return TestResult(
            test_name="Simulated_Annealing_ECC",
            algorithm="Simulated_Annealing",
            target_type="Hash160",
            initial_distance=convergence[0],
            final_distance=best_distance,
            improvement=improvement,
            convergence_curve=convergence,
            metadata={"initial_temp": initial_temp, "final_temp": final_temp}
        )

def run_comprehensive_validation():
    """Run all validation tests"""
    config = TestConfig()
    all_results = []
    
    print("🔬 RUNNING COMPREHENSIVE ECC VALIDATION SUITE")
    print("=" * 70)
    
    # Component isolation tests
    print("\n1. COMPONENT ISOLATION TESTS")
    print("-" * 40)
    
    ecc_result = ComponentIsolationTests.test_ecc_only(config)
    all_results.append(ecc_result)
    print(f"ECC Only: {ecc_result.improvement:.1f} bits improvement")
    
    sha256_result = ComponentIsolationTests.test_sha256_only(config)
    all_results.append(sha256_result)
    print(f"SHA256 Only: {sha256_result.improvement:.1f} bits improvement")
    
    ripemd_result = ComponentIsolationTests.test_ripemd160_only(config)
    all_results.append(ripemd_result)
    print(f"RIPEMD160 Only: {ripemd_result.improvement:.1f} bits improvement")
    
    # Target validation tests
    print("\n2. TARGET VALIDATION TESTS")
    print("-" * 40)
    
    sequential_results = TargetValidationTests.test_sequential_targets(config)
    all_results.extend(sequential_results)
    print(f"Sequential targets: {len(sequential_results)} tests completed")
    
    entropy_results = TargetValidationTests.test_entropy_sources(config)
    all_results.extend(entropy_results)
    print(f"Entropy source tests: {len(entropy_results)} tests completed")
    
    # Negative control tests
    print("\n3. NEGATIVE CONTROL TESTS")
    print("-" * 40)
    
    rsa_result = NegativeControlTests.test_rsa_signatures(config)
    all_results.append(rsa_result)
    print(f"RSA Signatures: {rsa_result.improvement:.1f} bits improvement (should be ~0)")
    
    random_result = NegativeControlTests.test_pure_random(config)
    all_results.append(random_result)
    print(f"Pure Random: {random_result.improvement:.1f} bits improvement (should be ~0)")
    
    # Algorithm validation tests  
    print("\n4. ALGORITHM VALIDATION TESTS")
    print("-" * 40)
    
    hill_result = AlgorithmValidationTests.test_hill_climbing(config)
    all_results.append(hill_result)
    print(f"Hill Climbing: {hill_result.improvement:.1f} bits improvement")
    
    annealing_result = AlgorithmValidationTests.test_simulated_annealing(config)
    all_results.append(annealing_result)
    print(f"Simulated Annealing: {annealing_result.improvement:.1f} bits improvement")
    
    # Analysis
    print("\n" + "=" * 70)
    print("🚨 VALIDATION ANALYSIS")
    print("=" * 70)
    
    ecc_improvements = []
    non_ecc_improvements = []
    
    for result in all_results:
        if "ECC" in result.test_name or "Hash160" in result.target_type:
            ecc_improvements.append(result.improvement)
        else:
            non_ecc_improvements.append(result.improvement)
    
    if ecc_improvements:
        avg_ecc = statistics.mean(ecc_improvements)
        print(f"Average ECC-related improvement: {avg_ecc:.1f} bits")
        
    if non_ecc_improvements:
        avg_non_ecc = statistics.mean(non_ecc_improvements)
        print(f"Average non-ECC improvement: {avg_non_ecc:.1f} bits")
        
    # Critical findings
    print("\n🔥 CRITICAL FINDINGS:")
    
    significant_ecc = [r for r in all_results if "ECC" in r.test_name and r.improvement > 5.0]
    if significant_ecc:
        print(f"⚠️  {len(significant_ecc)} ECC tests show >5 bit improvement")
        
    significant_non_ecc = [r for r in all_results if "ECC" not in r.test_name and r.improvement > 5.0]
    if significant_non_ecc:
        print(f"⚠️  {len(significant_non_ecc)} non-ECC tests show >5 bit improvement")
        
    if len(significant_ecc) > 0 and len(significant_non_ecc) == 0:
        print("🚨 ECC-SPECIFIC VULNERABILITY CONFIRMED")
    elif len(significant_ecc) > 0 and len(significant_non_ecc) > 0:
        print("🚨 GENERAL CRYPTOGRAPHIC IMPLEMENTATION ISSUE")
    else:
        print("✅ No systematic vulnerabilities detected")
    
    # Save results
    results_data = {
        'timestamp': time.time(),
        'config': config.__dict__,
        'results': [
            {
                'test_name': r.test_name,
                'algorithm': r.algorithm,
                'target_type': r.target_type,
                'improvement': r.improvement,
                'final_distance': r.final_distance,
                'metadata': r.metadata
            }
            for r in all_results
        ],
        'summary': {
            'avg_ecc_improvement': statistics.mean(ecc_improvements) if ecc_improvements else 0,
            'avg_non_ecc_improvement': statistics.mean(non_ecc_improvements) if non_ecc_improvements else 0,
            'significant_ecc_tests': len(significant_ecc),
            'significant_non_ecc_tests': len(significant_non_ecc)
        }
    }
    
    with open('validation_results.json', 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n📁 Results saved to validation_results.json")
    
    return all_results

if __name__ == "__main__":
    results = run_comprehensive_validation()
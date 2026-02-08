#!/usr/bin/env python3
"""
SAFE TEST: Bitcoin Cryptographic Pipeline vs GF(3) Theory
Tests if Bitcoin's actual crypto stack exhibits GF(3) vulnerabilities
WITHOUT attacking real Bitcoin - uses test vectors only
"""

import hashlib
import time
import random
from typing import Tuple, List, Dict
import hmac

# Import your actual GA engine
from turing import SubstrateProblem, SubstrateDetectorEngine, AtomicGAConfig
from turing2 import GF27, randbytes

# Safe test constants - NOT real Bitcoin data
TEST_PRIVKEYS = [randbytes(32) for _ in range(10)]  # Random test keys
TEST_BLOCK_HEIGHT = 123456  # Fake block number
DIFFICULTY_BITS = 20  # Much easier than real Bitcoin (256 bits)

class BitcoinMiningProblem(SubstrateProblem):
    """Test Bitcoin's PoW (double SHA-256) for GF(3) structure"""
    
    def __init__(self, difficulty_bits=20):
        self.difficulty_bits = difficulty_bits
        self.target = 2 ** (256 - difficulty_bits)
        self.block_template = b"TEST_BLOCK_" + randbytes(64)  # Fake block
        
    def evaluate(self, solution: bytes) -> float:
        """Bitcoin mining fitness: how close to valid PoW"""
        # Actual Bitcoin: SHA256(SHA256(header))
        hash1 = hashlib.sha256(self.block_template + solution).digest()
        hash2 = hashlib.sha256(hash1).digest()
        
        # Convert to number
        hash_num = int.from_bytes(hash2, 'big')
        
        # Distance to target (log scale for better GA performance)
        if hash_num < self.target:
            return 0.0  # Found valid block!
        
        # Leading zeros as fitness
        leading_zeros = 256 - hash_num.bit_length()
        return float(self.difficulty_bits - leading_zeros)
    
    def get_random_target(self):
        return self.target
    
    def get_max_score(self):
        return float(self.difficulty_bits)
    
    def describe(self):
        return f"Bitcoin Mining (double SHA-256), {self.difficulty_bits} bit difficulty"

class BitcoinAddressProblem(SubstrateProblem):
    """Test Bitcoin's address generation for GF(3) structure"""
    
    def __init__(self):
        # Generate a test "vanity address" target
        self.target_prefix = b"1TEST"  # Vanity address prefix
        self.target_checksum = randbytes(4)  # Random checksum
        
    def evaluate(self, solution: bytes) -> float:
        """Bitcoin address generation fitness"""
        # Actual Bitcoin: RIPEMD160(SHA256(pubkey))
        sha = hashlib.sha256(solution).digest()
        h = hashlib.new('ripemd160')
        h.update(sha)
        hash160 = h.digest()
        
        # Add version byte
        versioned = b'\x00' + hash160
        
        # Checksum = first 4 bytes of SHA256(SHA256(versioned))
        checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
        
        # Base58 would go here, but we'll test the raw bytes
        # Score based on matching prefix and checksum
        prefix_match = sum(1 for a, b in zip(versioned[:5], self.target_prefix) if a == b)
        checksum_match = sum(1 for a, b in zip(checksum, self.target_checksum) if a == b)
        
        return float(20 - (prefix_match * 3 + checksum_match))
    
    def get_random_target(self):
        return self.target_prefix + self.target_checksum
    
    def get_max_score(self):
        return 20.0
    
    def describe(self):
        return "Bitcoin Address Generation (RIPEMD160+SHA256)"

class BitcoinSignatureProblem(SubstrateProblem):
    """Test Bitcoin's ECDSA for GF(3) structure (simplified)"""
    
    def __init__(self):
        self.message = b"Test transaction"
        self.target_r = randbytes(32)  # Target signature component
        
    def evaluate(self, solution: bytes) -> float:
        """ECDSA signature fitness (simplified for safety)"""
        # We won't implement full secp256k1, just test the hash structure
        # Bitcoin uses: sign(SHA256(SHA256(message)), privkey)
        
        msg_hash = hashlib.sha256(hashlib.sha256(self.message).digest()).digest()
        
        # Simulate ECDSA's use of HMAC-SHA256 for deterministic k
        k = hmac.new(solution[:32], msg_hash, hashlib.sha256).digest()
        
        # Distance to target signature component
        distance = sum(abs(a - b) for a, b in zip(k, self.target_r))
        return float(distance) / 256
    
    def get_random_target(self):
        return self.target_r
    
    def get_max_score(self):
        return 256.0
    
    def describe(self):
        return "Bitcoin ECDSA Signature (simplified)"

class CascadedBitcoinProblem(SubstrateProblem):
    """Test full Bitcoin pipeline cascaded together"""
    
    def __init__(self):
        self.mining = BitcoinMiningProblem(16)  # Easier difficulty
        self.address = BitcoinAddressProblem()
        self.signature = BitcoinSignatureProblem()
        
    def evaluate(self, solution: bytes) -> float:
        """Combined Bitcoin pipeline fitness"""
        # Split solution into three parts
        part1 = solution[:len(solution)//3]
        part2 = solution[len(solution)//3:2*len(solution)//3]
        part3 = solution[2*len(solution)//3:]
        
        # Each stage feeds into the next (cascading)
        mining_score = self.mining.evaluate(part1)
        
        # Use mining output to influence address generation
        if mining_score < 5:  # Good mining result
            modified_part2 = bytes(a ^ b for a, b in zip(part2, part1[:len(part2)]))
            address_score = self.address.evaluate(modified_part2)
        else:
            address_score = self.address.evaluate(part2)
        
        # Use address output to influence signature
        if address_score < 10:  # Good address result
            modified_part3 = bytes(a ^ b for a, b in zip(part3, part2[:len(part3)]))
            sig_score = self.signature.evaluate(modified_part3)
        else:
            sig_score = self.signature.evaluate(part3)
        
        # Combined score with cascading bonus
        cascade_bonus = max(0, 10 - mining_score) * max(0, 15 - address_score) * 0.01
        return mining_score + address_score + sig_score - cascade_bonus
    
    def get_random_target(self):
        return None
    
    def get_max_score(self):
        return 300.0
    
    def describe(self):
        return "Cascaded Bitcoin Pipeline (Mining→Address→Signature)"

def test_bitcoin_gf3_vulnerability():
    """Main test: Does Bitcoin's crypto exhibit GF(3) structure?"""
    print("🔐 TESTING BITCOIN CRYPTOGRAPHIC PIPELINE FOR GF(3) VULNERABILITY")
    print("=" * 70)
    print("⚠️  SAFE TEST - Using test vectors only, NOT attacking real Bitcoin!")
    print("=" * 70)
    
    config = AtomicGAConfig()
    config.MAX_ROUNDS = 50
    config.K_POOL = 5000  # Larger population for crypto problems
    
    analyzer = GF27EmbeddingAnalyzer()
    results = {}
    
    # Test 1: Mining (Double SHA-256)
    print("\n1️⃣ BITCOIN MINING (Proof of Work)")
    for difficulty in [16, 20, 24]:
        print(f"\n   Testing {difficulty}-bit difficulty...")
        problem = BitcoinMiningProblem(difficulty)
        
        # Check GF(27) embedding
        embedding = analyzer.analyze_problem_embedding(problem)
        print(f"   GF(27) embedding quality: {embedding['embedding_quality']:.3f}")
        
        # Run GA
        engine = SubstrateDetectorEngine(config)
        ga_results = engine.run_substrate_detection(problem, problem.get_random_target())
        
        print(f"   GA improvement: {ga_results['improvement_bits']:.1f} bits")
        print(f"   Best score: {ga_results['final_best']:.1f}")
        
        results[f'mining_{difficulty}'] = {
            'embedding': embedding['embedding_quality'],
            'improvement': ga_results['improvement_bits'],
            'final_score': ga_results['final_best']
        }
    
    # Test 2: Address Generation
    print("\n2️⃣ BITCOIN ADDRESS GENERATION")
    problem = BitcoinAddressProblem()
    
    embedding = analyzer.analyze_problem_embedding(problem)
    print(f"   GF(27) embedding quality: {embedding['embedding_quality']:.3f}")
    
    engine = SubstrateDetectorEngine(config)
    ga_results = engine.run_substrate_detection(problem, problem.get_random_target())
    
    print(f"   GA improvement: {ga_results['improvement_bits']:.1f} bits")
    
    results['address'] = {
        'embedding': embedding['embedding_quality'],
        'improvement': ga_results['improvement_bits']
    }
    
    # Test 3: ECDSA Signatures
    print("\n3️⃣ BITCOIN ECDSA SIGNATURES")
    problem = BitcoinSignatureProblem()
    
    embedding = analyzer.analyze_problem_embedding(problem)
    print(f"   GF(27) embedding quality: {embedding['embedding_quality']:.3f}")
    
    engine = SubstrateDetectorEngine(config)
    ga_results = engine.run_substrate_detection(problem, problem.get_random_target())
    
    print(f"   GA improvement: {ga_results['improvement_bits']:.1f} bits")
    
    results['ecdsa'] = {
        'embedding': embedding['embedding_quality'],
        'improvement': ga_results['improvement_bits']
    }
    
    # Test 4: CASCADED ATTACK
    print("\n4️⃣ CASCADED BITCOIN PIPELINE ATTACK")
    problem = CascadedBitcoinProblem()
    
    # Run multiple times to check consistency
    improvements = []
    for run in range(3):
        print(f"\n   Run {run+1}/3...")
        engine = SubstrateDetectorEngine(config)
        ga_results = engine.run_substrate_detection(problem, None)
        improvements.append(ga_results['improvement_bits'])
        print(f"   Improvement: {ga_results['improvement_bits']:.1f} bits")
    
    avg_cascaded = sum(improvements) / len(improvements)
    
    # Analysis
    print("\n" + "=" * 70)
    print("📊 VULNERABILITY ANALYSIS")
    print("=" * 70)
    
    # Check if improvements match GF(3) theory
    individual_sum = (results['mining_20']['improvement'] + 
                     results['address']['improvement'] + 
                     results['ecdsa']['improvement'])
    
    amplification = avg_cascaded / max(individual_sum, 1)
    
    print(f"\nIndividual improvements sum: {individual_sum:.1f} bits")
    print(f"Cascaded improvement: {avg_cascaded:.1f} bits")
    print(f"Amplification factor: {amplification:.2f}x")
    
    if amplification > 1.5:
        print("\n⚠️  WARNING: Cascading amplification detected!")
        print("   Bitcoin's pipeline shows multiplicative GF(3) vulnerability")
    else:
        print("\n✅ SAFE: No significant cascading amplification")
        print("   Bitcoin's pipeline appears resistant to GF(3) attacks")
    
    # Check if near 27-bit multiples
    for name, result in results.items():
        if result['improvement'] > 20:
            quotient = result['improvement'] / 27
            if abs(quotient - round(quotient)) < 0.2:
                print(f"\n🎯 {name}: {result['improvement']:.1f} bits ≈ {round(quotient)} × 27!")
    
    return results

# GF(27) Embedding Analyzer (from your code)
class GF27EmbeddingAnalyzer:
    def __init__(self):
        self.gf = GF27()
    
    def analyze_problem_embedding(self, problem: SubstrateProblem, samples: int = 100) -> Dict:
        embedding_scores = []
        structure_scores = []
        trace_entropies = []
        
        for _ in range(samples):
            test_solution = randbytes(32)
            elements = self.gf.embed_bytes(test_solution)
            
            # Analyze trace distribution
            trace_counts = [0, 0, 0]
            for elem in elements:
                tr = self.gf.trace(elem)
                trace_counts[tr] += 1
            
            total = sum(trace_counts)
            entropy = 0
            for count in trace_counts:
                if count > 0:
                    p = count / total
                    import math
                    entropy -= p * math.log2(p)
            
            normalized_entropy = entropy / math.log2(3) if entropy > 0 else 0
            trace_entropies.append(normalized_entropy)
        
        avg_entropy = sum(trace_entropies) / len(trace_entropies)
        embedding_quality = avg_entropy
        
        return {
            'embedding_quality': embedding_quality,
            'trace_entropy': avg_entropy,
            'predicted_improvement': 27 * embedding_quality
        }

if __name__ == "__main__":
    test_bitcoin_gf3_vulnerability()
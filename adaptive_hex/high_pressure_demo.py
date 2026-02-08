#!/usr/bin/env python3
"""
Full Jericho Convergence Engine Implementation
Testing the claimed ECC vulnerability with real cryptography
"""

import hashlib
import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
import secrets

# Install with: pip install secp256k1 coincurve
try:
    import secp256k1
    has_secp = True
except ImportError:
    has_secp = False
    print("Warning: secp256k1 not found, using coincurve")
    from coincurve import PrivateKey, PublicKey

@dataclass
class Config:
    """Jericho configuration parameters as specified"""
    K: int = 5  # Elite pool size
    MICRO_N: int = 200_000
    MICRO_PASSES: int = 200
    MAX_PASSES: int = 5000
    ALPHA: float = 0.02
    EPSILON: float = 1e-6
    ETA_0: float = 0.02
    TAU_0: float = 2.0
    T_TAU: float = 500.0
    PCA_UPDATE_FREQ: int = 5
    PCA_THRESH: float = 0.08
    COV_THRESH: float = 0.02
    SAMPLER_WEIGHTS: List[float] = None
    CHUNK_SCHEDULE: List[Tuple[int, int]] = None
    
    def __post_init__(self):
        if self.SAMPLER_WEIGHTS is None:
            self.SAMPLER_WEIGHTS = [2.0, 2.0, 1.0, 1.0, 1.0]
        if self.CHUNK_SCHEDULE is None:
            self.CHUNK_SCHEDULE = [(0, 32), (3, 16), (6, 8)]

class ECCOperations:
    """Real ECC operations using secp256k1"""
    
    def __init__(self):
        if has_secp:
            self.ctx = secp256k1.lib.secp256k1_context_create(
                secp256k1.lib.SECP256K1_CONTEXT_SIGN | 
                secp256k1.lib.SECP256K1_CONTEXT_VERIFY
            )
        
    def private_to_public(self, private_key: bytes) -> bytes:
        """Convert 32-byte private key to 33-byte compressed public key"""
        if has_secp:
            pubkey = secp256k1.PublicKey(ctx=self.ctx)
            success = secp256k1.lib.secp256k1_ec_pubkey_create(
                self.ctx, pubkey.public_key, private_key
            )
            if not success:
                return None
            return pubkey.serialize(compressed=True)
        else:
            try:
                pk = PrivateKey(private_key)
                return pk.public_key.format(compressed=True)
            except:
                return None
    
    def hash160(self, public_key: bytes) -> bytes:
        """Bitcoin-style hash160 of public key"""
        sha256_hash = hashlib.sha256(public_key).digest()
        return hashlib.new('ripemd160', sha256_hash).digest()

class StructuredSamplers:
    """Structured samplers as described in the disclosure"""
    
    @staticmethod
    def golden_ratio_seed(i: int) -> bytes:
        """Golden ratio sampler"""
        phi = (1 + np.sqrt(5)) / 2
        value = int((phi ** (i % 64) * 1e9)) & ((1 << 256) - 1)
        return value.to_bytes(32, 'big')
    
    @staticmethod
    def crt_lattice_seed(i: int) -> bytes:
        """Chinese Remainder Theorem lattice sampler"""
        m1 = 1 << 128
        m2 = m1 - 59
        a = i % m1
        b = i % m2
        # Extended Euclidean algorithm for modular inverse
        inv = pow(m1, -1, m2)
        value = (a + m1 * ((b - a) * inv % m2)) & ((1 << 256) - 1)
        return value.to_bytes(32, 'big')
    
    @staticmethod
    def palindromic_seed(i: int) -> bytes:
        """Palindromic bit pattern sampler"""
        half = i & ((1 << 128) - 1)
        # Create palindrome
        binary = format(half, '0128b')
        palindrome = binary + binary[::-1]
        value = int(palindrome, 2)
        return value.to_bytes(32, 'big')
    
    @staticmethod
    def fractal_modular_seed(i: int) -> bytes:
        """Fractal modular exponentiation sampler"""
        value = pow(i + 1, (i % 128) + 2, 1 << 256)
        return value.to_bytes(32, 'big')
    
    @staticmethod
    def automorphism_seed(i: int) -> bytes:
        """Automorphism-based sampler"""
        LAMBDA = (1 << 128) + 1
        a = i & ((1 << 256) - 1)
        b = (i >> 128) & ((1 << 256) - 1)
        value = (a + b * LAMBDA) & ((1 << 256) - 1)
        return value.to_bytes(32, 'big')

class MutationEngine:
    """Advanced mutation strategies"""
    
    def __init__(self, config: Config):
        self.config = config
        self.weights = np.array([0.5] * 256, dtype=np.float32)
        self.eta = np.array([config.ETA_0] * 256, dtype=np.float32)
        self.C = np.zeros((256, 256), dtype=np.float32)  # Covariance matrix
        
    def mutate_bits(self, key: bytes) -> bytes:
        """Weighted bit mutation"""
        key_array = bytearray(key)
        for j in range(256):
            if np.random.random() < self.weights[j]:
                byte_idx = j // 8
                bit_idx = j % 8
                key_array[byte_idx] ^= (1 << bit_idx)
        return bytes(key_array)
    
    def chunk_flip(self, key: bytes, size: int) -> bytes:
        """Flip contiguous chunk of bits"""
        key_array = bytearray(key)
        offset = np.random.randint(0, 256 - size + 1)
        for j in range(offset, offset + size):
            byte_idx = j // 8
            bit_idx = j % 8
            key_array[byte_idx] ^= (1 << bit_idx)
        return bytes(key_array)
    
    def de_combine(self, a: bytes, b: bytes, c: bytes) -> bytes:
        """Differential Evolution recombination"""
        result = bytearray(32)
        for i in range(32):
            mask = np.random.randint(0, 256)
            result[i] = a[i] ^ ((b[i] ^ c[i]) & mask)
        return bytes(result)
    
    def pca_flip(self, key: bytes) -> bytes:
        """PCA-guided mutations using covariance matrix"""
        if np.sum(np.abs(self.C)) < 1e-6:  # Covariance not ready
            return self.mutate_bits(key)
        
        # Compute eigendecomposition
        try:
            eigvals, eigvecs = np.linalg.eigh(self.C)
            # Use top 3 eigenvectors
            key_array = bytearray(key)
            for i in range(min(3, len(eigvals))):
                vec = eigvecs[:, -(i+1)]  # Largest eigenvalues last
                for j in range(256):
                    if abs(vec[j]) > self.config.PCA_THRESH:
                        if np.random.random() < 0.5:
                            byte_idx = j // 8
                            bit_idx = j % 8
                            key_array[byte_idx] ^= (1 << bit_idx)
            return bytes(key_array)
        except:
            return self.mutate_bits(key)
    
    def block_flip(self, key: bytes) -> bytes:
        """Correlated block mutations based on covariance"""
        key_array = bytearray(key)
        # Find correlated bit clusters
        clusters = []
        visited = [False] * 256
        
        for i in range(256):
            if visited[i]:
                continue
            cluster = [i]
            visited[i] = True
            for j in range(i + 1, 256):
                if abs(self.C[i, j]) > self.config.COV_THRESH:
                    cluster.append(j)
                    visited[j] = True
            if len(cluster) > 1:
                clusters.append(cluster)
        
        # Flip correlated clusters
        if clusters:
            cluster = clusters[np.random.randint(len(clusters))]
            for bit_idx in cluster:
                if np.random.random() < 0.5:
                    byte_idx = bit_idx // 8
                    bit_pos = bit_idx % 8
                    key_array[byte_idx] ^= (1 << bit_pos)
        
        return bytes(key_array)
    
    def update_weights(self, improved_bits: List[int], tau: float):
        """Update bit weights based on which bits improved"""
        # Decay all weights
        self.weights *= (1 - self.config.ALPHA)
        
        # Boost weights for bits that improved
        for bit_idx in improved_bits:
            self.weights[bit_idx] = min(
                self.weights[bit_idx] + self.eta[bit_idx],
                1.0 - self.config.EPSILON
            )
        
        # Update learning rates
        self.eta *= 0.99
        
    def update_covariance(self, pool: List[bytes]):
        """Update covariance matrix from elite pool"""
        if len(pool) < 2:
            return
        
        # Convert pool to bit matrix
        bit_matrix = np.zeros((len(pool), 256))
        for i, key in enumerate(pool):
            for j in range(32):
                for k in range(8):
                    bit_idx = j * 8 + k
                    bit_matrix[i, bit_idx] = (key[j] >> k) & 1
        
        # Compute covariance
        self.C = np.cov(bit_matrix.T)

class JerichoEngine:
    """The main Jericho Convergence Engine"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.ecc = ECCOperations()
        self.mutation = MutationEngine(self.config)  # Pass self.config, not config
        self.samplers = [
            StructuredSamplers.golden_ratio_seed,
            StructuredSamplers.crt_lattice_seed,
            StructuredSamplers.palindromic_seed,
            StructuredSamplers.fractal_modular_seed,
            StructuredSamplers.automorphism_seed
        ]
        
        self.pool = []  # Elite pool
        self.scores = []  # Hamming distances
        self.attempts = 0
        self.tau = self.config.TAU_0
        
    def hamming_distance(self, a: bytes, b: bytes) -> int:
        """Calculate Hamming distance between two byte strings"""
        return sum(bin(x ^ y).count('1') for x, y in zip(a, b))
    
    def evaluate_key(self, private_key: bytes, target_hash160: bytes) -> Optional[int]:
        """Evaluate a private key against target"""
        public_key = self.ecc.private_to_public(private_key)
        if public_key is None:
            return None
        
        hash160 = self.ecc.hash160(public_key)
        return self.hamming_distance(hash160, target_hash160)
    
    def initialize_pool(self, target_hash160: bytes):
        """Initialize elite pool with structured samples"""
        print("Initializing elite pool with structured samplers...")
        
        for i in range(self.config.K):
            for j, sampler in enumerate(self.samplers):
                key = sampler(i * len(self.samplers) + j)
                distance = self.evaluate_key(key, target_hash160)
                if distance is not None:
                    self.pool.append(key)
                    self.scores.append(distance)
                    
        # Keep only top K
        if len(self.pool) > self.config.K:
            indices = np.argsort(self.scores)[:self.config.K]
            self.pool = [self.pool[i] for i in indices]
            self.scores = [self.scores[i] for i in indices]
    
    def evolve_pool(self, target_hash160: bytes) -> Tuple[int, bytes]:
        """One evolution pass of the pool"""
        candidates = []
        candidate_scores = []
        
        # Generate mutations
        for _ in range(self.config.MICRO_N):
            # Select mutation strategy
            strategy = np.random.choice([
                'bit_mutate', 'chunk_flip', 'de_combine', 
                'pca_flip', 'block_flip', 'fresh_sample'
            ], p=[0.3, 0.2, 0.2, 0.15, 0.1, 0.05])
            
            if strategy == 'bit_mutate':
                parent = self.pool[np.random.randint(len(self.pool))]
                child = self.mutation.mutate_bits(parent)
            
            elif strategy == 'chunk_flip':
                parent = self.pool[np.random.randint(len(self.pool))]
                chunk_size = self.get_chunk_size()
                child = self.mutation.chunk_flip(parent, chunk_size)
            
            elif strategy == 'de_combine':
                if len(self.pool) >= 3:
                    indices = np.random.choice(len(self.pool), 3, replace=False)
                    child = self.mutation.de_combine(
                        self.pool[indices[0]],
                        self.pool[indices[1]],
                        self.pool[indices[2]]
                    )
                else:
                    continue
            
            elif strategy == 'pca_flip':
                parent = self.pool[np.random.randint(len(self.pool))]
                child = self.mutation.pca_flip(parent)
            
            elif strategy == 'block_flip':
                parent = self.pool[np.random.randint(len(self.pool))]
                child = self.mutation.block_flip(parent)
            
            else:  # fresh_sample
                sampler = np.random.choice(self.samplers)
                child = sampler(np.random.randint(1000000))
            
            # Evaluate
            distance = self.evaluate_key(child, target_hash160)
            if distance is not None:
                candidates.append(child)
                candidate_scores.append(distance)
            
            self.attempts += 1
        
        # Update pool with best candidates
        all_keys = self.pool + candidates
        all_scores = self.scores + candidate_scores
        
        # Keep top K
        indices = np.argsort(all_scores)[:self.config.K]
        new_pool = [all_keys[i] for i in indices]
        new_scores = [all_scores[i] for i in indices]
        
        # Find which bits improved
        if new_scores[0] < self.scores[0]:
            old_best = self.pool[0]
            new_best = new_pool[0]
            improved_bits = []
            for i in range(256):
                byte_idx = i // 8
                bit_idx = i % 8
                old_bit = (old_best[byte_idx] >> bit_idx) & 1
                new_bit = (new_best[byte_idx] >> bit_idx) & 1
                if old_bit != new_bit:
                    improved_bits.append(i)
            self.mutation.update_weights(improved_bits, self.tau)
        
        self.pool = new_pool
        self.scores = new_scores
        
        # Update covariance periodically
        if self.attempts % (self.config.PCA_UPDATE_FREQ * self.config.MICRO_N) == 0:
            self.mutation.update_covariance(self.pool)
        
        # Update tau
        self.tau = self.config.TAU_0 * np.exp(-self.attempts / self.config.T_TAU)
        
        return self.scores[0], self.pool[0]
    
    def get_chunk_size(self) -> int:
        """Get chunk size based on schedule"""
        progress = self.attempts / (self.config.MAX_PASSES * self.config.MICRO_N)
        for threshold, size in self.config.CHUNK_SCHEDULE:
            if progress * 10 <= threshold:
                return size
        return 8  # Default
    
    def attack(self, target_hash160: bytes) -> dict:
        """Main attack loop"""
        start_time = time.time()
        
        print(f"\nStarting Jericho Convergence Engine attack")
        print(f"Target hash160: {target_hash160.hex()}")
        print(f"Configuration: K={self.config.K}, MICRO_N={self.config.MICRO_N}")
        print("-" * 60)
        
        # Initialize
        self.initialize_pool(target_hash160)
        best_distance = min(self.scores)
        print(f"Initial best distance: {best_distance} bits")
        
        # Main evolution loop
        pass_count = 0
        last_improvement = 0
        
        while pass_count < self.config.MAX_PASSES:
            # Evolve
            for _ in range(self.config.MICRO_PASSES):
                distance, key = self.evolve_pool(target_hash160)
                
                if distance < best_distance:
                    best_distance = distance
                    elapsed = time.time() - start_time
                    rate = self.attempts / elapsed
                    print(f"Pass {pass_count}, Attempts: {self.attempts:,}, "
                          f"Distance: {distance} bits, Rate: {rate:.0f} ops/s")
                    last_improvement = pass_count
                    
                    # Check convergence
                    mean_distance = np.mean(self.scores)
                    if mean_distance <= 25.0:
                        print(f"\nCONVERGED! Mean distance: {mean_distance:.1f} bits")
                        print(f"Best distance: {best_distance} bits")
                        print(f"Time: {elapsed:.2f}s")
                        return {
                            'success': True,
                            'best_distance': best_distance,
                            'mean_distance': mean_distance,
                            'attempts': self.attempts,
                            'time': elapsed,
                            'best_key': self.pool[0],
                            'pool': self.pool.copy()
                        }
            
            pass_count += 1
            
            # Progress report
            if pass_count % 10 == 0:
                elapsed = time.time() - start_time
                rate = self.attempts / elapsed
                mean_distance = np.mean(self.scores)
                print(f"Pass {pass_count}: Best={best_distance}, "
                      f"Mean={mean_distance:.1f}, Rate={rate:.0f} ops/s")
            
            # Check for stagnation
            if pass_count - last_improvement > 50:
                print("Stagnation detected, refreshing pool...")
                # Keep best, refresh rest
                best = self.pool[0]
                self.initialize_pool(target_hash160)
                self.pool[0] = best
                self.scores[0] = best_distance
                last_improvement = pass_count
        
        # Failed to converge
        elapsed = time.time() - start_time
        mean_distance = np.mean(self.scores)
        print(f"\nFailed to converge after {self.attempts:,} attempts")
        print(f"Best distance: {best_distance} bits")
        print(f"Mean distance: {mean_distance:.1f} bits")
        print(f"Time: {elapsed:.2f}s")
        
        return {
            'success': False,
            'best_distance': best_distance,
            'mean_distance': mean_distance,
            'attempts': self.attempts,
            'time': elapsed,
            'best_key': self.pool[0] if self.pool else None,
            'pool': self.pool.copy()
        }

def test_attack():
    """Test the Jericho attack with real ECC"""
    print("=" * 60)
    print("JERICHO CONVERGENCE ENGINE TEST")
    print("Testing with real secp256k1 ECC operations")
    print("=" * 60)
    
    # Generate a real target
    target_private = secrets.token_bytes(32)
    ecc = ECCOperations()
    target_public = ecc.private_to_public(target_private)
    target_hash160 = ecc.hash160(target_public)
    
    print(f"\nTarget private key: {target_private.hex()}")
    print(f"Target public key:  {target_public.hex()}")
    print(f"Target hash160:     {target_hash160.hex()}")
    
    # Run attack
    engine = JerichoEngine()
    result = engine.attack(target_hash160)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("ATTACK RESULTS ANALYSIS")
    print("=" * 60)
    
    if result['success']:
        print(f"Attack claims convergence with mean distance: {result['mean_distance']:.1f}")
        print(f"Best distance achieved: {result['best_distance']} bits")
        
        # Check if we actually found the key
        if result['best_key'] == target_private:
            print("\n⚠️  CRITICAL: Attack found the actual private key!")
            print("This would be a complete break of ECC!")
        else:
            print("\n✓ Attack did NOT find the actual private key")
            print(f"Found key:   {result['best_key'].hex()}")
            print(f"Target key:  {target_private.hex()}")
            
            # Verify the claimed distance
            found_public = ecc.private_to_public(result['best_key'])
            found_hash = ecc.hash160(found_public)
            actual_distance = sum(bin(a ^ b).count('1') for a, b in zip(found_hash, target_hash160))
            print(f"\nVerified Hamming distance: {actual_distance} bits")
    else:
        print(f"Attack failed to converge")
        print(f"Best distance achieved: {result['best_distance']} bits")
        print(f"Mean distance of pool: {result['mean_distance']:.1f} bits")
    
    print(f"\nTotal attempts: {result['attempts']:,}")
    print(f"Time taken: {result['time']:.2f} seconds")
    print(f"Rate: {result['attempts']/result['time']:.0f} operations/second")
    
    # Mathematical analysis
    print("\n" + "=" * 60)
    print("MATHEMATICAL ANALYSIS")
    print("=" * 60)
    print("Even if Hamming distance converges to 0:")
    print("1. That means finding a collision in RIPEMD160(SHA256(pubkey))")
    print("2. Due to 256->160 bit reduction, ~2^96 private keys map to same hash160")
    print("3. Finding ANY of them still requires reversing the one-way functions")
    print("4. The mutations don't follow the algebraic structure of ECC")
    print("\nConclusion: Low Hamming distance ≠ Breaking ECC")

if __name__ == "__main__":
    test_attack()
    
    # Note about defenses
    print("\n" + "=" * 60)
    print("ABOUT THE PROPOSED DEFENSES")
    print("=" * 60)
    print("The disclosure's defenses will be tested in the follow-up script")
    print("if this attack shows any real convergence beyond random chance.")
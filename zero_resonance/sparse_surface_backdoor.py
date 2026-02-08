#!/usr/bin/env python3
"""
ECC SPARSE SURFACE BACKDOOR EXPLORER
Tests if sparse patterns reveal hidden ECC structure that could be exploited
"""

import hashlib
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
from scipy import stats
from ecdsa import SigningKey, SECP256k1
from Crypto.Hash import RIPEMD160
import json
import time
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import warnings
warnings.filterwarnings('ignore')

SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

class ECCBackdoorExplorer:
    """Explore potential ECC backdoor via sparse pattern analysis"""
    
    def __init__(self):
        self.null_surface = {}
        self.sparse_approximations = defaultdict(list)
        self.pattern_map = {}
        self.collision_candidates = defaultdict(list)
        
    def hash160(self, data: bytes) -> bytes:
        """SHA256 + RIPEMD160"""
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()
    
    def private_key_to_hash160(self, privkey_int: int) -> bytes:
        """Convert private key int to hash160, handling invalid keys"""
        # For invalid keys (like 0x00), we still compute what the hash WOULD be
        # This lets us map the "forbidden space"
        
        if privkey_int == 0:
            # Special handling for null key - compute hypothetical output
            # Use the identity point behavior
            return self.hash160(b'\x00' * 33)  # Null pubkey representation
        
        # Ensure valid range for real keys
        if privkey_int >= SECP256K1_ORDER:
            privkey_int = privkey_int % (SECP256K1_ORDER - 1) + 1
            
        try:
            privkey_bytes = privkey_int.to_bytes(32, 'big')
            sk = SigningKey.from_string(privkey_bytes, curve=SECP256k1)
            vk = sk.verifying_key
            point = vk.pubkey.point
            
            # Compressed public key
            x = point.x()
            y = point.y()
            prefix = 0x02 if (y % 2 == 0) else 0x03
            pubkey = bytes([prefix]) + x.to_bytes(32, 'big')
            
            return self.hash160(pubkey)
        except:
            # For any invalid key, return a deterministic "error" hash
            return self.hash160(privkey_int.to_bytes(32, 'big'))
    
    def hamming_distance(self, a: bytes, b: bytes) -> int:
        """Hamming distance between two byte strings"""
        if len(a) != len(b):
            return max(len(a), len(b)) * 8
        return sum(bin(x ^ y).count('1') for x, y in zip(a, b))
    
    def generate_sparse_key(self, pattern_type: str, param: int = None) -> int:
        """Generate different types of sparse keys"""
        if pattern_type == "front_loaded":
            # Data at front, zeros at back
            if param is None:
                param = np.random.randint(1, 8)
            key_bytes = bytearray(32)
            for i in range(param):
                key_bytes[i] = np.random.randint(1, 255)
            return int.from_bytes(key_bytes, 'big')
            
        elif pattern_type == "back_loaded":
            # Zeros at front, data at back
            if param is None:
                param = np.random.randint(1, 8)
            key_bytes = bytearray(32)
            for i in range(32 - param, 32):
                key_bytes[i] = np.random.randint(1, 255)
            return int.from_bytes(key_bytes, 'big')
            
        elif pattern_type == "scattered":
            # Random positions
            if param is None:
                param = np.random.randint(4, 12)
            key_bytes = bytearray(32)
            positions = np.random.choice(32, param, replace=False)
            for pos in positions:
                key_bytes[pos] = np.random.randint(1, 255)
            return int.from_bytes(key_bytes, 'big')
            
        elif pattern_type == "sandwich":
            # Data at both ends, zeros in middle
            key_bytes = bytearray(32)
            front = np.random.randint(2, 6)
            back = np.random.randint(2, 6)
            for i in range(front):
                key_bytes[i] = np.random.randint(1, 255)
            for i in range(32 - back, 32):
                key_bytes[i] = np.random.randint(1, 255)
            return int.from_bytes(key_bytes, 'big')
            
        elif pattern_type == "single_bit":
            # Just one bit set
            if param is None:
                param = np.random.randint(0, 256)
            return 1 << param
            
        else:  # "chunked"
            # Alternating chunks
            key_bytes = bytearray(32)
            pos = 0
            while pos < 32:
                if np.random.random() < 0.4:  # 40% data chunks
                    chunk_len = np.random.randint(1, 4)
                    for i in range(min(chunk_len, 32 - pos)):
                        key_bytes[pos + i] = np.random.randint(1, 255)
                pos += np.random.randint(2, 6)
            return int.from_bytes(key_bytes, 'big')
    
    def find_sparse_approximations(self, target_hash: bytes, num_attempts: int = 10000) -> list:
        """Find sparse keys that approximate a target hash160"""
        approximations = []
        pattern_types = ["front_loaded", "back_loaded", "scattered", "sandwich", "single_bit", "chunked"]
        
        for _ in range(num_attempts):
            pattern_type = np.random.choice(pattern_types)
            sparse_key = self.generate_sparse_key(pattern_type)
            
            # Skip if invalid
            if sparse_key == 0 or sparse_key >= SECP256K1_ORDER:
                continue
                
            sparse_hash = self.private_key_to_hash160(sparse_key)
            distance = self.hamming_distance(sparse_hash, target_hash)
            
            if distance < 80:  # Better than random
                approximations.append({
                    'key': sparse_key,
                    'pattern_type': pattern_type,
                    'distance': distance,
                    'hash': sparse_hash.hex(),
                    'sparsity': bin(sparse_key).count('0') / 256
                })
        
        # Sort by distance
        approximations.sort(key=lambda x: x['distance'])
        return approximations[:20]  # Top 20
    
    def map_null_surface(self):
        """Map the surface created by null/trivial keys"""
        print("="*80)
        print("MAPPING NULL SURFACE")
        print("="*80)
        
        # Test various null/trivial keys
        null_keys = [
            0x00,  # The forbidden null
            0x01,  # Minimum valid
            0x02,
            0x03,
            0xFF,
            0x100,
            0xFFFF,
            0x10000,
            0xFFFFFF,
            0x1000000,
            SECP256K1_ORDER - 1,  # Maximum valid
            SECP256K1_ORDER,      # Just over (invalid)
            SECP256K1_ORDER + 1,  # Invalid
        ]
        
        # Add powers of 2
        for i in range(1, 256, 16):
            null_keys.append(1 << i)
        
        print(f"Testing {len(null_keys)} null/trivial keys...")
        
        for null_key in null_keys:
            print(f"\nTesting null key: 0x{null_key:064x}")
            
            # Get the hash160 for this null key
            null_hash = self.private_key_to_hash160(null_key)
            self.null_surface[null_key] = null_hash
            
            print(f"  Hash160: {null_hash.hex()}")
            
            # Find sparse approximations
            print("  Finding sparse approximations...")
            approximations = self.find_sparse_approximations(null_hash, num_attempts=5000)
            
            if approximations:
                print(f"  Found {len(approximations)} approximations")
                best = approximations[0]
                print(f"  Best: {best['distance']} bits, pattern: {best['pattern_type']}, sparsity: {best['sparsity']:.1%}")
                
                self.sparse_approximations[null_key] = approximations
    
    def analyze_sparse_manifold(self):
        """Analyze if sparse approximations form a learnable manifold"""
        print("\n" + "="*80)
        print("ANALYZING SPARSE MANIFOLD")
        print("="*80)
        
        # Collect all sparse keys and their properties
        all_sparse_keys = []
        all_null_keys = []
        all_distances = []
        
        for null_key, approximations in self.sparse_approximations.items():
            for approx in approximations[:5]:  # Top 5 per null key
                all_sparse_keys.append(approx['key'])
                all_null_keys.append(null_key)
                all_distances.append(approx['distance'])
        
        if len(all_sparse_keys) < 10:
            print("Not enough data for manifold analysis")
            return
        
        # Convert to bit representations for analysis
        print(f"\nAnalyzing {len(all_sparse_keys)} sparse keys...")
        
        # Create feature matrix (bit representation)
        max_bits = 256
        feature_matrix = np.zeros((len(all_sparse_keys), max_bits))
        
        for i, key in enumerate(all_sparse_keys):
            bit_string = bin(key)[2:].zfill(max_bits)
            feature_matrix[i] = [int(b) for b in bit_string]
        
        # PCA to find principal components
        pca = PCA(n_components=min(50, len(all_sparse_keys)))
        pca_result = pca.fit_transform(feature_matrix)
        
        # How much variance is explained?
        cumsum = np.cumsum(pca.explained_variance_ratio_)
        n_components_90 = np.argmax(cumsum >= 0.9) + 1
        
        print(f"\nPCA Results:")
        print(f"  Components for 90% variance: {n_components_90}")
        print(f"  Top 10 component variance: {pca.explained_variance_ratio_[:10]}")
        
        # Check if sparse keys cluster by their null key
        if len(np.unique(all_null_keys)) > 3:
            print("\nTesting clustering by null key...")
            
            # Use first 2 PCA components for visualization
            plt.figure(figsize=(10, 8))
            scatter = plt.scatter(pca_result[:, 0], pca_result[:, 1], 
                                c=[np.log(nk + 1) for nk in all_null_keys],
                                cmap='viridis', alpha=0.6)
            plt.colorbar(scatter, label='log(null_key)')
            plt.xlabel('First PC')
            plt.ylabel('Second PC')
            plt.title('Sparse Keys in PCA Space (colored by null key)')
            plt.savefig('sparse_manifold_pca.png')
            plt.close()
            
            print("  Saved visualization to sparse_manifold_pca.png")
        
        # Check for linear relationships
        print("\nChecking for linear relationships...")
        
        # Can we predict null key from sparse key bits?
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import train_test_split
        
        X_train, X_test, y_train, y_test = train_test_split(
            feature_matrix, all_null_keys, test_size=0.2, random_state=42
        )
        
        lr = LinearRegression()
        lr.fit(X_train, np.log(np.array(y_train) + 1))  # Log scale for null keys
        score = lr.score(X_test, np.log(np.array(y_test) + 1))
        
        print(f"  Linear predictability of null key from sparse bits: R² = {score:.3f}")
        
        if score > 0.5:
            print("  WARNING: High predictability suggests exploitable structure!")
        
        # Check for collision patterns
        self.find_collision_candidates()
    
    def find_collision_candidates(self):
        """Look for sparse keys that map to similar hash160s"""
        print("\n" + "="*80)
        print("SEARCHING FOR COLLISION CANDIDATES")
        print("="*80)
        
        # Group by hash160 prefix
        prefix_groups = defaultdict(list)
        
        for null_key, approximations in self.sparse_approximations.items():
            for approx in approximations:
                prefix = approx['hash'][:8]  # 4-byte prefix
                prefix_groups[prefix].append({
                    'null_key': null_key,
                    'sparse_key': approx['key'],
                    'full_hash': approx['hash'],
                    'distance': approx['distance']
                })
        
        # Find prefixes with multiple hits
        collision_prefixes = [(prefix, entries) for prefix, entries in prefix_groups.items() 
                             if len(entries) > 1]
        
        collision_prefixes.sort(key=lambda x: len(x[1]), reverse=True)
        
        print(f"Found {len(collision_prefixes)} prefixes with multiple sparse keys")
        
        if collision_prefixes:
            print("\nTop collision candidates:")
            for prefix, entries in collision_prefixes[:5]:
                print(f"\n  Prefix: {prefix}")
                print(f"  Sparse keys mapping here: {len(entries)}")
                
                # Check if these could be actual collisions
                hashes = [e['full_hash'] for e in entries]
                if len(set(hashes)) < len(hashes):
                    print("  🚨 ACTUAL COLLISION FOUND!")
                    
                # Show diversity of null keys leading here
                null_keys = [e['null_key'] for e in entries]
                print(f"  From null keys: {len(set(null_keys))} different")
    
    def test_interpolation_attack(self):
        """Test if we can interpolate between sparse keys to find new ones"""
        print("\n" + "="*80)
        print("TESTING INTERPOLATION ATTACK")
        print("="*80)
        
        # Pick two null keys with good sparse approximations
        null_keys_with_approx = [(nk, approx) for nk, approx in self.sparse_approximations.items() 
                                if len(approx) > 5]
        
        if len(null_keys_with_approx) < 2:
            print("Not enough data for interpolation test")
            return
        
        # Take first two
        null_key1, approx1 = null_keys_with_approx[0]
        null_key2, approx2 = null_keys_with_approx[1]
        
        print(f"Interpolating between:")
        print(f"  Null key 1: 0x{null_key1:x}")
        print(f"  Null key 2: 0x{null_key2:x}")
        
        # Get best sparse approximations
        sparse1 = approx1[0]['key']
        sparse2 = approx2[0]['key']
        
        # Try various interpolations
        interpolations = []
        
        # Bitwise interpolation
        for alpha in [0.25, 0.5, 0.75]:
            # Weighted XOR
            interpolated = int(sparse1 * (1 - alpha) + sparse2 * alpha) & ((1 << 256) - 1)
            
            if 0 < interpolated < SECP256K1_ORDER:
                hash_interp = self.private_key_to_hash160(interpolated)
                
                # Test against both targets
                dist1 = self.hamming_distance(hash_interp, self.null_surface[null_key1])
                dist2 = self.hamming_distance(hash_interp, self.null_surface[null_key2])
                
                interpolations.append({
                    'alpha': alpha,
                    'key': interpolated,
                    'dist_to_null1': dist1,
                    'dist_to_null2': dist2,
                    'sparsity': bin(interpolated).count('0') / 256
                })
        
        print(f"\nInterpolation results:")
        for interp in interpolations:
            print(f"  α={interp['alpha']}: dist1={interp['dist_to_null1']}, "
                  f"dist2={interp['dist_to_null2']}, sparsity={interp['sparsity']:.1%}")
    
    def test_curve_parameter_sensitivity(self):
        """Test if certain curve parameters make this worse"""
        print("\n" + "="*80)
        print("CURVE PARAMETER SENSITIVITY TEST")
        print("="*80)
        
        # Test with different byte positions having non-zero values
        position_results = defaultdict(list)
        
        print("Testing which byte positions create strongest bias...")
        
        for position in range(32):
            # Create keys with single byte at specific position
            for value in [0x01, 0x7F, 0xFF]:
                key_bytes = bytearray(32)
                key_bytes[position] = value
                key_int = int.from_bytes(key_bytes, 'big')
                
                if key_int < SECP256K1_ORDER:
                    hash160 = self.private_key_to_hash160(key_int)
                    
                    # Measure entropy of hash
                    hash_entropy = sum(bin(b).count('1') for b in hash160) / (20 * 8)
                    position_results[position].append(hash_entropy)
        
        # Find positions with most consistent bias
        position_bias = {}
        for pos, entropies in position_results.items():
            if entropies:
                mean_entropy = np.mean(entropies)
                std_entropy = np.std(entropies)
                position_bias[pos] = (mean_entropy, std_entropy)
        
        # Sort by deviation from 0.5 (maximum entropy)
        sorted_positions = sorted(position_bias.items(), 
                                key=lambda x: abs(x[1][0] - 0.5), 
                                reverse=True)
        
        print("\nMost biased byte positions:")
        for pos, (mean_ent, std_ent) in sorted_positions[:10]:
            bias = abs(mean_ent - 0.5)
            print(f"  Position {pos}: mean_entropy={mean_ent:.3f}, bias={bias:.3f}")
        
        # Check if early bytes (used in scalar multiplication) show more bias
        early_bias = np.mean([abs(position_bias[i][0] - 0.5) for i in range(8) if i in position_bias])
        late_bias = np.mean([abs(position_bias[i][0] - 0.5) for i in range(24, 32) if i in position_bias])
        
        print(f"\nEarly bytes (0-7) average bias: {early_bias:.3f}")
        print(f"Late bytes (24-31) average bias: {late_bias:.3f}")
        
        if early_bias > late_bias * 1.5:
            print("⚠️  Early bytes show significantly more bias - scalar multiplication leak!")
    
    def save_results(self):
        """Save all findings to file"""
        results = {
            'null_surface': {str(k): v.hex() for k, v in self.null_surface.items()},
            'approximation_summary': {},
            'collision_candidates': [],
            'timestamp': time.time()
        }
        
        # Summarize approximations
        for null_key, approx_list in self.sparse_approximations.items():
            if approx_list:
                results['approximation_summary'][str(null_key)] = {
                    'best_distance': approx_list[0]['distance'],
                    'num_found': len(approx_list),
                    'best_pattern': approx_list[0]['pattern_type']
                }
        
        with open('ecc_backdoor_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\nResults saved to ecc_backdoor_analysis.json")
    
    def run_full_analysis(self):
        """Run complete backdoor analysis"""
        print("🔍 ECC SPARSE SURFACE BACKDOOR ANALYSIS")
        print("="*80)
        print("Testing if sparse patterns reveal exploitable ECC structure...")
        print("="*80)
        
        # Step 1: Map null surface
        self.map_null_surface()
        
        # Step 2: Analyze manifold structure
        self.analyze_sparse_manifold()
        
        # Step 3: Test interpolation
        self.test_interpolation_attack()
        
        # Step 4: Test curve sensitivity
        self.test_curve_parameter_sensitivity()
        
        # Step 5: Save results
        self.save_results()
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        
        # Summary
        total_nulls = len(self.null_surface)
        total_approx = sum(len(v) for v in self.sparse_approximations.values())
        
        print(f"\nSummary:")
        print(f"  Null keys tested: {total_nulls}")
        print(f"  Sparse approximations found: {total_approx}")
        print(f"  Average distance achieved: {np.mean([a['distance'] for v in self.sparse_approximations.values() for a in v]):.1f} bits")
        
        # Check for smoking guns
        if any(len(v) > 10 for v in self.sparse_approximations.values()):
            print("\n🚨 WARNING: Some null keys have many sparse approximations!")
            print("   This suggests exploitable clustering in hash space.")
        
        if total_approx > total_nulls * 5:
            print("\n🚨 WARNING: Sparse keys cluster heavily around null keys!")
            print("   This could indicate a backdoor or fundamental weakness.")
        
        print("\nNext steps:")
        print("1. Test on real Bitcoin addresses known to use small private keys")
        print("2. Expand search to more null patterns")
        print("3. Train ML model on the sparse manifold")
        print("4. Test if this extends to other curves (P-256, etc.)")


if __name__ == "__main__":
    explorer = ECCBackdoorExplorer()
    explorer.run_full_analysis()
#!/usr/bin/env python3
"""
Improved Bullseye Finder - Uses consensus and XOR patterns
"""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse
import time
import random
from typing import List, Tuple, Optional, Dict
from scipy.spatial import distance_matrix
from scipy.stats import mode
import hashlib
from ecdsa import SECP256k1, SigningKey
from Crypto.Hash import RIPEMD160

class CryptoOps:
    """Crypto operations for secp256k1"""
    def __init__(self):
        self.curve = SECP256k1
        self.key_size = 32
        self.n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        
    def private_key_to_hash160(self, private_key: bytes) -> bytes:
        """Convert private key to hash160"""
        try:
            sk = SigningKey.from_string(private_key, curve=self.curve)
            vk = sk.verifying_key
            pubkey = vk.to_string("compressed")
            
            sha256_hash = hashlib.sha256(pubkey).digest()
            h = RIPEMD160.new()
            h.update(sha256_hash)
            return h.digest()
        except:
            return b'\x00' * 20

def hamming_distance(h1: bytes, h2: bytes) -> int:
    """Calculate Hamming distance between two hashes"""
    distance = 0
    for i in range(min(len(h1), len(h2))):
        xor_byte = h1[i] ^ h2[i]
        distance += bin(xor_byte).count('1')
    return distance

class ImprovedBullseyeFinder:
    """Improved bullseye finder with consensus and XOR patterns"""
    
    def __init__(self):
        self.crypto = CryptoOps()
        self.xor_pattern = bytes([0x55] * 32)
        self.center_history = []
        self.pattern_stable = False
        self.consensus_threshold = 0.7
        
    def apply_xor_transform(self, keys: List[bytes]) -> List[bytes]:
        """Apply XOR 0x5555... transform to keys"""
        return [bytes(a ^ b for a, b in zip(key, self.xor_pattern)) for key in keys]
    
    def find_consensus_center(self, elite_keys: List[bytes]) -> Dict:
        """Find center using multiple methods and check for consensus"""
        results = {
            'centers': [],
            'methods': [],
            'consensus': False,
            'best_center': None,
            'confidence': 0.0
        }
        
        # Method 1: Original keys PCA
        centers = []
        key_matrix = np.array([[int(b) for b in key] for key in elite_keys])
        
        pca1 = PCA(n_components=2)
        coords1 = pca1.fit_transform(key_matrix)
        center1 = np.mean(coords1, axis=0)
        centers.append(('original_mean', center1, pca1))
        
        # Method 2: XOR transformed keys PCA
        xor_keys = self.apply_xor_transform(elite_keys)
        xor_matrix = np.array([[int(b) for b in key] for key in xor_keys])
        
        pca2 = PCA(n_components=2)
        coords2 = pca2.fit_transform(xor_matrix)
        center2 = np.mean(coords2, axis=0)
        centers.append(('xor_mean', center2, pca2))
        
        # Method 3: K-means clustering on original
        if len(coords1) >= 3:
            kmeans1 = KMeans(n_clusters=min(3, len(coords1) // 10), random_state=42)
            kmeans1.fit(coords1)
            # Find the cluster with most points
            labels, counts = np.unique(kmeans1.labels_, return_counts=True)
            main_cluster = labels[np.argmax(counts)]
            main_points = coords1[kmeans1.labels_ == main_cluster]
            center3 = np.mean(main_points, axis=0)
            centers.append(('kmeans_original', center3, pca1))
        
        # Method 4: Look for actual circular pattern
        if len(coords1) >= 10:
            # Calculate pairwise distances from centroid
            centroid = np.mean(coords1, axis=0)
            distances = np.linalg.norm(coords1 - centroid, axis=1)
            
            # Check if distances are similar (circular pattern)
            cv = np.std(distances) / (np.mean(distances) + 1e-8)
            if cv < 0.5:  # Low variance = circular
                # Use the centroid
                centers.append(('circular_pattern', centroid, pca1))
        
        # Method 5: Elite subset consensus
        if len(elite_keys) >= 20:
            subset_centers = []
            for _ in range(5):
                subset = random.sample(elite_keys, 15)
                subset_matrix = np.array([[int(b) for b in key] for key in subset])
                pca_sub = PCA(n_components=2)
                coords_sub = pca_sub.fit_transform(subset_matrix)
                subset_centers.append(np.mean(coords_sub, axis=0))
            
            # Check if subset centers agree
            if subset_centers:
                subset_distances = distance_matrix(subset_centers, subset_centers)
                avg_dist = np.mean(subset_distances[np.triu_indices_from(subset_distances, k=1)])
                if avg_dist < 10:  # Close agreement
                    consensus_center = np.mean(subset_centers, axis=0)
                    centers.append(('subset_consensus', consensus_center, pca1))
        
        # Analyze consensus
        if len(centers) >= 2:
            # Get all 2D centers in the same PCA space
            standardized_centers = []
            for method, center, pca in centers:
                if pca == pca1:
                    standardized_centers.append(center)
                else:
                    # Project to pca1 space (approximate)
                    standardized_centers.append(center)  # Simplified for now
            
            # Check how close they are
            if len(standardized_centers) >= 2:
                center_distances = distance_matrix(standardized_centers, standardized_centers)
                max_dist = np.max(center_distances)
                
                if max_dist < 20:  # Good consensus
                    results['consensus'] = True
                    results['best_center'] = np.mean(standardized_centers, axis=0)
                    results['confidence'] = 1.0 - (max_dist / 100.0)
                else:
                    # Use the most common center
                    results['best_center'] = standardized_centers[0]
                    results['confidence'] = 0.3
        
        results['centers'] = centers
        return results
    
    def generate_smart_candidates(self, elite_keys: List[bytes], 
                                consensus_info: Dict) -> List[bytes]:
        """Generate candidates using consensus information and patterns"""
        candidates = []
        
        if not consensus_info['best_center']:
            return candidates
        
        # Use the PCA from original keys
        key_matrix = np.array([[int(b) for b in key] for key in elite_keys])
        pca = PCA(n_components=2)
        coords = pca.fit_transform(key_matrix)
        
        center_2d = consensus_info['best_center']
        
        # Strategy 1: Small keys with XOR
        # Your GA found small keys work well
        for _ in range(20):
            # Generate small key
            small_key = random.randint(1, 2**80).to_bytes(32, 'big')
            candidates.append(small_key)
            
            # Also try XOR version
            xor_small = bytes(a ^ b for a, b in zip(small_key, self.xor_pattern))
            candidates.append(xor_small)
        
        # Strategy 2: Project center back to key space
        # More sophisticated inverse projection
        components = pca.components_
        mean = pca.mean_
        
        # Multiple attempts with noise
        for _ in range(10):
            # Add noise to center
            noisy_center = center_2d + np.random.normal(0, 5, 2)
            
            # Project back (approximate)
            key_estimate = noisy_center @ components + mean
            key_bytes = np.clip(key_estimate[:32], 0, 255).astype(np.uint8)
            
            candidates.append(bytes(key_bytes))
            
            # XOR version
            xor_version = bytes(a ^ b for a, b in zip(bytes(key_bytes), self.xor_pattern))
            candidates.append(xor_version)
        
        # Strategy 3: Interpolate between elites toward center
        for i in range(min(5, len(elite_keys))):
            elite = elite_keys[i]
            elite_array = np.array([int(b) for b in elite])
            elite_2d = coords[i]
            
            # Direction to center
            direction = center_2d - elite_2d
            
            # Move toward center in original space (rough approximation)
            for alpha in [0.3, 0.5, 0.7, 1.0, 1.2]:
                # This is approximate - we're moving in high-D space
                # based on 2D direction
                noise_direction = np.random.randn(32)
                noise_direction = noise_direction / (np.linalg.norm(noise_direction) + 1e-8)
                
                moved = elite_array + alpha * np.linalg.norm(direction) * noise_direction * 10
                moved_bytes = np.clip(moved, 0, 255).astype(np.uint8)
                
                candidates.append(bytes(moved_bytes))
        
        # Strategy 4: Use bit patterns from best elites
        if len(elite_keys) >= 10:
            # Find common bit patterns
            elite_bits = []
            for key in elite_keys[:10]:
                key_int = int.from_bytes(key, 'big')
                elite_bits.append(format(key_int, '0256b'))
            
            # Vote on each bit position
            consensus_bits = []
            for bit_pos in range(256):
                bits_at_pos = [eb[bit_pos] for eb in elite_bits]
                most_common = max(set(bits_at_pos), key=bits_at_pos.count)
                consensus_bits.append(most_common)
            
            # Create key from consensus bits
            consensus_int = int(''.join(consensus_bits), 2)
            consensus_key = consensus_int.to_bytes(32, 'big')
            candidates.append(consensus_key)
            
            # Add variations
            for _ in range(5):
                # Flip a few random bits
                varied = consensus_int
                for _ in range(random.randint(5, 20)):
                    bit_pos = random.randint(0, 255)
                    varied ^= (1 << bit_pos)
                candidates.append(varied.to_bytes(32, 'big'))
        
        return candidates
    
    def check_pattern_stability(self) -> bool:
        """Check if the pattern is stable across rounds"""
        if len(self.center_history) < 3:
            return False
        
        # Look at last 3 centers
        recent_centers = self.center_history[-3:]
        
        # Calculate distances between consecutive centers
        distances = []
        for i in range(len(recent_centers) - 1):
            dist = np.linalg.norm(recent_centers[i] - recent_centers[i+1])
            distances.append(dist)
        
        # Stable if centers aren't moving much
        avg_movement = np.mean(distances)
        return avg_movement < 5.0
    
    def visualize_consensus(self, elite_keys: List[bytes], 
                          consensus_info: Dict,
                          candidates: List[bytes],
                          true_key: Optional[bytes] = None,
                          save_path: str = "consensus_bullseye.png"):
        """Visualize the consensus approach"""
        
        key_matrix = np.array([[int(b) for b in key] for key in elite_keys])
        pca = PCA(n_components=2)
        elite_coords = pca.fit_transform(key_matrix)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # Left plot: Original space
        ax1.scatter(elite_coords[:, 0], elite_coords[:, 1], 
                   c='blue', alpha=0.6, s=50, label='Elites')
        
        # Plot different centers
        colors = ['red', 'green', 'orange', 'purple', 'brown']
        for i, (method, center, _) in enumerate(consensus_info['centers'][:5]):
            ax1.scatter(center[0], center[1], c=colors[i % len(colors)], 
                       marker='x', s=200, label=method)
        
        # Best center
        if consensus_info['best_center'] is not None:
            best = consensus_info['best_center']
            ax1.scatter(best[0], best[1], c='red', marker='+', 
                       s=500, linewidth=3, label='Consensus center')
        
        # Candidates
        if candidates:
            cand_matrix = np.array([[int(b) for b in key] for key in candidates[:30]])
            cand_coords = pca.transform(cand_matrix)
            ax1.scatter(cand_coords[:, 0], cand_coords[:, 1], 
                       c='green', marker='^', s=80, alpha=0.7, label='Candidates')
        
        # True key if known
        if true_key:
            true_matrix = np.array([[int(b) for b in true_key]])
            true_coords = pca.transform(true_matrix)[0]
            ax1.scatter(true_coords[0], true_coords[1], c='red', marker='*', 
                       s=500, edgecolor='black', linewidth=2, label='TRUE KEY')
        
        ax1.set_xlabel('PC1')
        ax1.set_ylabel('PC2')
        ax1.set_title(f'Original Keys (Consensus: {consensus_info["consensus"]})')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Right plot: XOR transformed space
        xor_keys = self.apply_xor_transform(elite_keys)
        xor_matrix = np.array([[int(b) for b in key] for key in xor_keys])
        pca2 = PCA(n_components=2)
        xor_coords = pca2.fit_transform(xor_matrix)
        
        ax2.scatter(xor_coords[:, 0], xor_coords[:, 1], 
                   c='purple', alpha=0.6, s=50, label='XOR Elites')
        
        # XOR center
        xor_center = np.mean(xor_coords, axis=0)
        ax2.scatter(xor_center[0], xor_center[1], c='red', marker='+', 
                   s=500, linewidth=3, label='XOR Center')
        
        # True key XOR if known
        if true_key:
            true_xor = bytes(a ^ b for a, b in zip(true_key, self.xor_pattern))
            true_xor_matrix = np.array([[int(b) for b in true_xor]])
            true_xor_coords = pca2.transform(true_xor_matrix)[0]
            ax2.scatter(true_xor_coords[0], true_xor_coords[1], c='red', marker='*', 
                       s=500, edgecolor='black', linewidth=2, label='TRUE XOR')
        
        ax2.set_xlabel('PC1')
        ax2.set_ylabel('PC2')
        ax2.set_title('XOR Transformed Keys')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()

class ImprovedBullseyeGA:
    """GA with improved bullseye targeting"""
    
    def __init__(self, target_hash: bytes):
        self.target_hash = target_hash
        self.crypto = CryptoOps()
        self.finder = ImprovedBullseyeFinder()
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.best_key = None
        self.best_score = 160
        self.xor_pattern = bytes([0x55] * 32)
        
    def initialize_population(self, size: int = 8000):
        """Initialize with mix of strategies"""
        # 60% small keys (your GA discovery)
        for _ in range(int(size * 0.6)):
            key = random.randint(1, 2**80).to_bytes(32, 'big')
            self.population.append(key)
            score = self.score_key(key)
            self.scores.append(score)
        
        # 20% XOR variants of small keys
        for _ in range(int(size * 0.2)):
            small_key = random.randint(1, 2**80).to_bytes(32, 'big')
            xor_key = bytes(a ^ b for a, b in zip(small_key, self.xor_pattern))
            self.population.append(xor_key)
            score = self.score_key(xor_key)
            self.scores.append(score)
        
        # 20% random full range
        for _ in range(int(size * 0.2)):
            key = random.randint(1, self.crypto.n - 1).to_bytes(32, 'big')
            self.population.append(key)
            score = self.score_key(key)
            self.scores.append(score)
    
    def score_key(self, key: bytes) -> int:
        """Score a key against target"""
        hash160 = self.crypto.private_key_to_hash160(key)
        score = hamming_distance(hash160, self.target_hash)
        
        if score < self.best_score:
            self.best_score = score
            self.best_key = key
        
        return score
    
    def update_elites(self, elite_size: int = 400):
        """Update elite pool"""
        scored = list(zip(self.scores, self.population))
        scored.sort(key=lambda x: x[0])
        self.elite_keys = [key for score, key in scored[:elite_size]]
    
    def smart_bullseye_injection(self, round_num: int):
        """Inject candidates only when pattern is stable"""
        if len(self.elite_keys) < 50:
            return
        
        print(f"\n🎯 Round {round_num}: Analyzing pattern consensus...")
        
        # Get consensus info
        consensus_info = self.finder.find_consensus_center(self.elite_keys[:100])
        
        print(f"   Consensus: {consensus_info['consensus']}")
        print(f"   Confidence: {consensus_info['confidence']:.1%}")
        
        # Only inject if we have consensus or after enough rounds
        if consensus_info['consensus'] or round_num > 15:
            candidates = self.finder.generate_smart_candidates(
                self.elite_keys[:100], 
                consensus_info
            )
            
            # Score candidates
            candidate_scores = []
            for candidate in candidates:
                score = self.score_key(candidate)
                candidate_scores.append((score, candidate))
            
            # Sort by score
            candidate_scores.sort(key=lambda x: x[0])
            
            # Only inject if we found good candidates
            if candidate_scores and candidate_scores[0][0] < self.best_score + 10:
                num_inject = min(len(candidates), int(0.1 * len(self.population)))
                print(f"   💉 Injecting {num_inject} consensus candidates")
                
                # Replace worst
                worst_indices = sorted(range(len(self.scores)), 
                                     key=lambda i: self.scores[i], 
                                     reverse=True)[:num_inject]
                
                for i, (score, candidate) in enumerate(candidate_scores[:num_inject]):
                    idx = worst_indices[i]
                    self.population[idx] = candidate
                    self.scores[idx] = score
                
                print(f"   🎯 Best consensus candidate: {candidate_scores[0][0]} bits")
        else:
            print(f"   ⏳ Waiting for pattern stability...")
        
        # Update center history if we have a center
        if consensus_info['best_center'] is not None:
            self.finder.center_history.append(consensus_info['best_center'])
    
    def run(self, max_rounds: int = 30):
        """Run improved bullseye GA"""
        print(f"🎯 Starting Improved Bullseye GA")
        print(f"   Target: {self.target_hash.hex()}")
        
        self.initialize_population()
        self.update_elites()
        
        print(f"   Initial best: {self.best_score} bits")
        
        for round_num in range(max_rounds):
            # Evolution with XOR awareness
            new_population = []
            new_scores = []
            
            for i in range(len(self.population)):
                key = self.population[i]
                
                # Multiple mutation strategies
                if random.random() < 0.3:
                    # XOR mutation
                    key = bytes(a ^ b for a, b in zip(key, self.xor_pattern))
                elif random.random() < 0.5:
                    # Small change
                    key_int = int.from_bytes(key, 'big')
                    key_int = (key_int + random.randint(-1000, 1000)) % self.crypto.n
                    key = key_int.to_bytes(32, 'big')
                else:
                    # Bit flip
                    key_int = int.from_bytes(key, 'big')
                    bit_pos = random.randint(0, 255)
                    key_int ^= (1 << bit_pos)
                    key = key_int.to_bytes(32, 'big')
                
                score = self.score_key(key)
                new_population.append(key)
                new_scores.append(score)
            
            self.population = new_population
            self.scores = new_scores
            self.update_elites()
            
            # Smart injection with consensus
            if round_num % 3 == 0 and round_num > 0:
                self.smart_bullseye_injection(round_num)
                
                # Visualize occasionally
                if round_num % 6 == 0:
                    consensus_info = self.finder.find_consensus_center(self.elite_keys[:100])
                    candidates = self.finder.generate_smart_candidates(
                        self.elite_keys[:100], 
                        consensus_info
                    )
                    
                    try:
                        self.finder.visualize_consensus(
                            self.elite_keys[:100],
                            consensus_info,
                            candidates[:30],
                            save_path=f"consensus_round_{round_num}.png"
                        )
                    except:
                        pass
            
            # Progress
            if round_num % 5 == 0:
                stable = self.finder.check_pattern_stability()
                print(f"   Round {round_num}: Best = {self.best_score} bits, Pattern stable: {stable}")
            
            # Early termination
            if self.best_score < 30:
                print(f"   ✅ Reached < 30 bits at round {round_num}")
                break
        
        return {
            'best_key': self.best_key,
            'best_score': self.best_score,
            'rounds': round_num + 1,
            'pattern_stable': self.finder.check_pattern_stability()
        }

# Run test
if __name__ == "__main__":
    print("🧪 Testing Improved Bullseye with Consensus...")
    
    crypto = CryptoOps()
    true_key = random.randint(1, crypto.n - 1).to_bytes(32, 'big')
    target_hash = crypto.private_key_to_hash160(true_key)
    
    ga = ImprovedBullseyeGA(target_hash)
    results = ga.run(max_rounds=25)
    
    print(f"\n📊 Final Results:")
    print(f"   Best score: {results['best_score']} bits")
    print(f"   Pattern stable: {results['pattern_stable']}")
    
    # Final visualization with true key
    if results['best_key']:
        consensus_info = ga.finder.find_consensus_center(ga.elite_keys[:100])
        candidates = ga.finder.generate_smart_candidates(ga.elite_keys[:100], consensus_info)
        
        ga.finder.visualize_consensus(
            ga.elite_keys[:100],
            consensus_info,
            candidates[:30],
            true_key=true_key,
            save_path="final_consensus_with_true.png"
        )
        
        # Check true key position
        key_matrix = np.array([[int(b) for b in key] for key in ga.elite_keys[:100]])
        pca = PCA(n_components=2)
        pca.fit(key_matrix)
        
        true_coords = pca.transform(np.array([[int(b) for b in true_key]]))[0]
        if consensus_info['best_center'] is not None:
            dist = np.linalg.norm(true_coords - consensus_info['best_center'])
            print(f"\n🎯 True key distance from consensus center: {dist:.3f}")
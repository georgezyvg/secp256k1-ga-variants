#!/usr/bin/env python3
"""
Neural-Enhanced Bitcoin Search with Transformer Pattern Learning
Integrates a self-learning neural network that discovers hash transformation patterns
Specifically configured for Bitcoin puzzles using UNCOMPRESSED public keys

Performance optimizations:
- coincurve (libsecp256k1) for ~10x faster EC operations vs python-ecdsa
- Uses ALL available CPU cores for maximum parallelization
- Intelligent caching system with hit rate tracking
"""

import time
import random
import math
import hashlib
import struct
import logging
import pickle
import os
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import deque
import copy
import multiprocessing as mp

# SECP256k1 curve order (n)
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

try:
    import numpy as np
    from coincurve import PrivateKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os
    from sklearn.decomposition import PCA
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    CRYPTO_AVAILABLE = True
except ImportError:
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "coincurve", "pycryptodome", "scikit-learn", "torch"])
    
    import numpy as np
    from coincurve import PrivateKey
    from Crypto.Hash import RIPEMD160
    import multiprocessing as mp
    from multiprocessing import Value, Array
    from queue import SimpleQueue, Empty
    import os
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    CRYPTO_AVAILABLE = True

# SECP256k1 curve order (n)
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

@dataclass
class NeuralBitcoinConfig:
    """Enhanced configuration with neural parameters"""
    # Original GA parameters - 20% reduction
    POPULATION_SIZE: int = 8000  # Was 10000
    ELITE_SIZE: int = 400  # Was 500
    ELITE_PERCENT: float = 0.05
    
    # HIGH PRESSURE parameters
    POPULATION_PRESSURE_RATE: float = 0.8
    ELITE_CROSSOVER_RATE: float = 0.9
    SELECTION_PRESSURE: float = 0.7
    CONVERGENCE_ACCELERATION: float = 2.0
    
    # Genetic diversity parameters
    MIN_GENETIC_DIVERSITY: float = 8.0
    DIVERSITY_THRESHOLD: float = 12.0
    
    # Optimization parameters
    MUTATION_STRENGTH: float = 0.5
    MUTATION_DECAY: float = 0.98
    MUTATION_INCREASE: float = 3.0
    MUTATION_MIN: float = 0.15
    MUTATION_MAX: float = 0.95
    
    # Stagnation and adaptation
    STAGNATION_ROUNDS: int = 1
    ELITE_STAGNATION_ROUNDS: int = 2
    DIVERSITY_INJECTION_RATE: float = 0.8
    
    # Learning parameters
    GENETIC_LEARNING_SCALE: float = 15.0
    ADAPTATION_RATE: float = 0.15
    PATTERN_SENSITIVITY: float = 0.3
    
    # Population pressure specific
    ELITE_BREEDING_ROUNDS: int = 3
    POPULATION_REPLACEMENT_FREQ: int = 2
    PRESSURE_ESCALATION_RATE: float = 1.2
    
    # Neural network parameters - 20% reduction
    NEURAL_HIDDEN_DIM: int = 768  # Was 1024 (768/12=64)
    NEURAL_LAYERS: int = 5  # Was 6
    NEURAL_HEADS: int = 12  # Was 16
    NEURAL_LEARNING_RATE: float = 0.001
    NEURAL_MEMORY_SIZE: int = 8000  # Was 10000
    NEURAL_BATCH_SIZE: int = 24  # Was 32
    
    # Work management
    WORK_QUEUE_SIZE: int = 2000


class TransformerHashPatternLearner(nn.Module):
    """
    Neural network that learns the black-box transformation from private key to hash160
    Discovers patterns without being told about the 44-bit barrier
    """
    def __init__(self, config: NeuralBitcoinConfig):
        super().__init__()
        self.config = config
        
        # Input: 256 bits (private key) + 256 bit weights + score features
        self.input_dim = 256 + 256 + 160
        
        # Bit embedding layer
        self.bit_embedder = nn.Sequential(
            nn.Linear(self.input_dim, config.NEURAL_HIDDEN_DIM),
            nn.LayerNorm(config.NEURAL_HIDDEN_DIM),
            nn.GELU()
        )
        
        # Position encoding for bit positions
        self.position_encoding = nn.Parameter(torch.randn(1, 256, config.NEURAL_HIDDEN_DIM))
        
        # Transformer encoder - learns relationships between bit positions
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.NEURAL_HIDDEN_DIM,
            nhead=config.NEURAL_HEADS,
            dim_feedforward=config.NEURAL_HIDDEN_DIM * 4,
            dropout=0.1,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.NEURAL_LAYERS)
        
        # Hash function approximator - learns the black box transformation
        self.hash_approximator = nn.Sequential(
            nn.Linear(config.NEURAL_HIDDEN_DIM, config.NEURAL_HIDDEN_DIM * 2),
            nn.LayerNorm(config.NEURAL_HIDDEN_DIM * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(config.NEURAL_HIDDEN_DIM * 2, config.NEURAL_HIDDEN_DIM),
            nn.LayerNorm(config.NEURAL_HIDDEN_DIM),
            nn.GELU(),
            nn.Linear(config.NEURAL_HIDDEN_DIM, 160)  # Output: predicted hash160 bits
        )
        
        # Mutation strategy predictor
        self.mutation_predictor = nn.Sequential(
            nn.Linear(config.NEURAL_HIDDEN_DIM, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.Sigmoid()  # Per-bit mutation probabilities
        )
        
        # Hex position importance predictor
        self.hex_importance = nn.Sequential(
            nn.Linear(config.NEURAL_HIDDEN_DIM, 256),
            nn.ReLU(),
            nn.Linear(256, 64),  # 64 hex positions
            nn.Softmax(dim=-1)
        )
        
        # Pattern memory - stores successful transformations
        self.register_buffer('pattern_memory_keys', torch.zeros(config.NEURAL_MEMORY_SIZE, 256))
        self.register_buffer('pattern_memory_hashes', torch.zeros(config.NEURAL_MEMORY_SIZE, 160))
        self.register_buffer('pattern_memory_scores', torch.ones(config.NEURAL_MEMORY_SIZE) * 160)
        self.memory_ptr = 0
        
        # Success predictor - estimates improvement probability
        self.success_predictor = nn.Sequential(
            nn.Linear(config.NEURAL_HIDDEN_DIM + 256, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
        
        # Barrier detector - learns to identify optimization barriers
        self.barrier_detector = nn.Sequential(
            nn.Linear(config.NEURAL_HIDDEN_DIM, 256),
            nn.ReLU(),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        # Bit correlation matrix learner
        self.correlation_learner = nn.Linear(config.NEURAL_HIDDEN_DIM, 256 * 256)
        
        # Initialize optimizer
        self.optimizer = torch.optim.AdamW(self.parameters(), lr=config.NEURAL_LEARNING_RATE)
        
    def forward(self, private_key_bits, bit_weights, current_score):
        """Forward pass through the network"""
        # Handle inputs - ensure proper tensor format
        if isinstance(private_key_bits, np.ndarray):
            private_key_bits = torch.tensor(private_key_bits, dtype=torch.float32)
        if isinstance(bit_weights, np.ndarray):
            bit_weights = torch.tensor(bit_weights, dtype=torch.float32)
        
        # Ensure batch dimension
        if private_key_bits.dim() == 1:
            private_key_bits = private_key_bits.unsqueeze(0)
        if bit_weights.dim() == 1:
            bit_weights = bit_weights.unsqueeze(0)
        
        batch_size = private_key_bits.shape[0]
        
        # Ensure correct dimensions
        if private_key_bits.shape[1] != 256:
            # Pad or truncate to 256
            if private_key_bits.shape[1] < 256:
                padding = torch.zeros(batch_size, 256 - private_key_bits.shape[1])
                private_key_bits = torch.cat([private_key_bits, padding], dim=1)
            else:
                private_key_bits = private_key_bits[:, :256]
        
        if bit_weights.shape[1] != 256:
            # Pad or truncate to 256
            if bit_weights.shape[1] < 256:
                padding = torch.zeros(batch_size, 256 - bit_weights.shape[1])
                bit_weights = torch.cat([bit_weights, padding], dim=1)
            else:
                bit_weights = bit_weights[:, :256]
        
        # Create score features
        score_features = torch.zeros(batch_size, 160)
        if isinstance(current_score, (int, float)):
            score_idx = min(int(current_score), 159)
            score_features[0, score_idx] = 1.0
        elif hasattr(current_score, '__iter__'):
            for i, score in enumerate(current_score):
                if i < batch_size:
                    score_idx = min(int(score), 159)
                    score_features[i, score_idx] = 1.0
        
        # Combine inputs
        combined_input = torch.cat([private_key_bits, bit_weights, score_features], dim=-1)
        
        # Embed and reshape for transformer
        embedded = self.bit_embedder(combined_input)  # [batch, hidden_dim]
        
        # Reshape to sequence format [batch, seq_len, hidden_dim]
        seq_embedded = embedded.unsqueeze(1).expand(-1, 256, -1)
        
        # Add position encoding
        pos_enc = self.position_encoding[:, :256, :].expand(batch_size, -1, -1)
        seq_embedded = seq_embedded + pos_enc
        
        # Transformer encoding
        transformed = self.transformer(seq_embedded)  # [batch, 256, hidden_dim]
        
        # Global representation
        global_repr = transformed.mean(dim=1)  # [batch, hidden_dim]
        
        # Predict hash approximation
        hash_prediction = self.hash_approximator(global_repr)
        
        # Predict mutation strategies
        mutation_probs = self.mutation_predictor(global_repr)
        
        # Predict hex importance
        hex_importance = self.hex_importance(global_repr)
        
        # Predict success probability
        success_features = torch.cat([global_repr, private_key_bits], dim=-1)
        success_prob = self.success_predictor(success_features)
        
        # Detect barriers
        barrier_prob = self.barrier_detector(global_repr)
        
        # Learn bit correlations
        correlation_flat = self.correlation_learner(global_repr)
        correlation_matrix = correlation_flat.view(batch_size, 256, 256)
        correlation_matrix = (correlation_matrix + correlation_matrix.transpose(-1, -2)) / 2  # Symmetrize
        
        return {
            'hash_prediction': hash_prediction,
            'mutation_probs': mutation_probs,
            'hex_importance': hex_importance,
            'success_prob': success_prob,
            'barrier_prob': barrier_prob,
            'correlation_matrix': correlation_matrix,
            'global_representation': global_repr
        }
    
    def store_pattern(self, private_key_bits, hash160_bits, score):
        """Store successful patterns in memory"""
        # Ensure tensor format
        if isinstance(private_key_bits, np.ndarray):
            private_key_bits = torch.tensor(private_key_bits, dtype=torch.float32)
        if isinstance(hash160_bits, np.ndarray):
            hash160_bits = torch.tensor(hash160_bits, dtype=torch.float32)
        
        # Ensure correct dimensions
        if private_key_bits.dim() > 1:
            private_key_bits = private_key_bits.flatten()
        if hash160_bits.dim() > 1:
            hash160_bits = hash160_bits.flatten()
        
        # Pad or truncate to correct size
        if len(private_key_bits) != 256:
            if len(private_key_bits) < 256:
                padding = torch.zeros(256 - len(private_key_bits))
                private_key_bits = torch.cat([private_key_bits, padding])
            else:
                private_key_bits = private_key_bits[:256]
        
        if len(hash160_bits) != 160:
            if len(hash160_bits) < 160:
                padding = torch.zeros(160 - len(hash160_bits))
                hash160_bits = torch.cat([hash160_bits, padding])
            else:
                hash160_bits = hash160_bits[:160]
        
        idx = self.memory_ptr % self.config.NEURAL_MEMORY_SIZE
        self.pattern_memory_keys[idx] = private_key_bits
        self.pattern_memory_hashes[idx] = hash160_bits
        self.pattern_memory_scores[idx] = score
        self.memory_ptr += 1
    
    def learn_from_batch(self, batch_data):
        """Learn from a batch of (key, hash, score) tuples"""
        if not batch_data:
            return
        
        try:
            self.train()
            
            # Prepare batch with proper error handling
            keys = []
            hashes = []
            scores = []
            weights_list = []
            
            for data in batch_data:
                try:
                    # Handle different data formats
                    key_bits = data.get('key_bits', data.get('key', None))
                    hash_bits = data.get('hash_bits', data.get('hash', None))
                    score = data.get('score', 160)
                    weights = data.get('weights', np.ones(256) * 0.5)
                    
                    if key_bits is None or hash_bits is None:
                        continue
                    
                    # Convert to numpy if needed - NO INPLACE MODIFICATIONS
                    if isinstance(key_bits, bytes):
                        key_bits = np.unpackbits(np.frombuffer(key_bits, dtype=np.uint8)).copy()
                    else:
                        key_bits = np.array(key_bits).copy()
                        
                    if isinstance(hash_bits, bytes):
                        hash_bits = np.unpackbits(np.frombuffer(hash_bits, dtype=np.uint8))[:160].copy()
                    else:
                        hash_bits = np.array(hash_bits[:160]).copy()
                    
                    # Ensure correct size - CREATE NEW ARRAYS
                    if len(key_bits) != 256:
                        new_key_bits = np.zeros(256)
                        new_key_bits[:min(len(key_bits), 256)] = key_bits[:256]
                        key_bits = new_key_bits
                    
                    if len(hash_bits) != 160:
                        new_hash_bits = np.zeros(160)
                        new_hash_bits[:min(len(hash_bits), 160)] = hash_bits[:160]
                        hash_bits = new_hash_bits
                    
                    if len(weights) != 256:
                        weights = np.ones(256) * 0.5
                    
                    keys.append(key_bits)
                    hashes.append(hash_bits)
                    scores.append(score)
                    weights_list.append(weights)
                    
                except Exception as e:
                    continue  # Skip problematic samples
            
            if not keys:
                return
            
            # Convert to tensors - DETACH FROM COMPUTATION GRAPH
            keys_tensor = torch.tensor(np.array(keys), dtype=torch.float32).detach()
            hashes_tensor = torch.tensor(np.array(hashes), dtype=torch.float32).detach()
            scores_tensor = torch.tensor(scores, dtype=torch.float32).detach()
            weights_tensor = torch.tensor(np.array(weights_list), dtype=torch.float32).detach()
            
            # Clear any existing gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            outputs = self.forward(keys_tensor, weights_tensor, scores_tensor)
            
            # Ensure outputs don't share memory
            hash_pred = outputs['hash_prediction'].clone()
            success_prob = outputs['success_prob'].clone()
            barrier_prob = outputs['barrier_prob'].clone()
            
            # Loss calculations
            hash_loss = F.binary_cross_entropy_with_logits(hash_pred, hashes_tensor)
            
            # Success prediction
            improvements = torch.zeros(len(keys), dtype=torch.float32)
            for i, data in enumerate(batch_data):
                if i < len(improvements) and 'improved' in data:
                    improvements[i] = float(data['improved'])
            
            success_loss = F.binary_cross_entropy(torch.clamp(success_prob.squeeze(), 1e-7, 1-1e-7), improvements)
            
            # Barrier detection
            stuck_indicators = (scores_tensor > 40).float()
            barrier_loss = F.binary_cross_entropy(torch.clamp(barrier_prob.squeeze(), 1e-7, 1-1e-7), stuck_indicators)
            
            # Combined loss
            total_loss = hash_loss + 0.5 * success_loss + 0.3 * barrier_loss
            
            # Backward pass with error handling
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
            self.optimizer.step()
            
            return {
                'hash_loss': hash_loss.item(),
                'success_loss': success_loss.item(),
                'barrier_loss': barrier_loss.item(),
                'total_loss': total_loss.item()
            }
            
        except Exception as e:
            # Reset optimizer state on error
            try:
                self.optimizer.zero_grad()
            except:
                pass
            return None
    
    def get_mutation_strategy(self, private_key, bit_weights, current_score):
        """Get mutation strategy for a given key"""
        try:
            self.eval()
            
            with torch.no_grad():
                # Convert inputs
                if isinstance(private_key, bytes):
                    key_bits = torch.tensor(np.unpackbits(np.frombuffer(private_key, dtype=np.uint8)), dtype=torch.float32)
                else:
                    key_bits = torch.tensor(private_key, dtype=torch.float32)
                
                if isinstance(bit_weights, np.ndarray):
                    weights_tensor = torch.tensor(bit_weights, dtype=torch.float32)
                else:
                    weights_tensor = torch.tensor(bit_weights, dtype=torch.float32)
                
                # Ensure correct dimensions
                if len(key_bits) != 256:
                    if len(key_bits) < 256:
                        padding = torch.zeros(256 - len(key_bits))
                        key_bits = torch.cat([key_bits, padding])
                    else:
                        key_bits = key_bits[:256]
                
                if len(weights_tensor) != 256:
                    weights_tensor = torch.ones(256) * 0.5
                
                # Get predictions
                outputs = self.forward(key_bits, weights_tensor, current_score)
                
                # Extract strategies
                mutation_probs = outputs['mutation_probs'].squeeze().cpu().numpy()
                hex_importance = outputs['hex_importance'].squeeze().cpu().numpy()
                success_prob = outputs['success_prob'].item()
                barrier_prob = outputs['barrier_prob'].item()
                correlation_matrix = outputs['correlation_matrix'].squeeze().cpu().numpy()
                
                # Find correlated bit groups
                bit_groups = self._extract_bit_groups(correlation_matrix)
                
                # Get top hex positions
                top_hex_indices = np.argsort(hex_importance)[-12:][::-1]
                
                return {
                    'mutation_probs': mutation_probs,
                    'hex_positions': top_hex_indices.tolist(),
                    'bit_groups': bit_groups,
                    'success_probability': success_prob,
                    'barrier_probability': barrier_prob,
                    'correlation_matrix': correlation_matrix
                }
        except Exception as e:
            print(f"⚠️ Neural strategy error: {e}")
            return {
                'mutation_probs': np.ones(256) * 0.1,
                'hex_positions': list(range(12)),
                'bit_groups': [],
                'success_probability': 0.5,
                'barrier_probability': 0.0,
                'correlation_matrix': np.eye(256)
            }
    
    def _extract_bit_groups(self, correlation_matrix, threshold=0.7):
        """Extract groups of bits that should mutate together"""
        groups = []
        processed = set()
        
        try:
            for i in range(256):
                if i in processed:
                    continue
                
                group = [i]
                for j in range(i + 1, 256):
                    if abs(correlation_matrix[i, j]) > threshold:
                        group.append(j)
                        processed.add(j)
                
                if len(group) > 1:
                    groups.append(group)
                    processed.add(i)
        except Exception:
            pass
        
        return groups


class HighPressureBitcoinEngine:
    """High pressure Bitcoin search engine with genetic optimizations"""
    
    def __init__(self, config: NeuralBitcoinConfig):
        self.config = config
        self.crypto = BitcoinCrypto()
        self.generators = BitcoinKeyGenerators.get_all_generators()
        self.atomics = HighPressureBitcoinAtomics(config)
        self.pressure_system = PopulationPressureSystem(config)
        self.num_cores = min(os.cpu_count() or 1, 16)  # Limit to prevent system overload
        
        # Population storage
        population_size = self.config.POPULATION_SIZE * 32
        self.shared_population = Array('B', population_size, lock=True)
        self.shared_scores = Array('i', self.config.POPULATION_SIZE, lock=True)
        
        # Adaptive weight learning system
        self.shared_weights = Array('f', 256, lock=True)  # Bit importance weights
        self.shared_eta = Array('f', 256, lock=True)      # Learning rates per bit
        
        # Advanced adaptive features (thread-safe)
        self.advanced_lock = threading.RLock()
        self.dynamic_weights = np.ones(256) * 0.5  # Dynamic bit weights
        self.covariance_matrix = np.eye(256) * 0.1  # Covariance structure
        self.stagnation_counter = 0
        self.previous_best_score = 160
        
        # Elite tracking
        self.elite_lock = threading.RLock()
        self.elite_keys = []
        self.elite_scores = []
        self.elite_valid = False
        
        # Target hash
        self.target_hash = None
        
        # Progress tracking
        self.last_reported_best = 160
        self.last_reported_elite_mean = 160.0
        
        self.initialize_shared_state()
        
        # Setup logging (only if not already configured)
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(filename='bitcoin_search.log', level=logging.INFO,
                              format='%(asctime)s - %(levelname)s - %(message)s')
        
        print(f"🔥 HIGH PRESSURE Bitcoin Engine: {self.num_cores} cores, "
              f"Population={self.config.POPULATION_SIZE}, Elite={self.config.ELITE_SIZE}")
        print(f"🧠 ADAPTIVE LEARNING: Bit-level weight tracking and learning enabled")
        print(f"🔑 KEY FORMAT: Using UNCOMPRESSED public keys (65 bytes) for Bitcoin puzzles")
        print(f"⚡ CRYPTO: Using coincurve (libsecp256k1) for blazing fast EC operations")
    
    def atomic_snapshot_weights(self) -> np.ndarray:
        """Get atomic snapshot of bit weights for safe mutation"""
        try:
            with self.shared_weights.get_lock():
                return np.array([self.shared_weights[i] for i in range(256)], dtype=np.float32)
        except Exception:
            return np.full(256, 0.12, dtype=np.float32)  # Safe fallback
    
    def update_adaptive_weights(self, old_key: bytes, new_key: bytes, improvement: float):
        """Learn from improvements: update weights for bits that contributed"""
        try:
            if len(old_key) != 32 or len(new_key) != 32:
                return
            
            improvement = max(0.0, min(1.0, improvement))
            learning_scale = self.config.GENETIC_LEARNING_SCALE
            
            with self.shared_weights.get_lock():
                with self.shared_eta.get_lock():
                    for bit_pos in range(256):
                        try:
                            byte_idx = bit_pos // 8
                            bit_idx = bit_pos % 8
                            
                            old_bit = (old_key[byte_idx] >> bit_idx) & 1
                            new_bit = (new_key[byte_idx] >> bit_idx) & 1
                            
                            if old_bit != new_bit:
                                # This bit flip contributed to improvement
                                current_weight = self.shared_weights[bit_pos]
                                current_eta = self.shared_eta[bit_pos]
                                
                                learning_factor = improvement * learning_scale * current_eta
                                new_weight = min(current_weight + learning_factor, 1.0)
                                self.shared_weights[bit_pos] = max(0.0, new_weight)
                                
                                # Increase learning rate for successful bits with decay
                                new_eta = min(current_eta * 1.01, 0.25)
                                self.shared_eta[bit_pos] = new_eta
                                
                                # Apply weight decay to prevent saturation
                                decay_factor = 0.5 if current_weight > 0.8 else 1.0
                                self.shared_weights[bit_pos] *= decay_factor
                            else:
                                # Decay learning rate for unchanged bits
                                current_eta = self.shared_eta[bit_pos]
                                new_eta = max(current_eta * 0.9995, 0.001)
                                self.shared_eta[bit_pos] = new_eta
                        except (IndexError, ValueError):
                            continue  # Skip problematic bits
        
        except Exception as e:
            pass  # Non-critical failure
    
    def weighted_bit_mutation(self, key: bytes, weights: np.ndarray, strength: float) -> bytes:
        """Apply bit mutations biased by learned weights"""
        try:
            if len(weights) != 256:
                return key
            
            key_array = bytearray(key)
            base_threshold = max(0.001, min(0.5, strength * 0.3))
            
            for bit_pos in range(256):
                try:
                    weight_val = max(0.0, weights[bit_pos])
                    flip_prob = base_threshold * (1.0 + weight_val * 2.0)  # Weight amplification
                    
                    if random.random() < flip_prob:
                        byte_idx = bit_pos // 8
                        bit_idx = bit_pos % 8
                        key_array[byte_idx] ^= (1 << bit_idx)
                except (IndexError, ValueError):
                    continue
            
            return bytes(key_array)
        except Exception:
            return key
    
    def targeted_hex_mutation(self, key: bytes) -> bytes:
        """Let algorithm directly choose which hex positions to modify"""
        try:
            key_array = bytearray(key)
            
            # Algorithm chooses which hex positions (0-63) to modify
            num_positions = random.randint(1, 12)  # Modify 1-12 hex positions
            positions = random.sample(range(64), num_positions)  # 64 hex positions in 32 bytes
            
            for pos in positions:
                byte_idx = pos // 2
                if pos % 2 == 0:  # Upper nibble (first hex digit of byte)
                    key_array[byte_idx] = (key_array[byte_idx] & 0x0F) | (random.randint(0, 15) << 4)
                else:  # Lower nibble (second hex digit of byte)
                    key_array[byte_idx] = (key_array[byte_idx] & 0xF0) | random.randint(0, 15)
            
            return bytes(key_array)
        except Exception:
            return key
    
    def smart_hex_mutation(self, key: bytes, weights: np.ndarray) -> bytes:
        """Choose hex positions based on bit weight analysis"""
        try:
            key_array = bytearray(key)
            
            # Calculate hex position weights (each hex = 4 bits)
            hex_weights = []
            for hex_pos in range(64):  # 64 hex positions
                bit_start = hex_pos * 4
                bit_end = min(bit_start + 4, 256)
                hex_weight = np.mean(weights[bit_start:bit_end]) if bit_end <= 256 else 0.0
                hex_weights.append((hex_weight, hex_pos))
            
            # Sort by weight and select top positions for mutation
            hex_weights.sort(reverse=True)
            num_to_mutate = random.randint(2, 8)
            
            # Mix high-weight positions with some random exploration
            selected_positions = []
            for i in range(min(num_to_mutate // 2, len(hex_weights))):
                if random.random() < 0.7:  # 70% chance to use high-weight position
                    selected_positions.append(hex_weights[i][1])
            
            # Add some random positions for exploration
            remaining = num_to_mutate - len(selected_positions)
            if remaining > 0:
                random_positions = random.sample(range(64), min(remaining, 64 - len(selected_positions)))
                selected_positions.extend(random_positions)
            
            # Apply mutations to selected hex positions
            for pos in selected_positions:
                byte_idx = pos // 2
                if pos % 2 == 0:  # Upper nibble
                    key_array[byte_idx] = (key_array[byte_idx] & 0x0F) | (random.randint(0, 15) << 4)
                else:  # Lower nibble
                    key_array[byte_idx] = (key_array[byte_idx] & 0xF0) | random.randint(0, 15)
            
            return bytes(key_array)
        except Exception:
            return key
    
    def initialize_shared_state(self):
        try:
            with self.shared_scores.get_lock():
                for i in range(self.config.POPULATION_SIZE):
                    self.shared_scores[i] = 160  # Worst possible score
            
            # Initialize adaptive weight learning
            with self.shared_weights.get_lock():
                for i in range(256):
                    self.shared_weights[i] = 0.12  # Base weight for all bits
            
            with self.shared_eta.get_lock():
                for i in range(256):
                    self.shared_eta[i] = 0.08  # Base learning rate
        
        except Exception as e:
            print(f"⚠️  Init error: {e}")
    
    def update_elite_pool(self):
        """Update elite pool with diversity awareness"""
        try:
            valid_individuals = []
            with self.shared_scores.get_lock():
                with self.shared_population.get_lock():
                    for i in range(self.config.POPULATION_SIZE):
                        score = self.shared_scores[i]
                        if score < 160:  # Valid score
                            start_idx = i * 32
                            key_bytes = bytes(self.shared_population[start_idx:start_idx + 32])
                            if any(key_bytes):
                                valid_individuals.append((score, i, key_bytes))
            
            if not valid_individuals:
                with self.elite_lock:
                    self.elite_keys = []
                    self.elite_scores = []
                    self.elite_valid = False
                return
            
            valid_individuals.sort(key=lambda x: x[0])  # Sort by score (lower = better)
            
            # Select elite with diversity awareness
            selected_elite = []
            for score, idx, key_bytes in valid_individuals:
                is_diverse = True
                for _, _, existing_key in selected_elite:
                    diversity = calculate_key_diversity_bits(key_bytes, existing_key)
                    if diversity < self.config.DIVERSITY_THRESHOLD:
                        is_diverse = False
                        break
                
                if is_diverse:
                    selected_elite.append((score, idx, key_bytes))
                    if len(selected_elite) >= self.config.ELITE_SIZE:
                        break
            
            # Fill remaining slots if needed
            if len(selected_elite) < self.config.ELITE_SIZE:
                used_indices = {idx for _, idx, _ in selected_elite}
                remaining = self.config.ELITE_SIZE - len(selected_elite)
                
                for score, idx, key_bytes in valid_individuals:
                    if idx not in used_indices:
                        selected_elite.append((score, idx, key_bytes))
                        remaining -= 1
                        if remaining <= 0:
                            break
            
            elite_keys = [key_bytes for _, _, key_bytes in selected_elite]
            elite_scores = [score for score, _, _ in selected_elite]
            
            with self.elite_lock:
                self.elite_keys = elite_keys.copy()
                self.elite_scores = elite_scores.copy()
                self.elite_valid = True
            
            if elite_scores:
                elite_mean = sum(elite_scores) / len(elite_scores)
                print(f"✅ Elite updated: {len(elite_keys)} keys, mean={elite_mean:.1f}")
        
        except Exception as e:
            print(f"⚠️  Elite update error: {e}")
    
    def get_elite_sample(self, n_samples: int = 5) -> List[bytes]:
        try:
            with self.elite_lock:
                if not self.elite_valid or not self.elite_keys:
                    return []
                samples = []
                for i in range(min(n_samples, len(self.elite_keys))):
                    if random.random() < 0.8:
                        idx = min(i, len(self.elite_keys) - 1)
                    else:
                        idx = random.randint(0, len(self.elite_keys) - 1)
                    samples.append(self.elite_keys[idx])
                return samples
        except:
            return []
    
    def get_elite_mean_score(self) -> float:
        try:
            with self.elite_lock:
                if not self.elite_valid or not self.elite_scores:
                    return 160.0
                return sum(self.elite_scores) / len(self.elite_scores)
        except:
            return 160.0
    
    def evaluate_key_fitness(self, private_key: bytes) -> int:
        """Evaluate Bitcoin key fitness (Enhanced with hex matching)"""
        try:
            self.atomics.atomic_increment_evals(1)
            hash160 = self.crypto.private_key_to_hash160(private_key)
            distance = enhanced_fitness(hash160, self.target_hash)
            # Convert back to int for compatibility
            distance_int = int(round(distance))
            self.atomics.try_update_global_best(distance_int, private_key)
            return distance_int
        except Exception:
            return 160
    
    def evolve_key(self, base_key: bytes, worker_id: int) -> List[bytes]:
        """Evolve Bitcoin key using adaptive weights and pressure strategies"""
        try:
            if len(base_key) != 32:
                return [base_key]
            
            candidates = []
            stats = self.atomics.atomic_get_all_stats()
            current_strength = stats['mutation_strength']
            pressure_level = stats['pressure_level']
            
            # Enhanced mutation based on pressure level
            enhanced_strength = current_strength * pressure_level
            
            # Get learned weights for adaptive mutation
            learned_weights = self.atomic_snapshot_weights()
            
            # Get thread-safe copies of advanced features
            with self.advanced_lock:
                dynamic_weights_copy = self.dynamic_weights.copy()
                covariance_matrix_copy = self.covariance_matrix.copy()
            
            # Get elite guidance
            elite_sample = self.get_elite_sample(3)
            
            # 1. Elite-guided crossover
            if elite_sample and random.random() < (0.6 * pressure_level):
                try:
                    elite_parent = random.choice(elite_sample)
                    crossover_offspring = self.pressure_system.breeding_system.elite_crossover(
                        base_key, elite_parent)
                    candidates.append(crossover_offspring)
                except:
                    pass
            
            # 2. ADAPTIVE WEIGHTED bit mutations (key learning mechanism)
            try:
                adaptive_candidate = self.weighted_bit_mutation(
                    base_key, learned_weights, enhanced_strength)
                candidates.append(adaptive_candidate)
            except:
                pass
            
            # 3. DIRECT HEX POSITION control - algorithm chooses hex positions
            try:
                hex_candidate = self.targeted_hex_mutation(base_key)
                candidates.append(hex_candidate)
            except:
                pass
            
            # 4. SMART HEX mutation based on learned weights
            try:
                smart_hex_candidate = self.smart_hex_mutation(base_key, learned_weights)
                candidates.append(smart_hex_candidate)
            except:
                pass
            
            # 5. Standard bit flip mutations with different intensities
            for mutation_intensity in [0.1, 0.2, 0.5]:
                try:
                    candidate = bytearray(base_key)
                    num_flips = max(1, int(256 * enhanced_strength * mutation_intensity))
                    positions = random.sample(range(256), min(num_flips, 256))
                    
                    for pos in positions:
                        byte_idx = pos // 8
                        bit_idx = pos % 8
                        candidate[byte_idx] ^= (1 << bit_idx)
                    
                    candidates.append(bytes(candidate))
                except:
                    continue
            
            # 6. Weighted chunk mutations (focus on high-weight regions)
            try:
                candidate = bytearray(base_key)
                chunk_size = 16
                
                # Find highest weight region
                chunk_weights = []
                for start in range(0, 256, chunk_size):
                    end = min(start + chunk_size, 256)
                    chunk_weight = np.mean(learned_weights[start:end])
                    chunk_weights.append((chunk_weight, start, end))
                
                # Prefer high-weight chunks
                chunk_weights.sort(reverse=True)
                for weight, start, end in chunk_weights[:3]:  # Top 3 chunks
                    if random.random() < weight * enhanced_strength:
                        for bit_pos in range(start, end):
                            if random.random() < 0.3:  # 30% flip rate within chunk
                                byte_idx = bit_pos // 8
                                bit_idx = bit_pos % 8
                                candidate[byte_idx] ^= (1 << bit_idx)
                
                candidates.append(bytes(candidate))
            except:
                pass
            
            # 7. Byte-level mutations
            try:
                candidate = bytearray(base_key)
                num_bytes = max(1, int(32 * enhanced_strength * 0.1))
                positions = random.sample(range(32), min(num_bytes, 32))
                
                for pos in positions:
                    candidate[pos] = random.randint(0, 255)
                
                candidates.append(bytes(candidate))
            except:
                pass
            
            # 8. Enhanced covariance-based mutation
            try:
                covariance_candidate = enhanced_covariance_mutation(
                    base_key, dynamic_weights_copy, covariance_matrix_copy, enhanced_strength * 0.1)
                candidates.append(covariance_candidate)
            except:
                pass
            
            # 9. Elite template-based generation
            if pressure_level > 1.5 and elite_sample:
                try:
                    template = random.choice(elite_sample)
                    guided_key = BitcoinKeyGenerators.elite_guided_generator(template)
                    candidates.append(guided_key)
                except:
                    pass
            
            return candidates if candidates else [base_key]
        except:
            return [base_key]
    
    def update_population_individual(self, individual_id: int, key: bytes, score: int):
        try:
            if individual_id >= self.config.POPULATION_SIZE or len(key) != 32:
                return
            with self.shared_population.get_lock():
                with self.shared_scores.get_lock():
                    start_idx = individual_id * 32
                    for i, byte_val in enumerate(key):
                        self.shared_population[start_idx + i] = byte_val
                    self.shared_scores[individual_id] = score
        except:
            pass
    
    def apply_population_pressure_round(self, round_num: int):
        """Apply population pressure every few rounds"""
        try:
            if round_num % self.config.POPULATION_REPLACEMENT_FREQ == 0:
                # Get current population data
                valid_individuals = []
                with self.shared_scores.get_lock():
                    with self.shared_population.get_lock():
                        for i in range(self.config.POPULATION_SIZE):
                            score = self.shared_scores[i]
                            if score < 160:
                                start_idx = i * 32
                                key_bytes = bytes(self.shared_population[start_idx:start_idx + 32])
                                if any(key_bytes):
                                    valid_individuals.append((score, i, key_bytes))
                
                # Get elite keys
                with self.elite_lock:
                    if self.elite_valid and self.elite_keys:
                        elite_keys = self.elite_keys.copy()
                    else:
                        return
                
                # Apply population pressure
                pressure_level = self.atomics.get_population_pressure_level()
                new_population_data = self.pressure_system.apply_population_pressure(
                    valid_individuals, elite_keys, pressure_level)
                
                # Update population with new data
                replacement_count = 0
                for score, index, key in new_population_data:
                    if score == 160:  # New key needs evaluation
                        new_score = self.evaluate_key_fitness(key)
                        self.update_population_individual(index, key, new_score)
                        replacement_count += 1
                
                if replacement_count > 0:
                    print(f"🔥 POPULATION PRESSURE APPLIED: {replacement_count} keys replaced/evaluated")
                
                # Update pressure level
                self.atomics.update_population_pressure(round_num)
        
        except Exception as e:
            print(f"⚠️  Population pressure error: {e}")
    
    def parallel_worker(self, worker_id: int, work_duration: float = 1.0):
        """Enhanced worker with pressure-based evolution and adaptive learning"""
        end_time = time.time() + work_duration
        local_best_score = 160
        local_best_key = None
        evaluations = 0
        learning_events = 0
        population_slot = worker_id % self.config.POPULATION_SIZE
        
        while time.time() < end_time:
            try:
                # Generate work with pure freedom - no structured sampling
                stats = self.atomics.atomic_get_all_stats()
                elite_template = None
                
                # Get elite template under pressure
                if stats['pressure_level'] > 1.0:
                    elite_sample = self.get_elite_sample(1)
                    if elite_sample:
                        elite_template = elite_sample[0]
                
                # Pure freedom: either random or elite-guided, no other constraints
                if elite_template and random.random() < 0.4:
                    work_key = BitcoinKeyGenerators.elite_guided_generator(elite_template)
                else:
                    work_key = BitcoinKeyGenerators.random_key_generator()
                
                # Evolve with pressure and adaptive weights
                evolved_keys = self.evolve_key(work_key, worker_id)
                
                best_in_batch = work_key
                best_score_batch = self.evaluate_key_fitness(work_key)
                evaluations += 1
                
                for evolved_key in evolved_keys:
                    try:
                        score = self.evaluate_key_fitness(evolved_key)
                        evaluations += 1
                        
                        if score < best_score_batch:
                            # ADAPTIVE LEARNING: Learn from improvement
                            improvement = (best_score_batch - score) / 160.0  # Normalize 0-1
                            self.update_adaptive_weights(best_in_batch, evolved_key, improvement)
                            learning_events += 1
                            
                            best_score_batch = score
                            best_in_batch = evolved_key
                        
                        if score < local_best_score:
                            local_best_score = score
                            local_best_key = evolved_key
                    except:
                        continue
                
                self.update_population_individual(population_slot, best_in_batch, best_score_batch)
            
            except:
                continue
        
        return {
            'worker_id': worker_id,
            'best_score': local_best_score,
            'best_key': local_best_key,
            'evaluations': evaluations,
            'learning_events': learning_events
        }
    
    def _init_individual(self, index: int):
        """Initialize a single individual (for parallel initialization)"""
        try:
            key = BitcoinKeyGenerators.random_key_generator()
            score = self.evaluate_key_fitness(key)
            self.update_population_individual(index, key, score)
            if index < 5:
                print(f"  Key {index}: score={score}, hex={key.hex()[:16]}...")
        except:
            pass
    
    def run_high_pressure_bitcoin_search(self, target_hash_hex: str, max_duration: float = 300.0) -> dict:
        """Main high pressure Bitcoin search loop"""
        print(f"🔥 Starting HIGH PRESSURE Bitcoin Search")
        print(f"🎯 Target Hash: {target_hash_hex}")
        print(f"⚡ Population: {self.config.POPULATION_SIZE}, Elite: {self.config.ELITE_SIZE}")
        print(f"🔑 Using UNCOMPRESSED public keys (Bitcoin puzzle format)")
        print(f"💻 CPU Cores: {self.num_cores}")
        print(f"🔓 PURE FREEDOM: No structured samplers - algorithm chooses its own path")
        print(f"🎯 DIRECT HEX CONTROL: Algorithm can target specific hex positions in private keys")
        print(f"⚠️  NOTE: This is mathematically impossible but demonstrates the algorithm")
        
        try:
            self.target_hash = bytes.fromhex(target_hash_hex)
            if len(self.target_hash) != 20:
                raise ValueError("Target hash must be 40 hex characters (20 bytes)")
        except Exception as e:
            return {'error': f"Invalid target hash: {e}"}
        
        with self.atomics.start_time.get_lock():
            self.atomics.start_time.value = time.time()
        
        try:
            # Initialize population with pure freedom
            print("🔥 Initializing high pressure population...")
            
            # Parallel initialization for speed
            init_batch_size = 1000
            with ThreadPoolExecutor(max_workers=self.num_cores) as init_executor:
                for batch_start in range(0, self.config.POPULATION_SIZE, init_batch_size):
                    batch_end = min(batch_start + init_batch_size, self.config.POPULATION_SIZE)
                    
                    # Print progress
                    if batch_start % 5000 == 0:
                        print(f"  Initialized {batch_start}/{self.config.POPULATION_SIZE} keys...")
                    
                    # Submit batch for parallel evaluation
                    init_futures = []
                    for i in range(batch_start, batch_end):
                        future = init_executor.submit(self._init_individual, i)
                        init_futures.append(future)
                    
                    # Wait for batch completion
                    for future in init_futures:
                        try:
                            future.result(timeout=1.0)
                        except:
                            continue
            
            print(f"✅ Population initialized: {self.config.POPULATION_SIZE} keys")
            
            self.update_elite_pool()
            
            initial_elite_mean = self.get_elite_mean_score()
            print(f"🎯 Initial elite mean: {initial_elite_mean:.1f} bits")
            
            # High pressure optimization loop
            with ThreadPoolExecutor(max_workers=self.num_cores) as executor:
                worker_duration = max_duration / 10000  # More rounds for Bitcoin
                
                for round_num in range(10000):
                    try:
                        round_start_stats = self.atomics.atomic_get_all_stats()
                        round_start_elite_mean = self.get_elite_mean_score()
                        
                        # Apply population pressure
                        self.apply_population_pressure_round(round_num)
                        
                        # Update advanced features (dynamic pools, weights, covariance)
                        self.update_advanced_features(round_num)
                        
                        # Cache cleanup every 50 rounds
                        if round_num % 50 == 0:
                            cache_stats = self.crypto.get_cache_stats()
                            self.crypto.cleanup_cache()
                            if round_num % 200 == 0:  # Report stats every 200 rounds
                                print(f"💾 Cache stats: size={cache_stats['cache_size']}, "
                                      f"hit_rate={cache_stats['hit_rate']:.1f}%")
                        
                        # PCA injection during stagnation
                        pca_samples = []
                        if round_num % 10 == 0:  # Check stagnation every 10 rounds
                            pca_samples = self.get_pca_injection_samples(int(self.config.POPULATION_SIZE * 0.05))
                            if pca_samples:
                                logging.info(f"PCA injection: {len(pca_samples)} samples during stagnation")
                        
                        # Submit workers
                        round_futures = []
                        for worker_id in range(self.num_cores):
                            future = executor.submit(self.parallel_worker, worker_id, worker_duration)
                            round_futures.append(future)
                        
                        # Wait for completion
                        worker_results = []
                        for future in round_futures:
                            try:
                                result = future.result(timeout=worker_duration + 5.0)
                                worker_results.append(result)
                            except:
                                continue
                        
                        # Inject PCA samples into population if available
                        if pca_samples:
                            for i, pca_key in enumerate(pca_samples[:min(len(pca_samples), self.config.POPULATION_SIZE // 10)]):
                                try:
                                    score = self.evaluate_key_fitness(pca_key)
                                    slot = (i * 137) % self.config.POPULATION_SIZE  # Distribute across slots
                                    self.update_population_individual(slot, pca_key, score)
                                except:
                                    continue
                        
                        # Check improvements
                        round_end_stats = self.atomics.atomic_get_all_stats()
                        round_end_elite_mean = self.get_elite_mean_score()
                        
                        global_improved = round_end_stats['best_score'] < round_start_stats['best_score']
                        
                        if global_improved:
                            self.atomics.update_improvement_round(round_num)
                            self.atomics.atomic_update_mutation_strength(self.config.MUTATION_DECAY)
                        
                        # Stagnation handling
                        stagnation_rounds = self.atomics.get_stagnation_rounds(round_num)
                        if stagnation_rounds >= self.config.STAGNATION_ROUNDS:
                            print(f"🔥 HIGH PRESSURE stagnation response: {stagnation_rounds} rounds")
                            self.atomics.atomic_update_mutation_strength(self.config.MUTATION_INCREASE)
                        
                        self.update_elite_pool()
                        self.report_progress(round_num + 1, max_duration)
                        
                        # Theoretical success condition
                        if round_end_stats['best_score'] == 0:
                            print("🎉 IMPOSSIBLE ACHIEVED: Found exact match!")
                            break
                    
                    except Exception as e:
                        print(f"⚠️  Round {round_num} error: {e}")
                        continue
        
        except Exception as e:
            print(f"⚠️  High pressure optimization error: {e}")
        
        # Results
        try:
            with self.atomics.start_time.get_lock():
                total_time = time.time() - self.atomics.start_time.value
            
            final_stats = self.atomics.atomic_get_all_stats()
            final_elite_mean = self.get_elite_mean_score()
            
            # Get final cache stats
            cache_stats = self.crypto.get_cache_stats()
            
            best_key_bytes = self.atomics.get_best_key()
            
            results = {
                'best_key_hex': best_key_bytes.hex(),
                'best_score': final_stats['best_score'],
                'final_elite_mean': final_elite_mean,
                'elite_size': len(self.elite_keys) if self.elite_valid else 0,
                'final_mutation_strength': final_stats['mutation_strength'],
                'final_pressure_level': final_stats['pressure_level'],
                'breeding_generation': final_stats['breeding_generation'],
                'total_evaluations': final_stats['evaluations'],
                'improvements': final_stats['improvements'],
                'total_time': total_time,
                'evals_per_second': final_stats['evaluations'] / total_time if total_time > 0 else 0,
                'cache_hit_rate': cache_stats['hit_rate'],
                'target_hash': target_hash_hex,
                'solved': final_stats['best_score'] == 0
            }
            return results
        except Exception as e:
            return {'error': str(e)}
    
    def update_advanced_features(self, round_num: int):
        """Update dynamic pools, weights, and covariance based on performance"""
        try:
            current_best = self.atomics.atomic_get_all_stats()['best_score']
            
            with self.advanced_lock:
                # Track stagnation
                if current_best >= self.previous_best_score:
                    self.stagnation_counter += 1
                else:
                    self.stagnation_counter = 0
                    self.previous_best_score = current_best
                
                # Analyze dynamic pools (but don't change array sizes)
                if round_num % 10 == 0:  # Every 10 rounds
                    new_pop_size, new_elite_size = adjust_population_pools(
                        self.config.POPULATION_SIZE, self.config.ELITE_SIZE, self.stagnation_counter)
                    
                    # Log recommendations without changing array bounds
                    logging.info(f"Dynamic pool analysis: recommended_pop={new_pop_size}, "
                               f"recommended_elite={new_elite_size}, stagnation={self.stagnation_counter}, "
                               f"current_pop={self.config.POPULATION_SIZE}")
                
                # Update adaptive weights
                with self.elite_lock:
                    if self.elite_valid and len(self.elite_keys) > 5:
                        self.dynamic_weights = update_bit_weights(
                            self.elite_keys, self.elite_keys[:10], self.dynamic_weights)
                        
                        # Update covariance structure
                        self.covariance_matrix = covariance_analysis(self.elite_keys)
        
        except Exception as e:
            logging.error(f"Advanced features update error: {e}")
    
    def get_pca_injection_samples(self, num_samples: int) -> List[bytes]:
        """Get PCA-based diversity injection samples during stagnation"""
        try:
            with self.advanced_lock:
                stagnation_check = self.stagnation_counter > 5
            
            with self.elite_lock:
                if self.elite_valid and len(self.elite_keys) >= 10 and stagnation_check:
                    return pca_inject(self.elite_keys, num_samples)
            return []
        except Exception:
            return []
    
    def get_weight_statistics(self) -> dict:
        """Get statistics about learned bit weights"""
        try:
            weights = self.atomic_snapshot_weights()
            return {
                'mean_weight': float(np.mean(weights)),
                'max_weight': float(np.max(weights)),
                'min_weight': float(np.min(weights)),
                'std_weight': float(np.std(weights)),
                'hot_bits': int(np.sum(weights > 0.5)),  # Highly weighted bits
                'cold_bits': int(np.sum(weights < 0.05))  # Low weighted bits
            }
        except Exception:
            return {'mean_weight': 0.12, 'max_weight': 0.12, 'min_weight': 0.12,
                   'std_weight': 0.0, 'hot_bits': 0, 'cold_bits': 0}
    
    def report_progress(self, round_num: int, max_duration: float):
        """Enhanced progress reporting with adaptive learning stats"""
        try:
            with self.atomics.start_time.get_lock():
                elapsed = time.time() - self.atomics.start_time.value
            
            stats = self.atomics.atomic_get_all_stats()
            current_best = stats['best_score']
            elite_mean = self.get_elite_mean_score()
            
            with self.elite_lock:
                elite_count = len(self.elite_keys) if self.elite_valid else 0
            
            mutation_strength = stats['mutation_strength']
            pressure_level = stats['pressure_level']
            stagnation_rounds = self.atomics.get_stagnation_rounds(round_num - 1)
            total_evals = stats['evaluations']
            improvements = stats['improvements']
            evals_per_sec = total_evals / elapsed if elapsed > 0 else 0
            
            # Get adaptive learning stats
            weight_stats = self.get_weight_statistics()
            
            should_report = False
            improvement_msg = ""
            
            if current_best < self.last_reported_best:
                should_report = True
                best_key_hex = self.atomics.get_best_key().hex()
                improvement_msg = f"🎯 NEW BEST: {self.last_reported_best}→{current_best} KEY: {best_key_hex}"
                self.last_reported_best = current_best
                
            elif elite_mean < (self.last_reported_elite_mean - 0.1):
                should_report = True
                improvement_msg = f"🔥 ELITE IMPROVEMENT: {self.last_reported_elite_mean:.1f}→{elite_mean:.1f}"
                self.last_reported_elite_mean = elite_mean
                
            elif round_num % 5 == 0:
                should_report = True
                improvement_msg = "🔥 HIGH-PRESSURE SEARCH"
            
            if should_report:
                print(f"🔥 Round {round_num:2d}: best={current_best:3d} bits, "
                      f"elite_mean={elite_mean:.1f} (n={elite_count}), "
                      f"pressure={pressure_level:.2f}, stag={stagnation_rounds}, "
                      f"mut_str={mutation_strength:.3f}, improvements={improvements}, "
                      f"evals={total_evals:,}, speed={evals_per_sec:,.0f}/s, "
                      f"weights=μ{weight_stats['mean_weight']:.3f}/σ{weight_stats['std_weight']:.3f}, "
                      f"hot_bits={weight_stats['hot_bits']}, "
                      f"elapsed={elapsed:.0f}s - {improvement_msg}")
                
                # Log progress
                logging.info(f"Round {round_num}: best={current_best}, elite_mean={elite_mean:.1f}, "
                           f"pressure={pressure_level:.2f}, improvements={improvements}, "
                           f"evals={total_evals}, speed={evals_per_sec:.0f}/s")
        
        except Exception as e:
            print(f"⚠️  Reporting error: {e}")


class NeuralBitcoinEngine(HighPressureBitcoinEngine):
    """Enhanced Bitcoin engine with integrated neural pattern learning"""
    
    def __init__(self, config: NeuralBitcoinConfig):
        # Initialize parent class
        super().__init__(config)
        
        # Initialize neural network
        self.neural_net = TransformerHashPatternLearner(config)
        self.neural_enabled = True
        
        # Learning buffer
        self.learning_buffer = deque(maxlen=config.NEURAL_MEMORY_SIZE)
        self.learning_lock = threading.Lock()
        
        # Performance tracking
        self.neural_improvements = 0
        self.neural_predictions_made = 0
        
        print(f"🧠 NEURAL PATTERN LEARNER: Transformer with {config.NEURAL_LAYERS} layers, "
              f"{config.NEURAL_HEADS} heads, learning black-box transformation")
    
    def save_checkpoint(self, filepath: str = "neural_bitcoin_checkpoint.pkl"):
        """Save complete search state"""
        try:
            checkpoint = {
                'neural_state': self.neural_net.state_dict(),
                'optimizer_state': self.neural_net.optimizer.state_dict(),
                'config': self.config,
                'target_hash': self.target_hash,
                'neural_improvements': self.neural_improvements,
                'neural_predictions_made': self.neural_predictions_made,
                'learning_buffer': list(self.learning_buffer),
                'atomics_state': self._get_atomics_state(),
                'population_state': self._get_population_state(),
                'adaptive_weights': self._get_adaptive_weights_state(),
                'elite_state': self._get_elite_state(),
                'advanced_features': self._get_advanced_features_state(),
                'round_info': getattr(self, 'current_round', 0)
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(checkpoint, f)
            print(f"💾 Checkpoint saved: {filepath}")
            return True
        except Exception as e:
            print(f"⚠️ Checkpoint save failed: {e}")
            return False
    
    def load_checkpoint(self, filepath: str = "neural_bitcoin_checkpoint.pkl"):
        """Load complete search state"""
        try:
            if not os.path.exists(filepath):
                print(f"⚠️ Checkpoint not found: {filepath}")
                return False
            
            with open(filepath, 'rb') as f:
                checkpoint = pickle.load(f)
            
            # Restore neural network
            self.neural_net.load_state_dict(checkpoint['neural_state'])
            self.neural_net.optimizer.load_state_dict(checkpoint['optimizer_state'])
            
            # Restore tracking
            self.neural_improvements = checkpoint['neural_improvements']
            self.neural_predictions_made = checkpoint['neural_predictions_made']
            self.learning_buffer = deque(checkpoint['learning_buffer'], maxlen=self.config.NEURAL_MEMORY_SIZE)
            
            # Restore search state
            self.target_hash = checkpoint['target_hash']
            self._restore_atomics_state(checkpoint['atomics_state'])
            self._restore_population_state(checkpoint['population_state'])
            self._restore_adaptive_weights_state(checkpoint['adaptive_weights'])
            self._restore_elite_state(checkpoint['elite_state'])
            self._restore_advanced_features_state(checkpoint['advanced_features'])
            
            print(f"📂 Checkpoint loaded: {filepath}")
            return True
        except Exception as e:
            print(f"⚠️ Checkpoint load failed: {e}")
            return False
    
    def _get_atomics_state(self):
        """Get atomics state for checkpointing"""
        return {
            'best_score': self.atomics.global_best_score.value,
            'improvements': self.atomics.global_improvements.value,
            'evaluations': self.atomics.global_evaluations.value,
            'best_key': self.atomics.get_best_key(),
            'mutation_strength': self.atomics.mutation_strength.value,
            'pressure_level': self.atomics.population_pressure_level.value,
            'last_improvement_round': self.atomics.last_improvement_round.value
        }
    
    def _restore_atomics_state(self, state):
        """Restore atomics state from checkpoint"""
        with self.atomics.global_best_score.get_lock():
            self.atomics.global_best_score.value = state['best_score']
        with self.atomics.global_improvements.get_lock():
            self.atomics.global_improvements.value = state['improvements']
        with self.atomics.global_evaluations.get_lock():
            self.atomics.global_evaluations.value = state['evaluations']
        with self.atomics.best_key_bytes.get_lock():
            for i, byte_val in enumerate(state['best_key'][:32]):
                self.atomics.best_key_bytes[i] = byte_val
        with self.atomics.mutation_strength.get_lock():
            self.atomics.mutation_strength.value = state['mutation_strength']
        with self.atomics.population_pressure_level.get_lock():
            self.atomics.population_pressure_level.value = state['pressure_level']
        with self.atomics.last_improvement_round.get_lock():
            self.atomics.last_improvement_round.value = state['last_improvement_round']
    
    def _get_population_state(self):
        """Get population state for checkpointing"""
        with self.shared_population.get_lock():
            with self.shared_scores.get_lock():
                return {
                    'population': list(self.shared_population[:]),
                    'scores': list(self.shared_scores[:])
                }
    
    def _restore_population_state(self, state):
        """Restore population state from checkpoint"""
        with self.shared_population.get_lock():
            with self.shared_scores.get_lock():
                for i, val in enumerate(state['population']):
                    self.shared_population[i] = val
                for i, score in enumerate(state['scores']):
                    self.shared_scores[i] = score
    
    def _get_adaptive_weights_state(self):
        """Get adaptive weights state for checkpointing"""
        with self.shared_weights.get_lock():
            with self.shared_eta.get_lock():
                return {
                    'weights': list(self.shared_weights[:]),
                    'eta': list(self.shared_eta[:])
                }
    
    def _restore_adaptive_weights_state(self, state):
        """Restore adaptive weights state from checkpoint"""
        with self.shared_weights.get_lock():
            with self.shared_eta.get_lock():
                for i, weight in enumerate(state['weights']):
                    self.shared_weights[i] = weight
                for i, eta in enumerate(state['eta']):
                    self.shared_eta[i] = eta
    
    def _get_elite_state(self):
        """Get elite state for checkpointing"""
        with self.elite_lock:
            return {
                'elite_keys': self.elite_keys.copy() if self.elite_keys else [],
                'elite_scores': self.elite_scores.copy() if self.elite_scores else [],
                'elite_valid': self.elite_valid
            }
    
    def _restore_elite_state(self, state):
        """Restore elite state from checkpoint"""
        with self.elite_lock:
            self.elite_keys = state['elite_keys']
            self.elite_scores = state['elite_scores']
            self.elite_valid = state['elite_valid']
    
    def _get_advanced_features_state(self):
        """Get advanced features state for checkpointing"""
        with self.advanced_lock:
            return {
                'dynamic_weights': self.dynamic_weights.copy(),
                'covariance_matrix': self.covariance_matrix.copy(),
                'stagnation_counter': self.stagnation_counter,
                'previous_best_score': self.previous_best_score
            }
    
    def _restore_advanced_features_state(self, state):
        """Restore advanced features state from checkpoint"""
        with self.advanced_lock:
            self.dynamic_weights = state['dynamic_weights']
            self.covariance_matrix = state['covariance_matrix']
            self.stagnation_counter = state['stagnation_counter']
            self.previous_best_score = state['previous_best_score']
    
    def evaluate_key_fitness(self, private_key: bytes) -> int:
        """Enhanced evaluation that feeds data to neural network"""
        try:
            self.atomics.atomic_increment_evals(1)
            hash160 = self.crypto.private_key_to_hash160(private_key)
            distance = enhanced_fitness(hash160, self.target_hash)
            distance_int = int(round(distance))
            
            # Feed to neural network for learning
            if self.neural_enabled and random.random() < 0.1:  # Sample 10% for learning
                key_bits = np.unpackbits(np.frombuffer(private_key, dtype=np.uint8))
                hash_bits = np.unpackbits(np.frombuffer(hash160, dtype=np.uint8))[:160]
                weights = self.atomic_snapshot_weights()
                
                learning_data = {
                    'key_bits': key_bits,
                    'hash_bits': hash_bits,
                    'score': distance_int,
                    'weights': weights,
                    'timestamp': time.time()
                }
                
                with self.learning_lock:
                    self.learning_buffer.append(learning_data)
                
                # Trigger learning every N samples
                if len(self.learning_buffer) >= self.config.NEURAL_BATCH_SIZE:
                    self._neural_learning_step()
            
            # Check for improvement
            improved = self.atomics.try_update_global_best(distance_int, private_key)
            if improved and self.neural_enabled:
                # Mark this as an improvement for neural learning
                with self.learning_lock:
                    if self.learning_buffer:
                        self.learning_buffer[-1]['improved'] = True
                        self.neural_improvements += 1
            
            return distance_int
        except Exception:
            return 160
    
    def _neural_learning_step(self):
        """Perform a neural network learning step"""
        try:
            with self.learning_lock:
                if len(self.learning_buffer) < self.config.NEURAL_BATCH_SIZE:
                    return
                
                # Get batch
                batch = list(self.learning_buffer)[:self.config.NEURAL_BATCH_SIZE]
                
                # Clear processed items
                for _ in range(min(self.config.NEURAL_BATCH_SIZE, len(self.learning_buffer))):
                    self.learning_buffer.popleft()
            
            # Learn from batch
            loss_info = self.neural_net.learn_from_batch(batch)
            
            # Store successful patterns
            for data in batch:
                if data.get('improved', False) or data['score'] < 50:  # Good scores
                    key_tensor = torch.tensor(data['key_bits'], dtype=torch.float32)
                    hash_tensor = torch.tensor(data['hash_bits'], dtype=torch.float32)
                    self.neural_net.store_pattern(key_tensor, hash_tensor, data['score'])
            
        except Exception as e:
            pass  # Non-critical, continue evolution
    
    def evolve_key(self, base_key: bytes, worker_id: int) -> List[bytes]:
        """Neural-enhanced key evolution"""
        try:
            if len(base_key) != 32:
                return [base_key]
            
            candidates = []
            stats = self.atomics.atomic_get_all_stats()
            current_strength = stats['mutation_strength']
            pressure_level = stats['pressure_level']
            enhanced_strength = current_strength * pressure_level
            
            # Get learned weights
            learned_weights = self.atomic_snapshot_weights()
            
            # Get neural guidance if enabled
            neural_strategy = None
            if self.neural_enabled:
                try:
                    current_score = self.evaluate_key_fitness(base_key)
                    neural_strategy = self.neural_net.get_mutation_strategy(
                        base_key, learned_weights, current_score
                    )
                    self.neural_predictions_made += 1
                except:
                    neural_strategy = None
            
            # Get thread-safe copies of advanced features
            with self.advanced_lock:
                dynamic_weights_copy = self.dynamic_weights.copy()
                covariance_matrix_copy = self.covariance_matrix.copy()
            
            # Get elite guidance
            elite_sample = self.get_elite_sample(3)
            
            # 1. Neural-guided mutations (if available and promising)
            if neural_strategy and neural_strategy['success_probability'] > 0.2:
                # a) Neural bit mutations
                neural_candidate = bytearray(base_key)
                mutation_probs = neural_strategy['mutation_probs']
                
                for bit_pos in range(256):
                    if random.random() < mutation_probs[bit_pos] * enhanced_strength:
                        byte_idx = bit_pos // 8
                        bit_idx = bit_pos % 8
                        neural_candidate[byte_idx] ^= (1 << bit_idx)
                
                candidates.append(bytes(neural_candidate))
                
                # b) Neural hex position mutations
                hex_candidate = bytearray(base_key)
                for hex_pos in neural_strategy['hex_positions'][:8]:
                    byte_idx = hex_pos // 2
                    if hex_pos % 2 == 0:
                        hex_candidate[byte_idx] = (hex_candidate[byte_idx] & 0x0F) | (random.randint(0, 15) << 4)
                    else:
                        hex_candidate[byte_idx] = (hex_candidate[byte_idx] & 0xF0) | random.randint(0, 15)
                
                candidates.append(bytes(hex_candidate))
                
                # c) Correlated bit group mutations
                for bit_group in neural_strategy['bit_groups'][:2]:
                    group_candidate = bytearray(base_key)
                    if random.random() < 0.5:  # Flip entire group
                        for bit_pos in bit_group:
                            byte_idx = bit_pos // 8
                            bit_idx = bit_pos % 8
                            group_candidate[byte_idx] ^= (1 << bit_idx)
                    candidates.append(bytes(group_candidate))
            
            # 2. Elite-guided crossover
            if elite_sample and random.random() < (0.6 * pressure_level):
                try:
                    elite_parent = random.choice(elite_sample)
                    crossover_offspring = self.pressure_system.breeding_system.elite_crossover(
                        base_key, elite_parent)
                    candidates.append(crossover_offspring)
                except:
                    pass
            
            # 3. ADAPTIVE WEIGHTED bit mutations
            try:
                adaptive_candidate = self.weighted_bit_mutation(
                    base_key, learned_weights, enhanced_strength)
                candidates.append(adaptive_candidate)
            except:
                pass
            
            # 4. DIRECT HEX POSITION control
            try:
                hex_candidate = self.targeted_hex_mutation(base_key)
                candidates.append(hex_candidate)
            except:
                pass
            
            # 5. SMART HEX mutation based on learned weights
            try:
                smart_hex_candidate = self.smart_hex_mutation(base_key, learned_weights)
                candidates.append(smart_hex_candidate)
            except:
                pass
            
            # 6. Barrier-breaking mutations (if neural net detects barrier)
            if neural_strategy and neural_strategy['barrier_probability'] > 0.7:
                # Aggressive mutations for barrier breaking
                barrier_candidate = bytearray(base_key)
                
                # Focus on bits that neural net thinks are stuck
                correlation_matrix = neural_strategy['correlation_matrix']
                
                # Find least correlated bits (most independent)
                independence = 1 - np.abs(correlation_matrix).mean(axis=0)
                independent_bits = np.argsort(independence)[-30:]  # Top 30 independent bits
                
                for bit_pos in independent_bits:
                    if random.random() < 0.8:  # High mutation rate for independent bits
                        byte_idx = bit_pos // 8
                        bit_idx = bit_pos % 8
                        barrier_candidate[byte_idx] ^= (1 << bit_idx)
                
                candidates.append(bytes(barrier_candidate))
            
            # 7. Standard mutations with different intensities
            for mutation_intensity in [0.1, 0.2, 0.5]:
                try:
                    candidate = bytearray(base_key)
                    num_flips = max(1, int(256 * enhanced_strength * mutation_intensity))
                    positions = random.sample(range(256), min(num_flips, 256))
                    
                    for pos in positions:
                        byte_idx = pos // 8
                        bit_idx = pos % 8
                        candidate[byte_idx] ^= (1 << bit_idx)
                    
                    candidates.append(bytes(candidate))
                except:
                    continue
            
            # 8. Enhanced covariance-based mutation
            try:
                covariance_candidate = enhanced_covariance_mutation(
                    base_key, dynamic_weights_copy, covariance_matrix_copy, enhanced_strength * 0.1)
                candidates.append(covariance_candidate)
            except:
                pass
            
            return candidates if candidates else [base_key]
        except:
            return [base_key]
    
    def report_progress(self, round_num: int, max_duration: float):
        """Enhanced progress reporting with neural stats"""
        try:
            with self.atomics.start_time.get_lock():
                elapsed = time.time() - self.atomics.start_time.value
            
            stats = self.atomics.atomic_get_all_stats()
            current_best = stats['best_score']
            elite_mean = self.get_elite_mean_score()
            
            with self.elite_lock:
                elite_count = len(self.elite_keys) if self.elite_valid else 0
            
            mutation_strength = stats['mutation_strength']
            pressure_level = stats['pressure_level']
            stagnation_rounds = self.atomics.get_stagnation_rounds(round_num - 1)
            total_evals = stats['evaluations']
            improvements = stats['improvements']
            evals_per_sec = total_evals / elapsed if elapsed > 0 else 0
            
            # Get adaptive learning stats
            weight_stats = self.get_weight_statistics()
            
            # Neural stats
            neural_success_rate = (self.neural_improvements / max(1, self.neural_predictions_made)) * 100
            
            should_report = False
            improvement_msg = ""
            
            if current_best < self.last_reported_best:
                should_report = True
                best_key_hex = self.atomics.get_best_key().hex()
                improvement_msg = f"🎯 NEW BEST: {self.last_reported_best}→{current_best} KEY: {best_key_hex}"
                self.last_reported_best = current_best
                
            elif elite_mean < (self.last_reported_elite_mean - 0.1):
                should_report = True
                improvement_msg = f"🔥 ELITE IMPROVEMENT: {self.last_reported_elite_mean:.1f}→{elite_mean:.1f}"
                self.last_reported_elite_mean = elite_mean
                
            elif round_num % 5 == 0:
                should_report = True
                improvement_msg = "🔥 HIGH-PRESSURE SEARCH"
            
            if should_report:
                print(f"🔥 Round {round_num:2d}: best={current_best:3d} bits, "
                      f"elite_mean={elite_mean:.1f} (n={elite_count}), "
                      f"pressure={pressure_level:.2f}, stag={stagnation_rounds}, "
                      f"mut_str={mutation_strength:.3f}, improvements={improvements}, "
                      f"evals={total_evals:,}, speed={evals_per_sec:,.0f}/s, "
                      f"weights=μ{weight_stats['mean_weight']:.3f}/σ{weight_stats['std_weight']:.3f}, "
                      f"hot_bits={weight_stats['hot_bits']}, "
                      f"🧠neural_success={neural_success_rate:.1f}%, "
                      f"elapsed={elapsed:.0f}s - {improvement_msg}")
                
                # Log progress
                logging.info(f"Round {round_num}: best={current_best}, elite_mean={elite_mean:.1f}, "
                           f"pressure={pressure_level:.2f}, improvements={improvements}, "
                           f"neural_success_rate={neural_success_rate:.1f}%, "
                           f"evals={total_evals}, speed={evals_per_sec:.0f}/s")
            
        except Exception as e:
            print(f"⚠️  Reporting error: {e}")


# Keep all the original helper classes and functions
class BitcoinCrypto:
    """Bitcoin cryptographic operations"""
    
    def __init__(self):
        self.pubkey_cache = {}
        self.cache_lock = threading.RLock()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def private_key_to_public_key(self, private_key: bytes) -> bytes:
        """Convert private key to UNCOMPRESSED public key for Bitcoin puzzles using coincurve"""
        if len(private_key) != 32:
            raise ValueError("Private key must be 32 bytes")
        
        # Check cache first (thread-safe)
        key_int = int.from_bytes(private_key, 'big')
        with self.cache_lock:
            if key_int in self.pubkey_cache:
                self.cache_hits += 1
                return self.pubkey_cache[key_int]
            self.cache_misses += 1
        
        try:
            # Ensure valid private key range
            if key_int == 0 or key_int >= SECP256K1_ORDER:
                key_int = (key_int % (SECP256K1_ORDER - 1)) + 1
                private_key = key_int.to_bytes(32, 'big')
            
            # Use coincurve for fast EC operations
            pk = PrivateKey(private_key)
            # Get uncompressed public key (65 bytes: 0x04 + X + Y)
            result = pk.public_key.format(compressed=False)
            
            # Cache the result (thread-safe)
            with self.cache_lock:
                self.pubkey_cache[key_int] = result
            
            return result
        except Exception as e:
            # Fallback: ensure valid key and retry
            key_int = int.from_bytes(private_key, 'big')
            if key_int == 0:
                key_int = 1
            elif key_int >= SECP256K1_ORDER:
                key_int = SECP256K1_ORDER - 1
            
            private_key = key_int.to_bytes(32, 'big')
            pk = PrivateKey(private_key)
            return pk.public_key.format(compressed=False)
    
    def hash160(self, data: bytes) -> bytes:
        """Compute RIPEMD160(SHA256(data))"""
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()
    
    def cleanup_cache(self):
        """Cleanup ECC cache to prevent memory issues"""
        with self.cache_lock:
            if len(self.pubkey_cache) > 5000:  # Reduced limit for larger uncompressed keys
                # Keep only the most recent quarter
                keys_to_remove = list(self.pubkey_cache.keys())[:-1250]
                for key in keys_to_remove:
                    del self.pubkey_cache[key]
    
    def get_cache_stats(self):
        """Get cache performance statistics"""
        with self.cache_lock:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
            return {
                'cache_size': len(self.pubkey_cache),
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'hit_rate': hit_rate
            }
    
    def private_key_to_hash160(self, private_key: bytes) -> bytes:
        """Convert private key to hash160 (Bitcoin address format)"""
        pubkey = self.private_key_to_public_key(private_key)
        return self.hash160(pubkey)


class HighPressureBitcoinAtomics:
    """Enhanced atomics with population pressure tracking for Bitcoin search"""
    def __init__(self, config: NeuralBitcoinConfig):
        self.config = config
        self.global_best_score = Value('i', 160, lock=True)
        self.global_improvements = Value('L', 0, lock=True)
        self.global_evaluations = Value('L', 0, lock=True)
        self.best_key_bytes = Array('B', 32, lock=True)
        self.last_improvement_time = Value('d', 0.0, lock=True)
        self.start_time = Value('d', 0.0, lock=True)
        self.last_improvement_round = Value('i', 0, lock=True)
        self.mutation_strength = Value('f', config.MUTATION_STRENGTH, lock=True)
        
        # Population pressure tracking
        self.population_pressure_level = Value('f', 1.0, lock=True)
        self.elite_breeding_generation = Value('L', 0, lock=True)
        self.convergence_acceleration = Value('f', 1.0, lock=True)
        self.last_population_pressure = Value('i', 0, lock=True)
    
    def atomic_increment_evals(self, count: int = 1) -> int:
        with self.global_evaluations.get_lock():
            old_val = self.global_evaluations.value
            self.global_evaluations.value = old_val + count
            return self.global_evaluations.value
    
    def try_update_global_best(self, new_score: int, new_key: bytes) -> bool:
        with self.global_best_score.get_lock():
            current_best = self.global_best_score.value
            if new_score < current_best:
                self.global_best_score.value = new_score
                with self.global_improvements.get_lock():
                    self.global_improvements.value += 1
                with self.last_improvement_time.get_lock():
                    self.last_improvement_time.value = time.time()
                with self.best_key_bytes.get_lock():
                    for i, byte_val in enumerate(new_key[:32]):
                        self.best_key_bytes[i] = byte_val
                # Trigger convergence acceleration
                self.trigger_convergence_acceleration()
                return True
        return False
    
    def trigger_convergence_acceleration(self):
        """Trigger population-wide convergence acceleration"""
        with self.convergence_acceleration.get_lock():
            self.convergence_acceleration.value *= self.config.CONVERGENCE_ACCELERATION
    
    def update_improvement_round(self, round_num: int):
        with self.last_improvement_round.get_lock():
            self.last_improvement_round.value = round_num
    
    def get_stagnation_rounds(self, current_round: int) -> int:
        with self.last_improvement_round.get_lock():
            return current_round - self.last_improvement_round.value
    
    def atomic_update_mutation_strength(self, multiplier: float) -> float:
        with self.mutation_strength.get_lock():
            old_value = self.mutation_strength.value
            new_value = old_value * multiplier
            new_value = max(self.config.MUTATION_MIN, min(self.config.MUTATION_MAX, new_value))
            self.mutation_strength.value = new_value
            return new_value
    
    def update_population_pressure(self, round_num: int):
        """Update population pressure level"""
        with self.population_pressure_level.get_lock():
            base_pressure = 1.0
            escalation = (round_num * 0.1) * self.config.PRESSURE_ESCALATION_RATE
            self.population_pressure_level.value = min(3.0, base_pressure + escalation)
    
    def get_population_pressure_level(self) -> float:
        with self.population_pressure_level.get_lock():
            return self.population_pressure_level.value
    
    def get_convergence_acceleration(self) -> float:
        with self.convergence_acceleration.get_lock():
            current = self.convergence_acceleration.value
            # Decay acceleration over time
            self.convergence_acceleration.value = max(1.0, current * 0.95)
            return current
    
    def get_mutation_strength(self) -> float:
        with self.mutation_strength.get_lock():
            return self.mutation_strength.value
    
    def get_best_key(self) -> bytes:
        with self.best_key_bytes.get_lock():
            return bytes(self.best_key_bytes[:32])
    
    def atomic_get_all_stats(self) -> dict:
        with self.global_best_score.get_lock():
            best_score = self.global_best_score.value
        with self.global_improvements.get_lock():
            improvements = self.global_improvements.value
        with self.global_evaluations.get_lock():
            evaluations = self.global_evaluations.value
        with self.mutation_strength.get_lock():
            mutation_strength = self.mutation_strength.value
        with self.population_pressure_level.get_lock():
            pressure_level = self.population_pressure_level.value
        with self.elite_breeding_generation.get_lock():
            breeding_generation = self.elite_breeding_generation.value
        
        return {
            'best_score': best_score,
            'improvements': improvements,
            'evaluations': evaluations,
            'mutation_strength': mutation_strength,
            'pressure_level': pressure_level,
            'breeding_generation': breeding_generation
        }


def hamming_distance_160(h1: bytes, h2: bytes) -> int:
    """Calculate Hamming distance between two 20-byte hashes"""
    if len(h1) != 20 or len(h2) != 20:
        return 160
    
    distance = 0
    for i in range(20):
        xor_byte = h1[i] ^ h2[i]
        distance += bin(xor_byte).count('1')
    
    return distance


def enhanced_fitness(hash160: bytes, target_hash: bytes) -> float:
    """Enhanced fitness with hex match weighting"""
    hd = hamming_distance_160(hash160, target_hash)
    hex_matches = sum(a == b for a, b in zip(hash160.hex(), target_hash.hex()))
    return hd - (hex_matches * 0.1)  # Weight hex matches


def dynamic_mutation_scaling(current_best: int, previous_best: int, mutation_strength: float) -> float:
    """Dynamically adjust mutation strength based on performance"""
    if current_best >= previous_best:
        return min(mutation_strength * 1.1, 0.95)  # Increase when stagnant
    else:
        return max(mutation_strength * 0.9, 0.15)  # Decrease after improvement


def adjust_population_pools(population_size: int, elite_size: int, stagnation_rounds: int, max_pop: int = 100000, min_pop: int = 5000) -> tuple:
    """Dynamically scale the population and elite pool sizes"""
    if stagnation_rounds > 5:
        population_size = min(max_pop, int(population_size * 1.5))
        elite_size = max(int(elite_size * 0.9), 500)
    else:
        population_size = max(min_pop, int(population_size * 0.9))
        elite_size = min(int(elite_size * 1.1), int(population_size * 0.1))
    return population_size, elite_size


def update_bit_weights(population: List[bytes], best_individuals: List[bytes], weights: np.ndarray, learning_rate: float = 0.01) -> np.ndarray:
    """Update weights based on successful mutations"""
    try:
        for ind in best_individuals:
            if len(ind) == 32:
                for bit_idx in range(256):
                    bit_val = (ind[bit_idx // 8] >> (bit_idx % 8)) & 1
                    weights[bit_idx] += learning_rate * (bit_val - weights[bit_idx])
        return np.clip(weights, 0.05, 0.95)
    except Exception:
        return weights


def pca_inject(elite_pool: List[bytes], num_samples: int = 5000, scale: float = 0.2) -> List[bytes]:
    """Inject PCA-based structured diversity into the population"""
    try:
        if len(elite_pool) < 10:
            return []
        
        elite_array = np.array([np.unpackbits(np.frombuffer(k, dtype=np.uint8)) for k in elite_pool])
        pca = PCA(n_components=min(10, len(elite_pool)))
        pca.fit(elite_array)
        
        mean = pca.mean_
        components = pca.components_
        variances = pca.explained_variance_
        
        injected_population = []
        for _ in range(num_samples):
            coeffs = np.random.randn(len(variances)) * np.sqrt(variances) * scale
            new_sample_bits = mean + np.dot(coeffs, components)
            new_sample_bits = np.clip(new_sample_bits, 0, 1)
            new_sample_bytes = np.packbits((new_sample_bits > 0.5).astype(np.uint8)).tobytes()[:32]
            if len(new_sample_bytes) == 32:
                injected_population.append(new_sample_bytes)
        
        return injected_population
    except Exception:
        return []


def covariance_analysis(elite_pool: List[bytes]) -> np.ndarray:
    """Analyze covariance structure of elite pool"""
    try:
        if len(elite_pool) < 5:
            return np.eye(256) * 0.1
        
        elite_array = np.array([np.unpackbits(np.frombuffer(k, dtype=np.uint8)) for k in elite_pool])
        covariance_matrix = np.cov(elite_array, rowvar=False)
        return covariance_matrix + 1e-6 * np.eye(256)  # Add regularization
    except Exception:
        return np.eye(256) * 0.1


def enhanced_covariance_mutation(parent: bytes, weights: np.ndarray, covariance_matrix: np.ndarray, mutation_rate: float = 0.05) -> bytes:
    """Enhanced mutation using covariance structure"""
    try:
        parent_bits = np.unpackbits(np.frombuffer(parent, dtype=np.uint8))
        
        if random.random() < 0.3:  # 30% chance for structured mutation
            try:
                # Robust Cholesky decomposition with fallback
                try:
                    cov_cholesky = np.linalg.cholesky(covariance_matrix)
                    perturbation = np.dot(cov_cholesky, np.random.randn(256)) > 0.5
                    child_bits = np.bitwise_xor(parent_bits, perturbation.astype(np.uint8))
                except (np.linalg.LinAlgError, ValueError):
                    # Fallback: eigenvalue decomposition for non-positive definite matrices
                    try:
                        eigenvals, eigenvecs = np.linalg.eigh(covariance_matrix)
                        eigenvals = np.maximum(eigenvals, 1e-8)  # Ensure positive
                        sqrt_eigenvals = np.sqrt(eigenvals)
                        perturbation = np.dot(eigenvecs, sqrt_eigenvals * np.random.randn(256)) > 0.5
                        child_bits = np.bitwise_xor(parent_bits, perturbation.astype(np.uint8))
                    except (np.linalg.LinAlgError, ValueError):
                        # Final fallback to weighted mutation
                        flips = np.random.rand(256) < weights * mutation_rate
                        child_bits = np.bitwise_xor(parent_bits, flips.astype(np.uint8))
            except Exception:
                # Weighted random bit flip fallback
                flips = np.random.rand(256) < weights * mutation_rate
                child_bits = np.bitwise_xor(parent_bits, flips.astype(np.uint8))
        else:
            # Weighted random bit flip
            flips = np.random.rand(256) < weights * mutation_rate
            child_bits = np.bitwise_xor(parent_bits, flips.astype(np.uint8))
        
        result = np.packbits(child_bits).tobytes()[:32]
        return result if len(result) == 32 else parent
    except Exception:
        return parent


def calculate_key_diversity_bits(key1: bytes, key2: bytes) -> float:
    """Calculate diversity between two keys in raw bits"""
    if len(key1) != 32 or len(key2) != 32:
        return 0.0
    return float(sum(a != b for a, b in zip(key1, key2)))


class BitcoinKeyGenerators:
    """Collection of Bitcoin private key generators"""
    
    @staticmethod
    def random_key_generator() -> bytes:
        """Generate completely random private keys - no seeds, pure freedom"""
        return random.randbytes(32)
    
    @staticmethod
    def elite_guided_generator(elite_template: bytes = None) -> bytes:
        """Generate keys guided by elite templates"""
        if elite_template is None:
            return BitcoinKeyGenerators.random_key_generator()
        
        try:
            # Create variation of elite template
            new_key = bytearray(elite_template)
            
            # Apply controlled mutations (5-15% of bits)
            mutation_rate = random.uniform(0.05, 0.15)
            num_mutations = int(256 * mutation_rate)
            positions = random.sample(range(256), num_mutations)
            
            for pos in positions:
                byte_idx = pos // 8
                bit_idx = pos % 8
                new_key[byte_idx] ^= (1 << bit_idx)
            
            return bytes(new_key)
        except Exception:
            return BitcoinKeyGenerators.random_key_generator()
    
    @classmethod
    def get_all_generators(cls) -> List[Callable[[], bytes]]:
        """Return all key generators"""
        return [
            cls.random_key_generator,
            cls.random_key_generator,  # More weight to pure random
            cls.random_key_generator,
        ]


class EliteBitcoinBreeding:
    """Elite breeding system for Bitcoin keys"""
    
    def __init__(self, config: NeuralBitcoinConfig):
        self.config = config
    
    def elite_crossover(self, parent1: bytes, parent2: bytes) -> bytes:
        """Advanced crossover between elite Bitcoin keys"""
        try:
            if len(parent1) != 32 or len(parent2) != 32:
                return parent1
            
            strategy = random.choice(['single_point', 'two_point', 'uniform', 'bit_blend'])
            
            if strategy == 'single_point':
                crossover_point = random.randint(1, 31)
                offspring = parent1[:crossover_point] + parent2[crossover_point:]
                
            elif strategy == 'two_point':
                point1 = random.randint(0, 30)
                point2 = random.randint(point1 + 1, 32)
                offspring = parent1[:point1] + parent2[point1:point2] + parent1[point2:]
                
            elif strategy == 'uniform':
                offspring = bytearray(32)
                for i in range(32):
                    offspring[i] = parent1[i] if random.random() < 0.5 else parent2[i]
                offspring = bytes(offspring)
                
            else:  # bit_blend
                offspring = bytearray(32)
                for i in range(32):
                    # XOR blend
                    offspring[i] = parent1[i] ^ parent2[i]
                offspring = bytes(offspring)
            
            return offspring
            
        except Exception:
            return parent1
    
    def breed_elite_population(self, elite_keys: List[bytes], target_size: int) -> List[bytes]:
        """Generate new population from elite breeding"""
        if not elite_keys or len(elite_keys) < 2:
            return elite_keys
        
        bred_population = []
        
        # Keep original elite
        bred_population.extend(elite_keys)
        
        # Generate offspring through crossover
        while len(bred_population) < target_size:
            try:
                parent1_idx = min(random.randint(0, len(elite_keys) - 1),
                                random.randint(0, len(elite_keys) - 1))
                parent2_idx = min(random.randint(0, len(elite_keys) - 1),
                                random.randint(0, len(elite_keys) - 1))
                
                if parent1_idx != parent2_idx:
                    parent1 = elite_keys[parent1_idx]
                    parent2 = elite_keys[parent2_idx]
                    offspring = self.elite_crossover(parent1, parent2)
                    bred_population.append(offspring)
                else:
                    # Add slight variation to elite
                    base = elite_keys[parent1_idx]
                    mutated = self.slight_mutation(base)
                    bred_population.append(mutated)
                    
            except Exception:
                continue
        
        return bred_population[:target_size]
    
    def slight_mutation(self, key: bytes) -> bytes:
        """Apply slight mutation for variation"""
        try:
            key_array = bytearray(key)
            
            # 1-5 bit flips
            num_mutations = random.randint(1, 5)
            positions = random.sample(range(256), min(num_mutations, 256))
            
            for pos in positions:
                byte_idx = pos // 8
                bit_idx = pos % 8
                key_array[byte_idx] ^= (1 << bit_idx)
            
            return bytes(key_array)
        except Exception:
            return key


class PopulationPressureSystem:
    """Population pressure system for Bitcoin key search"""
    
    def __init__(self, config: NeuralBitcoinConfig):
        self.config = config
        self.breeding_system = EliteBitcoinBreeding(config)
    
    def apply_population_pressure(self, population_data: List[Tuple[int, int, bytes]],
                                elite_keys: List[bytes], pressure_level: float) -> List[Tuple[int, int, bytes]]:
        """Apply aggressive population pressure"""
        try:
            if not elite_keys or not population_data:
                return population_data
            
            # Sort population by score (best first)
            population_data.sort(key=lambda x: x[0])
            
            # Calculate replacement rate based on pressure level
            base_rate = self.config.POPULATION_PRESSURE_RATE
            pressure_adjusted_rate = min(0.95, base_rate * pressure_level)
            
            num_to_replace = int(len(population_data) * pressure_adjusted_rate)
            survivors = population_data[:len(population_data) - num_to_replace]
            
            print(f"🔥 POPULATION PRESSURE: Replacing {num_to_replace}/{len(population_data)} keys "
                  f"(pressure={pressure_level:.2f})")
            
            # Generate replacements from elite breeding
            replacement_size = num_to_replace
            bred_keys = self.breeding_system.breed_elite_population(elite_keys, replacement_size)
            
            # Create new population entries
            new_individuals = []
            for i, key in enumerate(bred_keys):
                temp_score = 160  # Will be re-evaluated
                temp_index = len(survivors) + i
                new_individuals.append((temp_score, temp_index, key))
            
            # Combine survivors with bred individuals
            new_population = survivors + new_individuals
            
            return new_population
            
        except Exception as e:
            print(f"⚠️  Population pressure error: {e}")
            return population_data


def neural_bitcoin_search(target_hash_hex: str, duration: float = 300.0, population_size: int = None):
    """
    🧠 NEURAL-ENHANCED BITCOIN SEARCH
    Combines genetic algorithms with transformer-based pattern learning
    Uses UNCOMPRESSED public keys for Bitcoin puzzle compatibility
    
    Args:
        target_hash_hex: Target hash160 to search for (40 hex chars)
        duration: Search duration in seconds
        population_size: Override default population size (None = use default)
    """
    print("🧠⚡₿ NEURAL-ENHANCED BITCOIN SEARCH ₿⚡🧠")
    print("=" * 100)
    print("🔑 UNCOMPRESSED KEYS: Using 65-byte public keys for Bitcoin puzzles")
    print("⚡ PERFORMANCE: coincurve + optimized CPU usage for maximum speed")
    print("🧠 TRANSFORMER PATTERN LEARNER: Discovers hash transformation patterns")
    print("🔥 AGGRESSIVE GENETIC OPTIMIZATION with neural guidance")
    print("🔓 PURE FREEDOM: Algorithm learns its own exploration strategy")
    print("⚠️  EDUCATIONAL ONLY: Demonstrates neural networks on cryptographic landscapes")
    
    try:
        config = NeuralBitcoinConfig()
        if population_size:
            config.POPULATION_SIZE = population_size
            config.ELITE_SIZE = max(100, population_size // 100)
        
        engine = NeuralBitcoinEngine(config)
        
        results = engine.run_high_pressure_bitcoin_search(target_hash_hex, duration)
        
        if 'error' in results:
            print(f"❌ Neural Bitcoin search failed: {results['error']}")
            return results
        
        print("\n" + "="*100)
        print("🧠⚡₿ NEURAL BITCOIN RESULTS ₿⚡🧠")
        print("="*100)
        print(f"Target Hash:        {results['target_hash']}")
        print(f"🔑 BEST PRIVATE KEY: {results['best_key_hex']}")
        print(f"Best Score:         🎯 {results['best_score']} bits difference")
        print(f"Elite Mean:         🔥 {results['final_elite_mean']:.1f} bits (n={results['elite_size']})")
        print(f"Pressure Level:     🔥 {results['final_pressure_level']:.2f}")
        print(f"Mutation Strength:  🎛️  {results['final_mutation_strength']:.3f}")
        print(f"Total Evaluations:  ⚡ {results['total_evaluations']:,}")
        print(f"Improvements:       📈 {results['improvements']}")
        print(f"Neural Predictions: 🧠 {engine.neural_predictions_made:,}")
        print(f"Neural Success:     🎯 {engine.neural_improvements:,} improvements via neural guidance")
        print(f"Time Elapsed:       ⏱️  {results['total_time']:.1f} seconds")
        print(f"Speed:              🚀 {results['evals_per_second']:,.0f} evals/second")
        print(f"Cache Hit Rate:     💾 {results['cache_hit_rate']:.1f}%")
        print(f"Solved:             {'🎉 YES (IMPOSSIBLE!)' if results['solved'] else '❌ NO (Expected)'}")
        
        # Analysis
        baseline_random = 80  # Expected random performance
        improvement = baseline_random - results['best_score']
        
        print(f"\n🔬 ALGORITHM ANALYSIS:")
        print(f"   Best Performance:   {results['best_score']} bits from target")
        print(f"   vs Random Baseline: {improvement:+.1f} bits {'better' if improvement > 0 else 'worse'}")
        print(f"   Neural Contribution: {(engine.neural_improvements / max(1, results['improvements'])) * 100:.1f}% of improvements")
        
        if improvement > 5:
            speedup = 2**improvement
            print(f"   Effective Speedup:  ~{speedup:,.0f}× better than random")
        
        print(f"\n🧠 NEURAL NETWORK INSIGHTS:")
        print(f"   Pattern Memory:     {engine.neural_net.memory_ptr} patterns learned")
        print(f"   Learning Buffer:    {len(engine.learning_buffer)} samples pending")
        print(f"   Network Layers:     {config.NEURAL_LAYERS} transformer layers")
        print(f"   Attention Heads:    {config.NEURAL_HEADS} heads discovering bit correlations")
        
        print("="*100)
        print("🧠 NEURAL ENHANCEMENT: Shows how transformers learn cryptographic patterns!")
        print("⚠️  Bitcoin remains secure - demonstrates AI limits on cryptographic problems!")
        
        return results
        
    except Exception as e:
        print(f"💥 Neural Bitcoin search failed: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}


# Keep backward compatibility
def high_pressure_bitcoin_search(target_hash_hex: str, duration: float = 300.0):
    return neural_bitcoin_search(target_hash_hex, duration, population_size=10000)


# Example usage
print("✅ NEURAL-ENHANCED BITCOIN SEARCH ENGINE LOADED!")
print("\n🧠 USAGE:")
print("   neural_bitcoin_search('1234567890abcdef1234567890abcdef12345678', duration=60)")
print("   neural_bitcoin_search('target_hash', duration=300, population_size=5000)  # Faster startup")
print("\n🔑 KEY FORMAT:")
print("   ✅ Using UNCOMPRESSED public keys (65 bytes)")
print("   ✅ Compatible with Bitcoin puzzle addresses")
print("\n⚡ PERFORMANCE:")
print("   ✅ coincurve (libsecp256k1) for ~10x faster EC operations")
print("   ✅ Optimized CPU core usage for maximum speed")
print("   ✅ Smart caching system with performance tracking")
print("\n⚠️  SYSTEM RESOURCES:")
print("   ⚡ This will use optimized CPU cores")
print("   💾 Monitor memory usage with large populations")
print("   🔥 Consider cooling if running for extended periods")
print("\n🧠 NEURAL FEATURES:")
print("   ✅ Transformer-based hash pattern learning")
print("   ✅ Learns private key → hash160 transformation")
print("   ✅ Discovers bit correlations automatically")
print("   ✅ Predicts mutation success probability")
print("   ✅ Detects optimization barriers")
print("   ✅ Neural-guided hex position selection")
print("   ✅ Correlated bit group mutations")
print("   🔓 No hardcoded limits - learns from experience")
print("\n🔥 GENETIC FEATURES:")
print("   ✅ Population pressure (80% replacement)")
print("   ✅ Elite breeding system")
print("   ✅ Convergence acceleration")
print("   ✅ Adaptive bit weighting")
print("   ✅ PCA diversity injection")
print("   ✅ Covariance-based mutations")
print("\n⚠️  EDUCATIONAL DEMONSTRATION ONLY!")
print("⚠️  Shows how neural networks approach cryptographic problems!")
print("\n🚀 READY FOR NEURAL-ENHANCED BITCOIN SEARCH!")

# RUN IT NOW for demonstration:
if __name__ == "__main__":
    # Important for Windows multiprocessing
    mp.freeze_support()
    
    # Set deterministic seeds for reproducibility
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    
    print("\n🧠 Starting neural-enhanced Bitcoin search demonstration...")
    print("🔑 Using UNCOMPRESSED public keys for Bitcoin puzzle compatibility")
    # Use a random target hash for demonstration
    demo_target = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"
    results = neural_bitcoin_search(demo_target, duration=60, population_size=5000)  # Smaller for demo
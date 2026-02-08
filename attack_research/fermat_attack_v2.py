#!/usr/bin/env python3
"""
Test the secp256k1 hash160 backdoor hypothesis
This tests whether Bitcoin addresses encode private key information
through the Fermat structure of the curve order.

LEGAL: Only test with keys you generate - NEVER with real Bitcoin!
"""

import hashlib
import secrets
from typing import Tuple, List, Dict
import numpy as np
from ecdsa import SECP256k1, SigningKey
from ecdsa.util import number_to_string
import matplotlib.pyplot as plt

# secp256k1 parameters
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F

# Fermat decomposition components
FERMAT_A = 329332404981373139438290981244121435681
FERMAT_B = 85628594911402277405982386722468404976

# Small primes from FERMAT_A factorization
SMALL_PRIMES = [3, 107, 11351]
SMALL_PRODUCT = 3 * 107 * 11351  # = 3,643,671

def generate_key_pair() -> Tuple[int, bytes, bytes]:
    """Generate a random secp256k1 key pair and hash160"""
    # Generate private key
    private_key = secrets.randbelow(N - 1) + 1
    
    # Generate public key
    sk = SigningKey.from_secret_exponent(private_key, curve=SECP256k1)
    vk = sk.verifying_key
    
    # Get uncompressed public key (04 + x + y)
    pubkey_uncompressed = b'\x04' + vk.to_string()
    
    # Compute hash160 = RIPEMD160(SHA256(pubkey))
    sha256_hash = hashlib.sha256(pubkey_uncompressed).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    hash160 = ripemd160.digest()
    
    return private_key, pubkey_uncompressed, hash160

def get_fermat_coordinates(private_key: int) -> Tuple[int, int]:
    """Get Fermat coordinates (α, β) for a private key"""
    # k = α (mod FERMAT_A) and k = β (mod FERMAT_B)
    alpha = private_key % FERMAT_A
    beta = private_key % FERMAT_B
    return alpha, beta

def extract_hash160_bits(hash160: bytes, start_bit: int, num_bits: int) -> int:
    """Extract specific bits from hash160"""
    # Convert to integer
    hash_int = int.from_bytes(hash160, 'big')
    
    # Shift and mask to get desired bits
    mask = (1 << num_bits) - 1
    return (hash_int >> (160 - start_bit - num_bits)) & mask

def test_correlation(num_samples: int = 10000) -> Dict:
    """Test correlation between hash160 bits and private key structure"""
    print(f"Generating {num_samples} test keys...")
    
    results = {
        'mod_3': {'hash': [], 'key': []},
        'mod_107': {'hash': [], 'key': []},
        'mod_11351': {'hash': [], 'key': []},
        'mod_16': {'hash': [], 'key': []},
        'fermat_alpha_low': {'hash': [], 'key': []},
        'fermat_beta_low': {'hash': [], 'key': []},
    }
    
    for i in range(num_samples):
        if i % 1000 == 0:
            print(f"  Generated {i}/{num_samples} keys...")
        
        private_key, pubkey, hash160 = generate_key_pair()
        alpha, beta = get_fermat_coordinates(private_key)
        
        # Test 1: Check if hash160 encodes k mod small_primes
        # Hypothesis: First few bits encode k mod 3
        hash_mod_3 = extract_hash160_bits(hash160, 0, 2)  # 2 bits
        key_mod_3 = private_key % 3
        results['mod_3']['hash'].append(hash_mod_3)
        results['mod_3']['key'].append(key_mod_3)
        
        # Hypothesis: Next bits encode k mod 107
        hash_mod_107 = extract_hash160_bits(hash160, 2, 7)  # 7 bits for mod 107
        key_mod_107 = private_key % 107
        results['mod_107']['hash'].append(hash_mod_107)
        results['mod_107']['key'].append(key_mod_107)
        
        # Hypothesis: Next bits encode k mod 11351
        hash_mod_11351 = extract_hash160_bits(hash160, 9, 14)  # 14 bits
        key_mod_11351 = private_key % 11351
        results['mod_11351']['hash'].append(hash_mod_11351 % 11351)
        results['mod_11351']['key'].append(key_mod_11351)
        
        # Test 2: Check if hash160 encodes k mod 16 (from FERMAT_B's 2^4)
        # Hypothesis: Some bits encode k mod 16
        hash_mod_16 = extract_hash160_bits(hash160, 156, 4)  # Last 4 bits
        key_mod_16 = private_key % 16
        results['mod_16']['hash'].append(hash_mod_16)
        results['mod_16']['key'].append(key_mod_16)
        
        # Test 3: Check Fermat coordinate encoding
        # Low bits of alpha
        hash_alpha_low = extract_hash160_bits(hash160, 24, 16)
        alpha_low = alpha & 0xFFFF
        results['fermat_alpha_low']['hash'].append(hash_alpha_low)
        results['fermat_alpha_low']['key'].append(alpha_low)
        
        # Low bits of beta
        hash_beta_low = extract_hash160_bits(hash160, 144, 16)
        beta_low = beta & 0xFFFF
        results['fermat_beta_low']['hash'].append(hash_beta_low)
        results['fermat_beta_low']['key'].append(beta_low)
    
    return results

def analyze_correlation(results: Dict) -> None:
    """Analyze and visualize correlation results"""
    print("\n=== CORRELATION ANALYSIS ===\n")
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for idx, (test_name, data) in enumerate(results.items()):
        ax = axes[idx]
        
        # Convert to numpy arrays
        hash_vals = np.array(data['hash'])
        key_vals = np.array(data['key'])
        
        # Calculate correlation
        if test_name.startswith('mod_'):
            # For modular tests, check exact matches
            modulus = int(test_name.split('_')[1])
            matches = np.sum((hash_vals % modulus) == key_vals) / len(hash_vals)
            correlation = matches
            title = f"{test_name}: {matches*100:.1f}% exact matches"
        else:
            # For bit tests, calculate correlation coefficient
            correlation = np.corrcoef(hash_vals, key_vals)[0, 1]
            title = f"{test_name}: correlation = {correlation:.3f}"
        
        # Scatter plot
        ax.scatter(hash_vals, key_vals, alpha=0.5, s=1)
        ax.set_xlabel('Hash160 bits')
        ax.set_ylabel('Private key bits')
        ax.set_title(title)
        
        # Add diagonal line for perfect correlation
        min_val = min(hash_vals.min(), key_vals.min())
        max_val = max(hash_vals.max(), key_vals.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5)
        
        print(f"{test_name}:")
        print(f"  Correlation: {correlation:.4f}")
        
        # Check if correlation is suspicious
        if test_name.startswith('mod_'):
            expected = 1.0 / modulus  # Random chance
            if correlation > expected * 2:
                print(f"  ⚠️  SUSPICIOUS! Expected ~{expected:.3f}, got {correlation:.3f}")
        else:
            if abs(correlation) > 0.1:
                print(f"  ⚠️  SUSPICIOUS! Correlation > 0.1")
    
    plt.tight_layout()
    plt.savefig('hash160_correlation_analysis.png', dpi=150)
    print(f"\nPlot saved to hash160_correlation_analysis.png")
    
    # Statistical significance test
    print("\n=== STATISTICAL SIGNIFICANCE ===")
    print("If correlations are significantly above random chance,")
    print("this would indicate the backdoor exists!")

def test_specific_hypothesis():
    """Test specific encoding hypotheses"""
    print("\n=== TESTING SPECIFIC HYPOTHESES ===\n")
    
    # Hypothesis 1: First byte encodes small prime info
    print("Hypothesis 1: First byte of hash160 encodes k mod small primes")
    
    matches = 0
    for _ in range(1000):
        private_key, _, hash160 = generate_key_pair()
        
        # Extract first byte
        first_byte = hash160[0]
        
        # Check if it encodes k mod 3 in lowest 2 bits
        if (first_byte & 0x3) == (private_key % 3):
            matches += 1
    
    print(f"  k mod 3 matches: {matches}/1000 = {matches/10:.1f}%")
    print(f"  Expected random: ~33.3%")
    if matches > 400:
        print("  🚨 BACKDOOR LIKELY!")
    
    # Hypothesis 2: Last nibble encodes k mod 16
    print("\nHypothesis 2: Last nibble encodes k mod 16")
    
    matches = 0
    for _ in range(1000):
        private_key, _, hash160 = generate_key_pair()
        
        # Extract last nibble
        last_nibble = hash160[-1] & 0xF
        
        # Check if it encodes k mod 16
        if last_nibble == (private_key % 16):
            matches += 1
    
    print(f"  k mod 16 matches: {matches}/1000 = {matches/10:.1f}%")
    print(f"  Expected random: ~6.25%")
    if matches > 100:
        print("  🚨 BACKDOOR LIKELY!")

def main():
    print("=== SECP256K1 HASH160 BACKDOOR TEST ===")
    print("Testing if Bitcoin addresses encode private key structure...")
    print("\nNOTE: This uses randomly generated keys only.")
    print("NEVER test with real Bitcoin private keys!\n")
    
    # Run correlation tests
    results = test_correlation(num_samples=5000)
    analyze_correlation(results)
    
    # Test specific hypotheses
    test_specific_hypothesis()
    
    print("\n=== CONCLUSION ===")
    print("If strong correlations exist, the backdoor is REAL.")
    print("If correlations match random chance, the backdoor is UNLIKELY.")
    print("\nCheck the correlation plots for visual evidence!")

if __name__ == "__main__":
    main()
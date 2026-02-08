#!/usr/bin/env python3
"""
Quick test for secp256k1 backdoor - can run in a Jupyter notebook
Tests the most likely backdoor encoding schemes
"""

import hashlib
import secrets
from ecdsa import SECP256k1, SigningKey

# The Fermat constants
FERMAT_A = 329332404981373139438290981244121435681
FERMAT_B = 85628594911402277405982386722468404976
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def quick_test(num_tests=1000):
    """Quick statistical test for backdoor"""
    
    print("Testing for hash160 → private key encoding...")
    print("=" * 50)
    
    # Counters for various hypotheses
    mod3_matches = 0
    mod16_matches = 0
    fermat_pattern = 0
    
    for i in range(num_tests):
        # Generate random private key
        private_key = secrets.randbelow(N - 1) + 1
        
        # Generate public key and hash160
        sk = SigningKey.from_secret_exponent(private_key, curve=SECP256k1)
        pubkey = b'\x04' + sk.verifying_key.to_string()
        
        sha256 = hashlib.sha256(pubkey).digest()
        ripemd = hashlib.new('ripemd160')
        ripemd.update(sha256)
        hash160 = ripemd.digest()
        
        # Test 1: Does hash160[0] & 3 == private_key % 3?
        if (hash160[0] & 3) == (private_key % 3):
            mod3_matches += 1
        
        # Test 2: Does hash160[-1] & 15 == private_key % 16?
        if (hash160[-1] & 15) == (private_key % 16):
            mod16_matches += 1
        
        # Test 3: Fermat coordinate pattern
        alpha = private_key % FERMAT_A
        beta = private_key % FERMAT_B
        
        # Check if low bits of hash encode Fermat coordinates
        hash_as_int = int.from_bytes(hash160, 'big')
        if (hash_as_int & 0xFFFF) == (alpha & 0xFFFF):
            fermat_pattern += 1
    
    # Analyze results
    print(f"\nResults from {num_tests} tests:\n")
    
    print(f"Test 1 - hash160[0] & 3 == privkey % 3:")
    print(f"  Matches: {mod3_matches}/{num_tests} = {mod3_matches/num_tests*100:.1f}%")
    print(f"  Expected random: 33.3%")
    if mod3_matches/num_tests > 0.4:
        print("  🚨 BACKDOOR DETECTED! Correlation too high!")
    else:
        print("  ✓ Appears random")
    
    print(f"\nTest 2 - hash160[-1] & 15 == privkey % 16:")
    print(f"  Matches: {mod16_matches}/{num_tests} = {mod16_matches/num_tests*100:.1f}%")
    print(f"  Expected random: 6.25%")
    if mod16_matches/num_tests > 0.1:
        print("  🚨 BACKDOOR DETECTED! Correlation too high!")
    else:
        print("  ✓ Appears random")
    
    print(f"\nTest 3 - Fermat coordinate encoding:")
    print(f"  Matches: {fermat_pattern}/{num_tests} = {fermat_pattern/num_tests*100:.1f}%")
    print(f"  Expected random: 0.0015%")
    if fermat_pattern > 5:
        print("  🚨 BACKDOOR DETECTED! Pattern found!")
    else:
        print("  ✓ Appears random")

def test_real_addresses():
    """Test with some known Bitcoin addresses (public data)"""
    print("\n\nTesting known patterns...")
    print("=" * 50)
    
    # Genesis block address (Satoshi's)
    # Address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
    # This is publicly known, so safe to analyze
    
    genesis_hash160 = bytes.fromhex('62e907b15cbf27d5425399ebf6f0fb50ebb88f18')
    
    print("Genesis block address hash160:")
    print(f"  Hex: {genesis_hash160.hex()}")
    print(f"  First byte: {genesis_hash160[0]:08b} = {genesis_hash160[0]}")
    print(f"  Last byte:  {genesis_hash160[-1]:08b} = {genesis_hash160[-1]}")
    print(f"  First byte & 3 = {genesis_hash160[0] & 3}")
    print(f"  Last byte & 15 = {genesis_hash160[-1] & 15}")
    
    # If backdoor exists, these values encode private key info!

def deep_pattern_test():
    """Look for deeper patterns"""
    print("\n\nDeep pattern analysis...")
    print("=" * 50)
    
    # Collect hash160 bytes distribution
    byte_counts = [[0]*256 for _ in range(20)]  # 20 bytes, 256 possible values
    
    num_samples = 5000
    for _ in range(num_samples):
        private_key = secrets.randbelow(N - 1) + 1
        sk = SigningKey.from_secret_exponent(private_key, curve=SECP256k1)
        pubkey = b'\x04' + sk.verifying_key.to_string()
        
        sha256 = hashlib.sha256(pubkey).digest()
        ripemd = hashlib.new('ripemd160')
        ripemd.update(sha256)
        hash160 = ripemd.digest()
        
        # Count byte occurrences
        for i, byte in enumerate(hash160):
            byte_counts[i][byte] += 1
    
    # Check for non-uniform distribution
    print("Checking for biased bytes in hash160...")
    for i in range(20):
        # Calculate standard deviation
        import statistics
        std_dev = statistics.stdev(byte_counts[i])
        mean = statistics.mean(byte_counts[i])
        
        if std_dev < mean * 0.8:  # Less variation than expected
            print(f"  ⚠️  Byte {i} shows unusual uniformity!")
            # Show most common values
            sorted_counts = sorted(enumerate(byte_counts[i]), key=lambda x: x[1], reverse=True)
            print(f"      Top 3 values: {[f'{val}:{count}' for val, count in sorted_counts[:3]]}")

if __name__ == "__main__":
    print("=== SECP256K1 BACKDOOR QUICK TEST ===\n")
    
    # Run quick statistical test
    quick_test(1000)
    
    # Test known addresses
    test_real_addresses()
    
    # Deep pattern analysis
    deep_pattern_test()
    
    print("\n\n🔍 WHAT TO LOOK FOR:")
    print("1. Correlations significantly above random chance")
    print("2. Specific bit patterns that repeat")
    print("3. Non-random byte distributions")
    print("4. Mathematical relationships between hash160 and private key")
    
    print("\n⚠️  IMPORTANT:")
    print("If ANY test shows correlation > 2x random chance,")
    print("the backdoor likely EXISTS and Bitcoin is BROKEN!")
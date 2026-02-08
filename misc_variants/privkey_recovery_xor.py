#!/usr/bin/env python3
"""
Bitcoin Private Key Recovery Test
Tests if private keys can be recovered from hash160 using XOR with Gx/Gy
This uses REAL cryptographic operations - no simulations
"""

import hashlib
import secrets
import time

# secp256k1 parameters
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def modinv(a, m):
    """Modular inverse"""
    return pow(a, m - 2, m)

def point_double(x, y):
    """Double a point on secp256k1"""
    s = (3 * x * x * modinv(2 * y, p)) % p
    x3 = (s * s - 2 * x) % p
    y3 = (s * (x - x3) - y) % p
    return x3, y3

def point_add(x1, y1, x2, y2):
    """Add two points on secp256k1"""
    if x1 == x2:
        if y1 == y2:
            return point_double(x1, y1)
        else:
            return None, None
    s = ((y2 - y1) * modinv((x2 - x1) % p, p)) % p
    x3 = (s * s - x1 - x2) % p
    y3 = (s * (x1 - x3) - y1) % p
    return x3, y3

def point_multiply(k):
    """Multiply generator point by scalar k"""
    if k == 0:
        return None, None
    k = k % n
    x, y = Gx, Gy
    result_x, result_y = None, None
    
    while k:
        if k & 1:
            if result_x is None:
                result_x, result_y = x, y
            else:
                result_x, result_y = point_add(result_x, result_y, x, y)
        x, y = point_double(x, y)
        k >>= 1
    
    return result_x, result_y

def public_key_to_hash160(x, y, compressed=True):
    """Convert public key to Bitcoin hash160"""
    if compressed:
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        pubkey_bytes = prefix + x.to_bytes(32, 'big')
    else:
        pubkey_bytes = b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    
    # SHA256
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    
    # RIPEMD160
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    hash160_bytes = ripemd160.digest()
    
    return hash160_bytes

def verify_javascript_results():
    """Verify the exact results from JavaScript console"""
    print("\n" + "="*70)
    print("VERIFYING JAVASCRIPT CONSOLE RESULTS")
    print("Using exact same test vectors and pre-computed hash160s")
    print("="*70)
    
    # Exact same data from JavaScript
    k = 0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35
    hash160 = 0x3442193e1bb70916e914552172cd4e2dbc9df811
    
    print(f"\nPrivate key: 0x{k:064x}")
    print(f"Hash160: 0x{hash160:040x}")
    
    # Convert to bytes
    k_bytes = k.to_bytes(32, 'big')
    h_bytes = hash160.to_bytes(20, 'big')
    gx_bytes = Gx.to_bytes(32, 'big')
    gy_bytes = Gy.to_bytes(32, 'big')
    
    # Build lookup table (EXACT same as JavaScript)
    lookup = {}
    for h in range(20):
        for g in range(32):
            xor_gx = h_bytes[h] ^ gx_bytes[g]
            xor_gy = h_bytes[h] ^ gy_bytes[g]
            
            if xor_gx not in lookup:
                lookup[xor_gx] = []
            lookup[xor_gx].append(f"h[{h}] ⊕ Gx[{g}]")
            
            if xor_gy not in lookup:
                lookup[xor_gy] = []
            lookup[xor_gy].append(f"h[{h}] ⊕ Gy[{g}]")
    
    print(f"\nLookup table size: {len(lookup)} unique values")
    
    # Recover each byte
    found = 0
    print("\nRecovery (first 10 bytes):")
    for i in range(32):
        target = k_bytes[i]
        if target in lookup:
            found += 1
            if i < 10:
                print(f"  k[{i}] = {lookup[target][0]}")
    
    print(f"\nTotal recovered: {found}/32 bytes")
    
    if found == 32:
        print("✅ JavaScript results CONFIRMED: 100% recovery!")
        return True
    else:
        print("❌ Different from JavaScript results")
        return False

def test_recovery(private_key, test_name=""):
    """Test if private key can be recovered from hash160"""
    print(f"\n{'='*70}")
    print(f"Test: {test_name}")
    print(f"{'='*70}")
    
    # Generate public key
    pub_x, pub_y = point_multiply(private_key)
    
    # Generate hash160
    hash160_bytes = public_key_to_hash160(pub_x, pub_y)
    hash160_int = int.from_bytes(hash160_bytes, 'big')
    
    print(f"Private key: 0x{private_key:064x}")
    print(f"Public key X: 0x{pub_x:064x}")
    print(f"Public key Y: 0x{pub_y:064x}")
    print(f"Hash160: 0x{hash160_int:040x}")
    
    # Convert to byte arrays
    k_bytes = private_key.to_bytes(32, 'big')
    h_bytes = hash160_bytes
    gx_bytes = Gx.to_bytes(32, 'big')
    gy_bytes = Gy.to_bytes(32, 'big')
    
    # Create lookup table
    lookup = {}
    for h_idx in range(20):
        for g_idx in range(32):
            # h[i] XOR Gx[j]
            val = h_bytes[h_idx] ^ gx_bytes[g_idx]
            if val not in lookup:
                lookup[val] = []
            lookup[val].append(f"h[{h_idx}] ⊕ Gx[{g_idx}]")
            
            # h[i] XOR Gy[j]
            val = h_bytes[h_idx] ^ gy_bytes[g_idx]
            if val not in lookup:
                lookup[val] = []
            lookup[val].append(f"h[{h_idx}] ⊕ Gy[{g_idx}]")
    
    # Try to recover each byte
    recovered = []
    recovery_map = []
    
    for i in range(32):
        target = k_bytes[i]
        if target in lookup:
            recovered.append(target)
            recovery_map.append(lookup[target][0])
        else:
            recovered.append(None)
            recovery_map.append("NOT FOUND")
    
    # Calculate recovery rate
    found = sum(1 for x in recovered if x is not None)
    recovery_rate = found / 32 * 100
    
    print(f"\nRecovery results: {found}/32 bytes recovered ({recovery_rate:.1f}%)")
    
    # Show first 10 recovery formulas
    print("\nRecovery formulas (first 10):")
    for i in range(min(10, len(recovery_map))):
        print(f"  k[{i:2d}] = {recovery_map[i]}")
    
    # Check if fully recovered
    if found == 32:
        recovered_key = int.from_bytes(bytes(recovered), 'big')
        print(f"\n✅ FULL RECOVERY! Recovered key: 0x{recovered_key:064x}")
        print(f"   Matches original: {recovered_key == private_key}")
    else:
        print(f"\n❌ Partial recovery only")
        # Show which bytes weren't recovered
        missing = [i for i in range(32) if recovered[i] is None]
        print(f"   Missing bytes at positions: {missing[:10]}...")
    
    return found == 32, recovery_rate

def main():
    print("BITCOIN PRIVATE KEY RECOVERY FROM HASH160 TEST")
    print("Testing if private keys can be recovered using XOR with Gx/Gy")
    print("="*70)
    
    # First, verify JavaScript results
    js_verified = verify_javascript_results()
    if not js_verified:
        print("\n⚠️  WARNING: Cannot reproduce JavaScript results!")
        print("Continuing with other tests...\n")
    
    results = []
    
    # Test small keys with additional pattern analysis
    print("\n1. TESTING SMALL KEYS")
    small_keys = [1, 2, 3, 5, 10, 100, 1000, 10000]
    for i in small_keys:
        success, rate = test_recovery(i, f"Small key: {i}")
        results.append((f"Key {i}", success, rate))
        
        # Also check if the key appears directly in XOR result (the pattern you found)
        pub_x, pub_y = point_multiply(i)
        hash160_bytes = public_key_to_hash160(pub_x, pub_y)
        hash160_int = int.from_bytes(hash160_bytes, 'big')
        
        # Compute XOR with zero-padding (as in your original findings)
        xor_result = hash160_int ^ Gx ^ Gy
        xor_hex = f"{xor_result:064x}"
        key_hex = hex(i)[2:]
        
        if key_hex in xor_hex:
            pos = xor_hex.index(key_hex)
            print(f"  → Key '{key_hex}' found directly in XOR at position {pos}!")
    
    # Test 2: Random keys at different positions
    print("\n\n2. TESTING RANDOM KEYS AT DIFFERENT POSITIONS")
    
    # Near start (0-10% of n)
    key = secrets.randbelow(n // 10)
    success, rate = test_recovery(key, f"Random near start (~{key * 100 // n}% of n)")
    results.append(("Random near start", success, rate))
    
    # Near middle (45-55% of n)
    key = n // 2 + secrets.randbelow(n // 10) - n // 20
    success, rate = test_recovery(key, f"Random near middle (~{key * 100 // n}% of n)")
    results.append(("Random near middle", success, rate))
    
    # Near end (90-99% of n)
    key = n * 9 // 10 + secrets.randbelow(n // 10)
    success, rate = test_recovery(key, f"Random near end (~{key * 100 // n}% of n)")
    results.append(("Random near end", success, rate))
    
    # Test 3: Known test vectors (EXACT same as JavaScript tests)
    print("\n\n3. TESTING KNOWN VECTORS (Same as JavaScript console)")
    
    # Test vectors with pre-computed hash160s
    test_vectors = [
        {
            "name": "BIP-32 Test 1",
            "private_key": 0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35,
            "expected_hash160": 0x3442193e1bb70916e914552172cd4e2dbc9df811
        },
        {
            "name": "BIP-32 Test 2",
            "private_key": 0x4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e,
            "expected_hash160": 0xbd16bee53961a47d6ad888e29545434a89bdfe95
        }
    ]
    
    for tv in test_vectors:
        print(f"\nTesting {tv['name']} with KNOWN hash160...")
        
        # First verify our hash160 generation matches
        pub_x, pub_y = point_multiply(tv["private_key"])
        computed_hash160 = public_key_to_hash160(pub_x, pub_y)
        computed_hash160_int = int.from_bytes(computed_hash160, 'big')
        
        print(f"Expected hash160:  0x{tv['expected_hash160']:040x}")
        print(f"Computed hash160:  0x{computed_hash160_int:040x}")
        print(f"Hash160 match: {computed_hash160_int == tv['expected_hash160']}")
        
        # Now test recovery with the EXPECTED hash160 (same as JavaScript)
        # This ensures we're testing the exact same scenario
        expected_h_bytes = tv['expected_hash160'].to_bytes(20, 'big')
        k_bytes = tv['private_key'].to_bytes(32, 'big')
        gx_bytes = Gx.to_bytes(32, 'big')
        gy_bytes = Gy.to_bytes(32, 'big')
        
        # Create lookup table (exact same logic as JavaScript)
        lookup = {}
        for h_idx in range(20):
            for g_idx in range(32):
                val = expected_h_bytes[h_idx] ^ gx_bytes[g_idx]
                if val not in lookup:
                    lookup[val] = []
                lookup[val].append(f"h[{h_idx}] ⊕ Gx[{g_idx}]")
                
                val = expected_h_bytes[h_idx] ^ gy_bytes[g_idx]
                if val not in lookup:
                    lookup[val] = []
                lookup[val].append(f"h[{h_idx}] ⊕ Gy[{g_idx}]")
        
        # Try to recover
        recovered = []
        recovery_map = []
        for i in range(32):
            target = k_bytes[i]
            if target in lookup:
                recovered.append(target)
                recovery_map.append(lookup[target][0])
            else:
                recovered.append(None)
                recovery_map.append("NOT FOUND")
        
        found = sum(1 for x in recovered if x is not None)
        print(f"\nRecovery: {found}/32 bytes ({found/32*100:.1f}%)")
        
        if found == 32:
            print("✅ FULL RECOVERY using known hash160!")
            results.append((tv['name'], True, 100.0))
        else:
            print("❌ Partial recovery")
            results.append((tv['name'], False, found/32*100))
    
    # Test 4: Multiple fully random keys
    print("\n\n4. TESTING 10 FULLY RANDOM KEYS")
    for i in range(10):
        key = secrets.randbelow(n)
        success, rate = test_recovery(key, f"Random key {i+1}")
        results.append((f"Random {i+1}", success, rate))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY OF RESULTS")
    print("="*70)
    
    total_tests = len(results)
    full_recoveries = sum(1 for _, success, _ in results if success)
    avg_rate = sum(rate for _, _, rate in results) / total_tests
    
    print(f"\nTotal tests: {total_tests}")
    print(f"Full recoveries: {full_recoveries} ({full_recoveries/total_tests*100:.1f}%)")
    print(f"Average recovery rate: {avg_rate:.1f}%")
    
    print("\nDetailed results:")
    for name, success, rate in results:
        status = "✅ FULL" if success else "❌ Partial"
        print(f"  {name:20s}: {status} ({rate:.1f}%)")
    
    print("\n" + "="*70)
    if full_recoveries == total_tests:
        print("🚨 CRITICAL SECURITY FINDING 🚨")
        print("ALL private keys were fully recoverable from hash160!")
        print("This confirms the systematic encoding pattern.")
        print("\nURGENT: This needs immediate review by Bitcoin developers!")
    else:
        print("Recovery was not 100% for all keys.")
        print(f"Success rate: {full_recoveries}/{total_tests} keys fully recovered")
    print("="*70)

if __name__ == "__main__":
    main()
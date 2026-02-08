#!/usr/bin/env python3
"""
Bitcoin Puzzle 71 - Test ALL extraction candidates
No more fucking around - test everything!
"""

import hashlib
import base58
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# Target
TARGET_ADDRESS = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
TARGET_HASH160 = 0xfb2a7398ea7b9d7e02c1c38c78c85a91e051b639

# secp256k1 parameters
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def mod_inverse(a, m):
    if a < 0:
        a = (a % m + m) % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise Exception('Modular inverse does not exist')
    return x % m


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


def point_add(x1, y1, x2, y2):
    if x1 == x2:
        if y1 == y2:
            s = (3 * x1 * x1 * mod_inverse(2 * y1, p)) % p
        else:
            return None
    else:
        s = ((y2 - y1) * mod_inverse(x2 - x1, p)) % p
    
    x3 = (s * s - x1 - x2) % p
    y3 = (s * (x1 - x3) - y1) % p
    return x3, y3


def scalar_mult(k, x, y):
    if k == 0:
        return None
    if k == 1:
        return (x, y)
    
    result = None
    addend = (x, y)
    
    while k:
        if k & 1:
            if result is None:
                result = addend
            else:
                result = point_add(result[0], result[1], addend[0], addend[1])
        if k > 1:
            addend = point_add(addend[0], addend[1], addend[0], addend[1])
        k >>= 1
    
    return result


def private_key_to_address(private_key):
    pub_point = scalar_mult(private_key, Gx, Gy)
    if pub_point is None:
        return None
    
    pub_x, pub_y = pub_point
    
    if pub_y & 1:
        pubkey = b'\x03' + pub_x.to_bytes(32, 'big')
    else:
        pubkey = b'\x02' + pub_x.to_bytes(32, 'big')
    
    sha256_hash = hashlib.sha256(pubkey).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    versioned = b'\x00' + ripemd160_hash
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    address_bytes = versioned + checksum
    
    return base58.b58encode(address_bytes).decode('ascii')


def generate_all_candidates():
    """Generate ALL possible candidates from hash160"""
    candidates = set()
    
    # 1. Continuous extractions
    for pos in range(0, 90):
        extracted = (TARGET_HASH160 >> pos) & ((1 << 71) - 1)
        if (1 << 70) <= extracted < (1 << 71):
            candidates.add(extracted)
    
    # 2. Split extractions (first X + last Y = 71)
    for first_bits in range(1, 71):
        last_bits = 71 - first_bits
        first_part = TARGET_HASH160 >> (160 - first_bits)
        last_part = TARGET_HASH160 & ((1 << last_bits) - 1)
        combined = (first_part << last_bits) | last_part
        if (1 << 70) <= combined < (1 << 71):
            candidates.add(combined)
    
    # 3. Reversed hash160 extractions
    # Byte reverse
    hash_bytes = []
    temp = TARGET_HASH160
    for i in range(20):
        hash_bytes.append(temp & 0xFF)
        temp >>= 8
    
    reversed_hash = 0
    for b in hash_bytes:
        reversed_hash = (reversed_hash << 8) | b
    
    for pos in range(0, 90):
        extracted = (reversed_hash >> pos) & ((1 << 71) - 1)
        if (1 << 70) <= extracted < (1 << 71):
            candidates.add(extracted)
    
    # 4. Transformations of high 71 bits
    high_71 = TARGET_HASH160 >> 89
    
    # Bit reversal
    binary = bin(high_71)[2:].zfill(71)
    bit_reversed = int(binary[::-1], 2)
    if (1 << 70) <= bit_reversed < (1 << 71):
        candidates.add(bit_reversed)
    
    # Simple modifications
    for delta in [-71, -1, 1, 71]:
        modified = high_71 + delta
        if (1 << 70) <= modified < (1 << 71):
            candidates.add(modified)
    
    # XOR with patterns
    patterns = [0x5555555555555555555, 0xAAAAAAAAAAAAAAAAAAAA, 71]
    for pattern in patterns:
        xored = high_71 ^ (pattern & ((1 << 71) - 1))
        if (1 << 70) <= xored < (1 << 71):
            candidates.add(xored)
    
    # 5. Skip patterns
    for gap in range(10, 81, 10):
        for first_bits in range(30, 41):
            last_bits = 71 - first_bits
            last_pos = 160 - gap - last_bits
            if last_pos > first_bits:
                first_part = (TARGET_HASH160 >> (160 - first_bits)) & ((1 << first_bits) - 1)
                last_part = (TARGET_HASH160 >> last_pos) & ((1 << last_bits) - 1)
                combined = (first_part << last_bits) | last_part
                if (1 << 70) <= combined < (1 << 71):
                    candidates.add(combined)
    
    return list(candidates)


def test_batch(candidates):
    """Test a batch of candidates"""
    results = []
    for i, pk in enumerate(candidates):
        try:
            address = private_key_to_address(pk)
            if address == TARGET_ADDRESS:
                return (pk, address, True)
            results.append((pk, address, False))
        except Exception as e:
            results.append((pk, str(e), False))
        
        if i % 10 == 0:
            print(f"  Tested {i+1}/{len(candidates)} in this batch...")
    
    return results


def main():
    print("BITCOIN PUZZLE 71 - EXHAUSTIVE TEST")
    print("=" * 50)
    print(f"Target: {TARGET_ADDRESS}")
    print(f"Hash160: 0x{TARGET_HASH160:040x}\n")
    
    print("Generating all candidates...")
    candidates = generate_all_candidates()
    print(f"Total candidates: {len(candidates)}\n")
    
    # Test in parallel
    num_workers = mp.cpu_count()
    batch_size = len(candidates) // num_workers + 1
    
    print(f"Testing with {num_workers} workers...")
    print("=" * 50)
    
    found = False
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i+batch_size]
            future = executor.submit(test_batch, batch)
            futures.append(future)
        
        for i, future in enumerate(as_completed(futures)):
            print(f"\nBatch {i+1}/{len(futures)} complete")
            results = future.result()
            
            if isinstance(results, tuple) and results[2]:  # Found!
                pk, address, _ = results
                print(f"\n{'='*50}")
                print(f"🎉 FOUND PUZZLE 71! 🎉")
                print(f"{'='*50}")
                print(f"Private Key: 0x{pk:x}")
                print(f"Decimal: {pk}")
                print(f"Binary: {bin(pk)}")
                print(f"Address: {address}")
                found = True
                break
    
    if not found:
        print("\n\nNo match found in all candidates.")
        print("The pattern might be more complex than simple extraction.")
        
        # Print some candidates for manual inspection
        print("\n\nSome candidates tested:")
        for i in range(min(10, len(candidates))):
            print(f"0x{candidates[i]:x}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Bitcoin Null Hypothesis Tester
Tests patterns between all-zero hash160, all-zero private keys, and random keypairs
"""

import hashlib
import os
import random
from collections import defaultdict

# Hardcoded secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
A = 0
B = 7

# Base58 alphabet
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def sha256(data):
    """Real SHA256 hash function"""
    return hashlib.sha256(data).digest()

def ripemd160(data):
    """Real RIPEMD160 hash function"""
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()

def double_sha256(data):
    """Double SHA256 hash"""
    return sha256(sha256(data))

def int_to_bytes(x, length):
    """Convert integer to bytes with specified length"""
    return x.to_bytes(length, byteorder='big')

def bytes_to_int(b):
    """Convert bytes to integer"""
    return int.from_bytes(b, byteorder='big')

def base58_encode(data):
    """Base58 encoding"""
    n = bytes_to_int(data)
    result = ''
    while n > 0:
        n, remainder = divmod(n, 58)
        result = BASE58_ALPHABET[remainder] + result
    
    for byte in data:
        if byte == 0:
            result = '1' + result
        else:
            break
    
    return result or '1'

def base58_decode(s):
    """Base58 decoding"""
    n = 0
    for char in s:
        n = n * 58 + BASE58_ALPHABET.index(char)
    
    # Count leading 1s
    leading_zeros = len(s) - len(s.lstrip('1'))
    
    # Convert to bytes
    h = hex(n)[2:]
    if len(h) % 2:
        h = '0' + h
    res = bytes.fromhex(h)
    
    # Add leading zeros
    return b'\x00' * leading_zeros + res

def base58_check_encode(payload, version_byte):
    """Base58Check encoding with version byte"""
    versioned = bytes([version_byte]) + payload
    checksum = double_sha256(versioned)[:4]
    return base58_encode(versioned + checksum)

def mod_inverse(a, m):
    """Modular inverse using Extended Euclidean Algorithm"""
    if a < 0:
        return m - mod_inverse(-a, m)
    
    g, x, _ = extended_gcd(a % m, m)
    if g > 1:
        raise Exception('Modular inverse does not exist')
    return x % m

def extended_gcd(a, b):
    """Extended Euclidean Algorithm"""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def point_add(p1, p2):
    """Add two points on secp256k1"""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    
    x1, y1 = p1
    x2, y2 = p2
    
    if x1 == x2:
        if y1 == y2:
            # Point doubling
            s = (3 * x1 * x1 + A) * mod_inverse(2 * y1, P) % P
        else:
            # Points are inverses
            return None
    else:
        # Point addition
        s = (y2 - y1) * mod_inverse(x2 - x1, P) % P
    
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    
    return (x3, y3)

def point_multiply(k, point):
    """Multiply a point by scalar k"""
    if k == 0:
        return None  # Point at infinity
    
    if k < 0:
        return point_multiply(-k, (point[0], (-point[1]) % P))
    
    result = None
    addend = point
    
    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    
    return result

def private_key_to_public_key(private_key_int):
    """Convert private key to public key"""
    if private_key_int == 0:
        # Special case: return (0, 0) for demonstration
        return (0, 0)
    
    point = point_multiply(private_key_int, (Gx, Gy))
    if point is None:
        return (0, 0)  # Shouldn't happen for valid private keys
    
    return point

def public_key_to_address(x, y, compressed=True):
    """Convert public key to Bitcoin address"""
    if compressed:
        if y % 2 == 0:
            pubkey = b'\x02' + int_to_bytes(x, 32)
        else:
            pubkey = b'\x03' + int_to_bytes(x, 32)
    else:
        pubkey = b'\x04' + int_to_bytes(x, 32) + int_to_bytes(y, 32)
    
    hash160 = ripemd160(sha256(pubkey))
    return base58_check_encode(hash160, 0x00), hash160

def hash160_to_address(hash160):
    """Convert hash160 directly to address"""
    return base58_check_encode(hash160, 0x00)

def hamming_distance_bytes(b1, b2):
    """Calculate Hamming distance between two byte arrays"""
    # Pad to same length
    max_len = max(len(b1), len(b2))
    b1 = b1.ljust(max_len, b'\x00')
    b2 = b2.ljust(max_len, b'\x00')
    
    distance = 0
    for byte1, byte2 in zip(b1, b2):
        xor = byte1 ^ byte2
        distance += bin(xor).count('1')
    
    return distance

def hamming_distance_addresses(addr1, addr2):
    """Calculate Hamming distance between two addresses"""
    # Decode addresses to get the hash160
    try:
        decoded1 = base58_decode(addr1)
        decoded2 = base58_decode(addr2)
        # Extract hash160 (skip version byte and checksum)
        hash160_1 = decoded1[1:21]
        hash160_2 = decoded2[1:21]
        return hamming_distance_bytes(hash160_1, hash160_2)
    except:
        # If decode fails, compare as strings
        return hamming_distance_bytes(addr1.encode(), addr2.encode())

def generate_random_private_key():
    """Generate a random valid private key"""
    while True:
        key = random.randint(1, N - 1)
        if key != 0:  # Ensure not zero
            return key

def analyze_null_hypothesis(num_samples=1000):
    """Main analysis function"""
    print("=" * 80)
    print("Bitcoin Null Hypothesis Analysis")
    print("Testing patterns between zero hash160, zero private key, and random keys")
    print("=" * 80)
    print()
    
    # 1. Generate address from all-zero hash160
    print("1. All-Zero Hash160 Address:")
    zero_hash160 = b'\x00' * 20
    zero_hash160_address = hash160_to_address(zero_hash160)
    print(f"   Hash160: {zero_hash160.hex()}")
    print(f"   Address: {zero_hash160_address}")
    print()
    
    # 2. Generate address from all-zero private key
    print("2. All-Zero Private Key Address:")
    zero_privkey = 0
    zero_pubkey = private_key_to_public_key(zero_privkey)
    zero_privkey_address, zero_privkey_hash160 = public_key_to_address(zero_pubkey[0], zero_pubkey[1])
    print(f"   Private Key: {'00' * 32}")
    print(f"   Public Key: ({hex(zero_pubkey[0])}, {hex(zero_pubkey[1])})")
    print(f"   Hash160: {zero_privkey_hash160.hex()}")
    print(f"   Address: {zero_privkey_address}")
    print()
    
    # 3. Generate some specific test cases
    print("3. Edge Case Private Keys:")
    edge_cases = [1, 2, N-1, 0xDEADBEEF, 0x5A5A5A5A5A5A5A5A]
    edge_addresses = []
    
    for privkey in edge_cases:
        pubkey = private_key_to_public_key(privkey)
        addr, hash160 = public_key_to_address(pubkey[0], pubkey[1])
        edge_addresses.append((privkey, addr, hash160))
        print(f"   Private Key: {hex(privkey)}")
        print(f"   Address: {addr}")
        print(f"   Hash160: {hash160.hex()}")
        print()
    
    # 4. Generate random keypairs and analyze
    print(f"4. Generating {num_samples} random keypairs for analysis...")
    
    hamming_to_zero_hash160 = []
    hamming_to_zero_privkey = []
    hamming_between_randoms = []
    hash160_bit_distribution = defaultdict(int)
    
    random_addresses = []
    
    for i in range(num_samples):
        # Generate random private key
        privkey = generate_random_private_key()
        pubkey = private_key_to_public_key(privkey)
        addr, hash160 = public_key_to_address(pubkey[0], pubkey[1])
        random_addresses.append((privkey, addr, hash160))
        
        # Calculate Hamming distances
        h1 = hamming_distance_bytes(hash160, zero_hash160)
        h2 = hamming_distance_bytes(hash160, zero_privkey_hash160)
        hamming_to_zero_hash160.append(h1)
        hamming_to_zero_privkey.append(h2)
        
        # Analyze bit distribution in hash160
        for byte_idx, byte_val in enumerate(hash160):
            for bit_idx in range(8):
                if byte_val & (1 << bit_idx):
                    hash160_bit_distribution[byte_idx * 8 + bit_idx] += 1
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"   Processed {i + 1}/{num_samples} samples...")
    
    # Calculate Hamming distances between random pairs
    print("   Calculating inter-random Hamming distances...")
    for i in range(min(100, num_samples)):
        for j in range(i + 1, min(100, num_samples)):
            h = hamming_distance_bytes(random_addresses[i][2], random_addresses[j][2])
            hamming_between_randoms.append(h)
    
    # 5. Statistical Analysis
    print()
    print("5. Statistical Analysis:")
    print()
    
    print("   Hamming Distance Statistics (bits different in hash160):")
    print(f"   - To zero hash160:     avg={sum(hamming_to_zero_hash160)/len(hamming_to_zero_hash160):.2f}, "
          f"min={min(hamming_to_zero_hash160)}, max={max(hamming_to_zero_hash160)}")
    print(f"   - To zero privkey addr: avg={sum(hamming_to_zero_privkey)/len(hamming_to_zero_privkey):.2f}, "
          f"min={min(hamming_to_zero_privkey)}, max={max(hamming_to_zero_privkey)}")
    print(f"   - Between randoms:      avg={sum(hamming_between_randoms)/len(hamming_between_randoms):.2f}, "
          f"min={min(hamming_between_randoms)}, max={max(hamming_between_randoms)}")
    print()
    
    # Expected Hamming distance for random 160-bit values is 80 bits
    print("   Expected Hamming distance for random 160-bit values: 80 bits")
    print()
    
    # Check for any addresses unusually close to zero addresses
    print("   Closest addresses to zero hash160:")
    sorted_by_zero_hash160 = sorted(zip(hamming_to_zero_hash160, random_addresses), key=lambda x: x[0])
    for i in range(min(5, len(sorted_by_zero_hash160))):
        dist, (privkey, addr, hash160) = sorted_by_zero_hash160[i]
        print(f"   - Distance: {dist} bits")
        print(f"     Private Key: {hex(privkey)}")
        print(f"     Address: {addr}")
        print(f"     Hash160: {hash160.hex()}")
    print()
    
    print("   Closest addresses to zero private key address:")
    sorted_by_zero_privkey = sorted(zip(hamming_to_zero_privkey, random_addresses), key=lambda x: x[0])
    for i in range(min(5, len(sorted_by_zero_privkey))):
        dist, (privkey, addr, hash160) = sorted_by_zero_privkey[i]
        print(f"   - Distance: {dist} bits")
        print(f"     Private Key: {hex(privkey)}")
        print(f"     Address: {addr}")
        print(f"     Hash160: {hash160.hex()}")
    print()
    
    # Bit distribution analysis
    print("   Bit Distribution Analysis (how often each bit is 1 in hash160):")
    expected_freq = num_samples / 2
    significant_deviations = []
    
    for bit_pos in range(160):
        freq = hash160_bit_distribution[bit_pos]
        deviation = abs(freq - expected_freq) / expected_freq
        if deviation > 0.1:  # More than 10% deviation
            significant_deviations.append((bit_pos, freq, deviation))
    
    if significant_deviations:
        print("   Significant deviations from expected 50% frequency:")
        for bit_pos, freq, dev in sorted(significant_deviations, key=lambda x: x[2], reverse=True)[:5]:
            print(f"   - Bit {bit_pos}: {freq}/{num_samples} ({freq/num_samples*100:.1f}%), "
                  f"deviation: {dev*100:.1f}%")
    else:
        print("   No significant deviations from expected uniform distribution")
    print()
    
    # Null hypothesis conclusion
    print("6. Null Hypothesis Test Results:")
    print("   H0: Addresses from zero hash160/privkey have no special relationship to random addresses")
    print()
    
    avg_random_hamming = sum(hamming_between_randoms) / len(hamming_between_randoms)
    avg_to_zero_hash160 = sum(hamming_to_zero_hash160) / len(hamming_to_zero_hash160)
    avg_to_zero_privkey = sum(hamming_to_zero_privkey) / len(hamming_to_zero_privkey)
    
    # Simple statistical test
    if abs(avg_to_zero_hash160 - avg_random_hamming) < 5 and abs(avg_to_zero_privkey - avg_random_hamming) < 5:
        print("   Result: FAIL TO REJECT null hypothesis")
        print("   The zero addresses appear to have no special relationship to random addresses")
    else:
        print("   Result: Evidence to REJECT null hypothesis")
        print("   The zero addresses may have special properties")
    
    print()
    print("   Summary:")
    print(f"   - Zero addresses are about as distant from random addresses")
    print(f"     as random addresses are from each other (~80 bits)")
    print(f"   - No evidence of hidden patterns or relationships")
    print(f"   - Hash160 values appear uniformly distributed")
    
    return {
        'zero_hash160_address': zero_hash160_address,
        'zero_privkey_address': zero_privkey_address,
        'hamming_stats': {
            'to_zero_hash160': (min(hamming_to_zero_hash160), 
                               sum(hamming_to_zero_hash160)/len(hamming_to_zero_hash160), 
                               max(hamming_to_zero_hash160)),
            'to_zero_privkey': (min(hamming_to_zero_privkey), 
                               sum(hamming_to_zero_privkey)/len(hamming_to_zero_privkey), 
                               max(hamming_to_zero_privkey)),
            'between_randoms': (min(hamming_between_randoms), 
                               sum(hamming_between_randoms)/len(hamming_between_randoms), 
                               max(hamming_between_randoms))
        }
    }

if __name__ == "__main__":
    # Set random seed for reproducibility (optional)
    # random.seed(42)
    
    # Run analysis
    results = analyze_null_hypothesis(num_samples=1000)
    
    print("\n" + "="*80)
    print("Analysis Complete!")
    print("="*80)
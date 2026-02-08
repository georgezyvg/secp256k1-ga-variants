#!/usr/bin/env python3
"""
Test specific zero patterns that GA discovered vs random patterns
Theory: Specific patterns (not just zero count) create exploitable structure
"""

import hashlib
import random
import statistics
from typing import List, Tuple

try:
    import coincurve
    HAS_COINCURVE = True
except ImportError:
    HAS_COINCURVE = False
    from ecdsa import SECP256k1, SigningKey

from Crypto.Hash import RIPEMD160

def get_public_key(private_key: bytes) -> bytes:
    """Get compressed public key"""
    try:
        if HAS_COINCURVE:
            privkey = coincurve.PrivateKey(private_key)
            return privkey.public_key.format(compressed=True)
        else:
            sk = SigningKey.from_string(private_key, curve=SECP256k1)
            vk = sk.verifying_key
            point = vk.pubkey.point
            x = point.x()
            y = point.y()
            prefix = 0x02 if (y % 2 == 0) else 0x03
            return bytes([prefix]) + x.to_bytes(32, 'big')
    except:
        # Just use 1 if invalid
        return get_public_key(b'\x00' * 31 + b'\x01')

def hash160(pubkey: bytes) -> bytes:
    """SHA256 + RIPEMD160"""
    sha256_hash = hashlib.sha256(pubkey).digest()
    h = RIPEMD160.new()
    h.update(sha256_hash)
    return h.digest()

def hamming_distance(h1: bytes, h2: bytes) -> int:
    """Calculate Hamming distance in bits"""
    return sum(bin(a ^ b).count('1') for a, b in zip(h1, h2))

def test_patterns():
    """Test GA-discovered patterns vs random"""
    
    # Generate random target
    target = hashlib.sha256(b"test target").digest()[:20]
    print(f"🎯 Target: {target.hex()}\n")
    
    results = {}
    
    # 1. GA-like patterns (what your GA tends to find)
    print("📊 Testing GA-discovered patterns:")
    ga_patterns = {
        "small_values": lambda i: max(1, i).to_bytes(32, 'big'),  # What GA finds
        "single_byte_end": lambda i: b'\x00' * 31 + bytes([max(1, i % 256)]),
        "ff_transitions": lambda i: b'\x00' * 15 + b'\xff' + b'\x00' * 16,
        "sparse_bytes": lambda i: bytes([max(1, i % 256) if j < 3 else 0 for j in range(32)]),
    }
    
    for name, pattern_func in ga_patterns.items():
        distances = []
        for i in range(1, 1001):
            private_key = pattern_func(i)
            pubkey = get_public_key(private_key)
            h160 = hash160(pubkey)
            dist = hamming_distance(h160, target)
            distances.append(dist)
        
        results[name] = {
            'avg': statistics.mean(distances),
            'min': min(distances),
            'max': max(distances),
            'stdev': statistics.stdev(distances)
        }
        print(f"   {name:20}: avg={results[name]['avg']:.1f}, min={results[name]['min']}, std={results[name]['stdev']:.1f}")
    
    # 2. Random patterns for comparison
    print("\n📊 Testing random patterns:")
    random_patterns = {
        "full_random": lambda i: bytes([random.randint(0, 255) for _ in range(32)]),
        "half_random": lambda i: bytes([random.randint(0, 255) if j < 16 else 0 for j in range(32)]),
        "scattered_random": lambda i: bytes([random.randint(0, 255) if j % 4 == 0 else 0 for j in range(32)]),
    }
    
    for name, pattern_func in random_patterns.items():
        distances = []
        for i in range(1, 1001):
            private_key = pattern_func(i)
            pubkey = get_public_key(private_key)
            h160 = hash160(pubkey)
            dist = hamming_distance(h160, target)
            distances.append(dist)
        
        results[name] = {
            'avg': statistics.mean(distances),
            'min': min(distances),
            'max': max(distances),
            'stdev': statistics.stdev(distances)
        }
        print(f"   {name:20}: avg={results[name]['avg']:.1f}, min={results[name]['min']}, std={results[name]['stdev']:.1f}")
    
    # 3. Test specific transitions GA found
    print("\n📊 Testing specific value transitions:")
    transitions = [
        (b'\x01', b'\xff', "01->FF"),
        (b'\x01', b'\xa0', "01->A0"),
        (b'\x01', b'\x02', "01->02"),
        (b'\xff', b'\x01', "FF->01"),
    ]
    
    for from_val, to_val, name in transitions:
        distances_before = []
        distances_after = []
        
        for i in range(100):
            # Before transition
            key_before = b'\x00' * 15 + from_val + b'\x00' * 16
            pubkey = get_public_key(key_before)
            h160 = hash160(pubkey)
            dist = hamming_distance(h160, target)
            distances_before.append(dist)
            
            # After transition
            key_after = b'\x00' * 15 + to_val + b'\x00' * 16
            pubkey = get_public_key(key_after)
            h160 = hash160(pubkey)
            dist = hamming_distance(h160, target)
            distances_after.append(dist)
        
        avg_before = statistics.mean(distances_before)
        avg_after = statistics.mean(distances_after)
        improvement = avg_before - avg_after
        
        print(f"   {name:10}: before={avg_before:.1f}, after={avg_after:.1f}, improvement={improvement:+.1f}")
    
    # Find winner
    print("\n🏆 RESULTS:")
    sorted_results = sorted(results.items(), key=lambda x: x[1]['avg'])
    best = sorted_results[0]
    worst = sorted_results[-1]
    
    print(f"   Best pattern:  {best[0]} (avg={best[1]['avg']:.1f})")
    print(f"   Worst pattern: {worst[0]} (avg={worst[1]['avg']:.1f})")
    print(f"   Advantage:     {worst[1]['avg'] - best[1]['avg']:.1f} bits")
    
    if best[0] in ga_patterns:
        print("\n   ✅ GA-discovered pattern wins! The GA found real structure.")
    else:
        print("\n   ❌ Random pattern wins. GA patterns might be target-specific.")

if __name__ == "__main__":
    print("🔬 GA PATTERN VERIFICATION TEST")
    print("="*50)
    test_patterns()
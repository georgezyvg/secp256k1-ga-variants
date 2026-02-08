#!/usr/bin/env python3
"""
Correct Private Key Recovery Test
Takes hash160, uses modular constraints to find private key candidates
"""

import hashlib
import secrets
from typing import List, Optional

try:
    import coincurve
    HAS_COINCURVE = True
except ImportError:
    from ecdsa import SECP256k1, SigningKey
    HAS_COINCURVE = False

from Crypto.Hash import RIPEMD160

class BitcoinCrypto:
    def __init__(self):
        self.use_coincurve = HAS_COINCURVE
        
    def private_key_to_public_key(self, private_key_bytes: bytes) -> bytes:
        if self.use_coincurve:
            privkey = coincurve.PrivateKey(private_key_bytes)
            return privkey.public_key.format(compressed=False)
        else:
            priv_int = int.from_bytes(private_key_bytes, 'big')
            if priv_int == 0 or priv_int >= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141:
                raise ValueError("Invalid private key")
            sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            vk = sk.verifying_key
            point = vk.pubkey.point
            x = point.x()
            y = point.y()
            x_bytes = x.to_bytes(32, 'big')
            y_bytes = y.to_bytes(32, 'big')
            return bytes([0x04]) + x_bytes + y_bytes
    
    def hash160(self, data: bytes) -> bytes:
        sha256_hash = hashlib.sha256(data).digest()
        h = RIPEMD160.new()
        h.update(sha256_hash)
        return h.digest()
    
    def private_key_to_hash160(self, private_key_bytes: bytes) -> bytes:
        pubkey = self.private_key_to_public_key(private_key_bytes)
        return self.hash160(pubkey)

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def chinese_remainder_theorem(remainders: List[int], moduli: List[int]) -> Optional[int]:
    """Solve system of modular equations"""
    if not remainders or not moduli or len(remainders) != len(moduli):
        return None
    
    total = 1
    for m in moduli:
        total *= m
    
    result = 0
    for r, m in zip(remainders, moduli):
        Mi = total // m
        gcd, x, y = extended_gcd(Mi, m)
        if gcd != 1:
            return None  # Not coprime
        yi = x % m
        result += r * Mi * yi
    
    return result % total

def crack_private_key_from_hash160(target_hash160_hex: str, crypto: BitcoinCrypto) -> Optional[bytes]:
    """
    COMPREHENSIVE ATTACK: Test all moduli under 1M with tolerance <100
    """
    target_hash160 = bytes.fromhex(target_hash160_hex)
    hash_int = int.from_bytes(target_hash160, 'big')
    
    print(f"🎯 TARGET: {target_hash160_hex}")
    print(f"Testing moduli 2 to 1,000,000 with tolerance <100...")
    
    max_mod = 1000000
    tolerance = 99
    max_candidates_per_mod = 1000  # Limit to keep it fast
    
    for mod in range(2, max_mod + 1):
        if mod % 50000 == 0:
            print(f"   Progress: testing mod {mod:,}...")
            
        hash_remainder = hash_int % mod
        candidates_tested = 0
        
        # Test offsets within tolerance
        for offset in range(-tolerance, tolerance + 1):
            if candidates_tested >= max_candidates_per_mod:
                break
                
            target_remainder = (hash_remainder + offset) % mod
            
            # Test a few multiples of this remainder
            for multiplier in range(0, 10):
                candidate_int = target_remainder + (multiplier * mod)
                
                if candidate_int <= 0:
                    continue
                if candidate_int >= 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141:
                    break
                
                candidates_tested += 1
                
                try:
                    candidate_key = candidate_int.to_bytes(32, 'big')
                    computed_hash160 = crypto.private_key_to_hash160(candidate_key)
                    
                    if computed_hash160 == target_hash160:
                        diff = abs((candidate_int % mod) - hash_remainder)
                        print(f"\n💀 BITCOIN IS COMPLETELY BROKEN! 💀")
                        print(f"Private key cracked using mod {mod}!")
                        print(f"Private key: {candidate_key.hex()}")
                        print(f"Modular relationship: priv%{mod}={candidate_int % mod}, hash%{mod}={hash_remainder}, diff={diff}")
                        return candidate_key
                        
                except Exception:
                    continue
    
    print(f"\n✅ Attack failed completely - Bitcoin appears cryptographically secure")
    return None

def run_attack_test():
    """Test the attack on a random key"""
    print("🔥 TESTING PRIVATE KEY RECOVERY ATTACK")
    print("="*60)
    
    crypto = BitcoinCrypto()
    
    # Generate random target
    true_privkey = secrets.randbits(255).to_bytes(32, 'big')
    target_hash160 = crypto.private_key_to_hash160(true_privkey)
    
    print(f"🎲 GENERATED RANDOM TARGET:")
    print(f"True private key: {true_privkey.hex()}")
    print(f"Target hash160: {target_hash160.hex()}")
    
    # Show actual modular relationships
    true_int = int.from_bytes(true_privkey, 'big')
    hash_int = int.from_bytes(target_hash160, 'big')
    print(f"\n📊 ACTUAL MODULAR RELATIONSHIPS:")
    for mod in [29, 62, 165, 45, 64]:
        priv_mod = true_int % mod
        hash_mod = hash_int % mod
        diff = abs(priv_mod - hash_mod)
        print(f"   mod {mod}: priv={priv_mod}, hash={hash_mod}, diff={diff}")
    
    print(f"\n" + "-"*60)
    
    # Attempt the attack
    recovered_key = crack_private_key_from_hash160(target_hash160.hex(), crypto)
    
    if recovered_key:
        success = (recovered_key == true_privkey)
        print(f"\n🎯 ATTACK RESULT: {'SUCCESS' if success else 'WRONG KEY'}")
        if success:
            print("💀 BITCOIN WOULD BE COMPLETELY BROKEN 💀")
        return success
    else:
        print(f"\n✅ ATTACK FAILED - Bitcoin appears secure")
        return False

if __name__ == "__main__":
    success = run_attack_test()
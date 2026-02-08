#!/usr/bin/env python3
"""
Mt. Gox Key Compression Tester
Tests both compressed and uncompressed key formats with various hashing methods
"""

import hashlib
import base58
import binascii
from typing import List, Tuple
import time

class MtGoxKeyTester:
    def __init__(self):
        self.target_address = "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF"
        self.secp256k1_params = {
            'p': 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F,
            'n': 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
            'g': (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
                  0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
        }
    
    def sha256(self, data: bytes) -> bytes:
        """Standard SHA256"""
        return hashlib.sha256(data).digest()
    
    def sha256d(self, data: bytes) -> bytes:
        """Double SHA256 (Bitcoin standard)"""
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
    
    def sha256_concat(self, data: bytes) -> bytes:
        """SHA256 with concatenation method"""
        # Try different concatenation approaches
        hash1 = hashlib.sha256(data).digest()
        hash2 = hashlib.sha256(data + hash1).digest()
        return hash2
    
    def ripemd160(self, data: bytes) -> bytes:
        """RIPEMD160 hash"""
        import hashlib
        return hashlib.new('ripemd160', data).digest()
    
    def mod_inverse(self, a: int, m: int) -> int:
        """Modular inverse using extended Euclidean algorithm"""
        if a < 0:
            a = (a % m + m) % m
        g, x, _ = self.extended_gcd(a, m)
        if g != 1:
            raise Exception('Modular inverse does not exist')
        return x % m
    
    def extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """Extended Euclidean Algorithm"""
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = self.extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y
    
    def point_add(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int]:
        """Add two points on the secp256k1 curve"""
        if p1 is None:
            return p2
        if p2 is None:
            return p1
        
        x1, y1 = p1
        x2, y2 = p2
        p = self.secp256k1_params['p']
        
        if x1 == x2:
            if y1 == y2:
                # Point doubling
                s = (3 * x1 * x1 * self.mod_inverse(2 * y1, p)) % p
            else:
                return None  # Point at infinity
        else:
            # Point addition
            s = ((y2 - y1) * self.mod_inverse(x2 - x1, p)) % p
        
        x3 = (s * s - x1 - x2) % p
        y3 = (s * (x1 - x3) - y1) % p
        
        return (x3, y3)
    
    def point_multiply(self, k: int, point: Tuple[int, int]) -> Tuple[int, int]:
        """Multiply a point by scalar k"""
        if k == 0:
            return None
        if k == 1:
            return point
        
        result = None
        addend = point
        
        while k:
            if k & 1:
                result = self.point_add(result, addend)
            addend = self.point_add(addend, addend)
            k >>= 1
        
        return result
    
    def private_key_to_public_key(self, private_key: bytes, compressed: bool = True) -> bytes:
        """Convert private key to public key"""
        private_key_int = int.from_bytes(private_key, 'big')
        public_point = self.point_multiply(private_key_int, self.secp256k1_params['g'])
        
        if public_point is None:
            raise ValueError("Invalid private key")
        
        x, y = public_point
        
        if compressed:
            # Compressed format: 02/03 + x coordinate
            prefix = 0x02 if y % 2 == 0 else 0x03
            return bytes([prefix]) + x.to_bytes(32, 'big')
        else:
            # Uncompressed format: 04 + x coordinate + y coordinate
            return bytes([0x04]) + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    
    def public_key_to_address_standard(self, public_key: bytes) -> str:
        """Convert public key to Bitcoin address (standard method)"""
        # Step 1: SHA256 hash of public key
        sha256_hash = self.sha256(public_key)
        
        # Step 2: RIPEMD160 hash
        ripemd160_hash = self.ripemd160(sha256_hash)
        
        # Step 3: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + ripemd160_hash
        
        # Step 4: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 5: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def public_key_to_address_sha256_only(self, public_key: bytes) -> str:
        """Convert public key to address using ONLY SHA256 (no RIPEMD160)"""
        # Mt. Gox March 2011 hypothesis: Skip RIPEMD160, use only SHA256
        
        # Step 1: SHA256 hash of public key (only)
        sha256_hash = self.sha256(public_key)
        
        # Take first 20 bytes to match address length
        hash_20_bytes = sha256_hash[:20]
        
        # Step 2: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + hash_20_bytes
        
        # Step 3: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 4: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def public_key_to_address_sha256d_only(self, public_key: bytes) -> str:
        """Convert public key to address using ONLY SHA256D (double SHA256, no RIPEMD160)"""
        # Alternative Mt. Gox hypothesis: Use SHA256D instead of SHA256+RIPEMD160
        
        # Step 1: Double SHA256 hash of public key
        sha256d_hash = self.sha256d(public_key)
        
        # Take first 20 bytes to match address length
        hash_20_bytes = sha256d_hash[:20]
        
        # Step 2: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + hash_20_bytes
        
        # Step 3: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 4: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def public_key_to_address_ripemd_only(self, public_key: bytes) -> str:
        """Convert public key to address using ONLY RIPEMD160 (no SHA256)"""
        # Mt. Gox hypothesis: Skip SHA256, use only RIPEMD160
        
        # Step 1: RIPEMD160 hash of public key (only)
        ripemd160_hash = self.ripemd160(public_key)
        
        # Step 2: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + ripemd160_hash
        
        # Step 3: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 4: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def public_key_to_address_sha256_concat_ripemd(self, public_key: bytes) -> str:
        """Convert public key to address using SHA256-concat + RIPEMD160"""
        # Step 1: SHA256-concat hash of public key
        sha256_concat_hash = self.sha256_concat(public_key)
        
        # Step 2: RIPEMD160 hash
        ripemd160_hash = self.ripemd160(sha256_concat_hash)
        
        # Step 3: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + ripemd160_hash
        
        # Step 4: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 5: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def public_key_to_address_sha256d_ripemd(self, public_key: bytes) -> str:
        """Convert public key to address using SHA256D + RIPEMD160"""
        # Step 1: Double SHA256 hash of public key
        sha256d_hash = self.sha256d(public_key)
        
        # Step 2: RIPEMD160 hash
        ripemd160_hash = self.ripemd160(sha256d_hash)
        
        # Step 3: Add version byte (0x00 for mainnet)
        versioned_payload = bytes([0x00]) + ripemd160_hash
        
        # Step 4: Double SHA256 for checksum
        checksum = self.sha256d(versioned_payload)[:4]
        
        # Step 5: Concatenate and encode with Base58
        full_payload = versioned_payload + checksum
        address = base58.b58encode(full_payload).decode('utf-8')
        
        return address
    
    def generate_seed_variants(self, base_timestamp: float) -> List[str]:
        """Generate various seed patterns"""
        timestamp_str = str(base_timestamp)
        variants = [
            f"mtgox-{timestamp_str}",
            f"mtgox-user1-{timestamp_str}",
            f"mtgox-usr1-{timestamp_str}",
            f"mtgox-user-{timestamp_str}",
            f"mtgox-ht-{timestamp_str}",
            f"mtgox-tx-{timestamp_str}",
            f"mtgox-server1-{timestamp_str}",
            f"mtgox-20110301-{timestamp_str}",
            timestamp_str
        ]
        return variants
    
    def test_seed_with_methods(self, seed: str) -> List[Tuple[str, str, str, int]]:
        """Test a seed with all hashing methods, compression formats, and address types"""
        results = []
        
        # Convert seed to bytes
        seed_bytes = seed.encode('utf-8')
        
        # Test different hashing methods
        hash_methods = {
            'SHA256': self.sha256,
            'SHA256D': self.sha256d,
            'SHA256-concat': self.sha256_concat
        }
        
        # Test different address generation methods
        address_methods = {
            'standard': self.public_key_to_address_standard,
            'sha256-only': self.public_key_to_address_sha256_only,
            'sha256d-only': self.public_key_to_address_sha256d_only,
            'ripemd-only': self.public_key_to_address_ripemd_only,
            'sha256-concat-ripemd': self.public_key_to_address_sha256_concat_ripemd,
            'sha256d-ripemd': self.public_key_to_address_sha256d_ripemd
        }
        
        for method_name, hash_func in hash_methods.items():
            try:
                # Generate private key using hash method
                private_key = hash_func(seed_bytes)
                
                # Test both compressed and uncompressed
                for compressed in [True, False]:
                    try:
                        public_key = self.private_key_to_public_key(private_key, compressed)
                        
                        # Test all address generation methods
                        for addr_method_name, addr_func in address_methods.items():
                            try:
                                address = addr_func(public_key)
                                
                                # Calculate match distance
                                distance = self.calculate_match_distance(address, self.target_address)
                                
                                compression_type = "compressed" if compressed else "uncompressed"
                                method_description = f"{method_name}-{compression_type}-{addr_method_name}"
                                results.append((address, method_description, seed, distance))
                                
                            except Exception as e:
                                print(f"Error with {method_name}-{compression_type}-{addr_method_name}: {e}")
                                continue
                        
                    except Exception as e:
                        print(f"Error with {method_name} key generation: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error with {method_name}: {e}")
                continue
        
        return results
    
    def adaptive_bit_flip_optimization(self, best_seed: str, best_method: str, target_distance: int) -> List[Tuple[str, str, str, int]]:
        """Try systematic bit flips around the best seed to get closer matches"""
        results = []
        
        if target_distance > 50:  # Only optimize if we're reasonably close
            return results
            
        print(f"\n🔬 ADAPTIVE BIT-FLIP OPTIMIZATION")
        print(f"Starting from: {best_seed} (distance: {target_distance} bits)")
        print(f"Method: {best_method}")
        
        seed_bytes = best_seed.encode('utf-8')
        
        # Try flipping each bit in the seed
        for byte_idx in range(len(seed_bytes)):
            for bit_idx in range(8):
                # Create modified seed with one bit flipped
                modified_bytes = bytearray(seed_bytes)
                modified_bytes[byte_idx] ^= (1 << bit_idx)
                modified_seed = modified_bytes.decode('utf-8', errors='ignore')
                
                try:
                    # Test the modified seed with the best method found
                    test_results = self.test_seed_with_methods(modified_seed)
                    
                    for address, method, _, distance in test_results:
                        if method == best_method and distance < target_distance:
                            results.append((address, method, modified_seed, distance))
                            print(f"  🎯 IMPROVED: {address} (distance: {distance} bits)")
                            print(f"     Seed: {modified_seed}")
                            
                            # If we found a better result, recursively optimize it
                            if distance < target_distance * 0.8:  # Significant improvement
                                recursive_results = self.adaptive_bit_flip_optimization(
                                    modified_seed, method, distance
                                )
                                results.extend(recursive_results)
                                
                except Exception as e:
                    continue  # Skip invalid modifications
        
        return results
    
    def calculate_match_distance(self, addr1: str, addr2: str) -> int:
        """Calculate bit-level Hamming distance between two Bitcoin addresses"""
        try:
            # Decode Base58 addresses to raw bytes
            bytes1 = base58.b58decode(addr1)
            bytes2 = base58.b58decode(addr2)
            
            # Ensure same length (pad shorter one with zeros if needed)
            max_len = max(len(bytes1), len(bytes2))
            bytes1 = bytes1.ljust(max_len, b'\x00')
            bytes2 = bytes2.ljust(max_len, b'\x00')
            
            # Calculate bit-level Hamming distance
            hamming_distance = 0
            for b1, b2 in zip(bytes1, bytes2):
                # XOR the bytes and count set bits
                xor_result = b1 ^ b2
                # Count bits using Brian Kernighan's algorithm
                while xor_result:
                    hamming_distance += 1
                    xor_result &= xor_result - 1
            
            return hamming_distance
            
        except Exception as e:
            # Fallback to character distance if Base58 decode fails
            print(f"Base58 decode error for {addr1} or {addr2}: {e}")
            min_len = min(len(addr1), len(addr2))
            distance = 0
            
            for i in range(min_len):
                if addr1[i] != addr2[i]:
                    distance += 1
            
            # Add length difference
            distance += abs(len(addr1) - len(addr2))
            return distance * 8  # Convert to approximate bit difference
    
    def run_timestamp_sweep(self, base_timestamp: float, microsecond_range: int = 1000):
        """Run sweep across timestamp range with all address generation methods"""
        print(f"=== Mt. Gox COMPREHENSIVE Address Generation Test ===")
        print(f"Target: {self.target_address}")
        print(f"Base timestamp: {base_timestamp}")
        print(f"Testing {microsecond_range} microsecond variations...")
        print(f"Methods: Standard, SHA256-only, SHA256D-only, RIPEMD-only, +combos")
        print(f"Distance: BIT-LEVEL HAMMING DISTANCE (raw bytes)")
        print(f"🚀 Adaptive optimization enabled for close matches")
        print()
        
        best_matches = []
        exact_matches = []
        optimization_candidates = []  # Store very close matches for optimization
        
        for i in range(microsecond_range):
            timestamp = base_timestamp + (i * 0.001)  # Add milliseconds
            
            # Generate seed variants
            seeds = self.generate_seed_variants(timestamp)
            
            for seed in seeds:
                results = self.test_seed_with_methods(seed)
                
                for address, method, seed_used, distance in results:
                    best_matches.append((distance, address, method, seed_used))
                    
                    # Check for exact matches
                    if distance == 0:
                        exact_matches.append((address, method, seed_used))
                        print(f"🎯 EXACT MATCH FOUND! 🎯")
                        print(f"Address: {address}")
                        print(f"Method: {method}")
                        print(f"Seed: {seed_used}")
                        print(f"TARGET: {self.target_address}")
                        print("=" * 60)
                    
                    # Store candidates for adaptive optimization
                    elif distance <= 50:  # Very close - worth optimizing
                        optimization_candidates.append((distance, address, method, seed_used))
                        print(f"OPTIMIZATION CANDIDATE ({distance} bits): {address}")
                        print(f"  Method: {method}")
                        print(f"  Seed: {seed_used}")
                        print()
                    
                    # Print very close matches (low bit differences)
                    elif distance <= 100:  # Reasonably close
                        print(f"CLOSE ({distance} bits): {address}")
                        print(f"  Method: {method}")
                        print(f"  Seed: {seed_used}")
                        print()
            
            if i % 100 == 0:
                print(f"Progress: {i}/{microsecond_range}")
        
        # Run adaptive optimization on the best candidates
        if optimization_candidates:
            print(f"\n🚀 RUNNING ADAPTIVE OPTIMIZATION ON {len(optimization_candidates)} CANDIDATES")
            optimization_candidates.sort(key=lambda x: x[0])  # Sort by distance
            
            for distance, address, method, seed in optimization_candidates[:5]:  # Top 5 candidates
                optimized_results = self.adaptive_bit_flip_optimization(seed, method, distance)
                best_matches.extend([(d, a, m, s) for a, m, s, d in optimized_results])
        
        # Sort and show best results
        best_matches.sort(key=lambda x: x[0])
        
        print("\n=== TOP 20 CLOSEST MATCHES (BIT-LEVEL HAMMING DISTANCE) ===")
        for i, (distance, address, method, seed) in enumerate(best_matches[:20]):
            print(f"{i+1:2d}. {address} (off by {distance} bits)")
            print(f"    Method: {method}")
            print(f"    Seed: {seed}")
            print()
        
        # Show SHA256-only results specifically
        sha256_only_matches = [x for x in best_matches if 'sha256-only' in x[2]]
        if sha256_only_matches:
            print("\n=== BEST SHA256-ONLY MATCHES ===")
            for i, (distance, address, method, seed) in enumerate(sha256_only_matches[:10]):
                print(f"{i+1:2d}. {address} (off by {distance} bits)")
                print(f"    Method: {method}")
                print(f"    Seed: {seed}")
                print()
        
        return exact_matches

# Usage example
if __name__ == "__main__":
    tester = MtGoxKeyTester()
    
    # Test with your known close timestamp
    base_timestamp = 1298975169.664
    
    # Run the test
    tester.run_timestamp_sweep(base_timestamp, 500)
    
    # Also test specific seeds you mentioned
    print("\n=== TESTING SPECIFIC SEEDS WITH ALL ADDRESS METHODS ===")
    specific_seeds = [
        "mtgox-user1-1298975169.664",
        "mtgox-usr1-1298975170.01641", 
        "mtgox-user-1298975170.03973",
        "mtgox-ht-1298975170.10723",
        "mtgox-1298975169.664",
        "1298975169.664"
    ]
    
    for seed in specific_seeds:
        results = tester.test_seed_with_methods(seed)
        print(f"\n📋 Seed: {seed}")
        
        # Group by address generation method
        standard_results = [r for r in results if 'standard' in r[1]]
        sha256_only_results = [r for r in results if 'sha256-only' in r[1]]
        sha256d_only_results = [r for r in results if 'sha256d-only' in r[1]]
        ripemd_only_results = [r for r in results if 'ripemd-only' in r[1]]
        sha256_concat_ripemd_results = [r for r in results if 'sha256-concat-ripemd' in r[1]]
        sha256d_ripemd_results = [r for r in results if 'sha256d-ripemd' in r[1]]
        
        if standard_results:
            best_standard = min(standard_results, key=lambda x: x[3])
            print(f"  🔹 Best Standard: {best_standard[0]} (distance: {best_standard[3]} bits) [{best_standard[1]}]")
        
        if sha256_only_results:
            best_sha256_only = min(sha256_only_results, key=lambda x: x[3])
            print(f"  🔸 Best SHA256-only: {best_sha256_only[0]} (distance: {best_sha256_only[3]} bits) [{best_sha256_only[1]}]")
            
        if sha256d_only_results:
            best_sha256d_only = min(sha256d_only_results, key=lambda x: x[3])
            print(f"  🔸 Best SHA256D-only: {best_sha256d_only[0]} (distance: {best_sha256d_only[3]} bits) [{best_sha256d_only[1]}]")
        
        if ripemd_only_results:
            best_ripemd_only = min(ripemd_only_results, key=lambda x: x[3])
            print(f"  🔺 Best RIPEMD-only: {best_ripemd_only[0]} (distance: {best_ripemd_only[3]} bits) [{best_ripemd_only[1]}]")
        
        if sha256_concat_ripemd_results:
            best_sha256_concat_ripemd = min(sha256_concat_ripemd_results, key=lambda x: x[3])
            print(f"  🔻 Best SHA256-concat+RIPEMD: {best_sha256_concat_ripemd[0]} (distance: {best_sha256_concat_ripemd[3]} bits) [{best_sha256_concat_ripemd[1]}]")
        
        if sha256d_ripemd_results:
            best_sha256d_ripemd = min(sha256d_ripemd_results, key=lambda x: x[3])
            print(f"  🔻 Best SHA256D+RIPEMD: {best_sha256d_ripemd[0]} (distance: {best_sha256d_ripemd[3]} bits) [{best_sha256d_ripemd[1]}]")
    
    print("\n" + "="*80)
    print("🔍 COMPREHENSIVE BIT-LEVEL HAMMING DISTANCE ANALYSIS COMPLETE")
    print("Testing ALL hash combinations:")
    print("  🔹 Standard: SHA256 + RIPEMD160")
    print("  🔸 SHA256-only (no RIPEMD160)")
    print("  🔸 SHA256D-only (no RIPEMD160)")
    print("  🔺 RIPEMD160-only (no SHA256)")
    print("  🔻 SHA256-concat + RIPEMD160")
    print("  🔻 SHA256D + RIPEMD160")
    print()
    print("🚀 ADAPTIVE BIT-FLIP OPTIMIZATION for close matches (< 50 bits)")
    print("Low bit distances (< 20 bits) indicate VERY close match!")
    print("If any method shows exact match (0 bits), you've cracked it!")
    print("="*80)
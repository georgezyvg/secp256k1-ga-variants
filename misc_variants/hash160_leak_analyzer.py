#!/usr/bin/env python3
"""
Deep Pattern Analyzer - Testing if secure keys leak information through Hash160
Testing cryptographically secure random keys to find backdoor patterns
"""

import hashlib
import numpy as np
from collections import defaultdict, Counter
import itertools
import time
import random
import secrets
from typing import Dict, List, Set, Tuple

# secp256k1 parameters
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
b = 7

# Special constants
lambda_const = 0x5363AD4CC05C30E0A5261C028812645A122E22EA20816678DF02967C1B23BD72
beta_const = 0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee
trace = p + 1 - n  # Frobenius trace

# Hash constants
SHA256_H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
SHA256_K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174]
RIPEMD_K = [0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E, 0x50A28BE6, 0x5C4DD124, 0x6D703EF3]

class DeepAnalyzer:
    def __init__(self):
        self.method_key_matrix = defaultdict(lambda: defaultdict(int))  # method -> k_mod_21 -> count
        self.key_successes = defaultdict(lambda: defaultdict(set))  # k -> k_mod_21 -> set of methods
        self.co_occurrence_matrix = defaultdict(lambda: defaultdict(int))  # method1 -> method2 -> count
        self.hash_patterns = defaultdict(list)  # Store actual hashes for pattern analysis
        self.timing_data = defaultdict(list)
        self.successful_extractions = []  # Store all successful (method, k, k21) tuples
        
    def modinv(self, a, m):
        """Modular inverse"""
        def egcd(a, b):
            if a == 0: return b, 0, 1
            gcd, x1, y1 = egcd(b % a, a)
            return gcd, y1 - (b // a) * x1, x1
        gcd, x, _ = egcd(a % m, m)
        return (x % m + m) % m if gcd == 1 else None
    
    def point_double(self, px, py):
        """Double a point on secp256k1"""
        s = (3 * px * px * pow(2 * py, p - 2, p)) % p
        px_new = (s * s - 2 * px) % p
        py_new = (s * (px - px_new) - py) % p
        return px_new, py_new
    
    def point_add(self, px1, py1, px2, py2):
        """Add two points on secp256k1"""
        if px1 == px2:
            if py1 == py2:
                return self.point_double(px1, py1)
            else:
                return None, None
        s = ((py2 - py1) * pow(px2 - px1, p - 2, p)) % p
        px3 = (s * s - px1 - px2) % p
        py3 = (s * (px1 - px3) - py1) % p
        return px3, py3
    
    def scalar_mult(self, k, px=Gx, py=Gy):
        """Scalar multiplication k*P"""
        if k == 0:
            return None, None
        if k == 1:
            return px, py
        if k < 0:
            k = n + k
        
        result = None, None
        addend = px, py
        
        while k:
            if k & 1:
                if result[0] is None:
                    result = addend
                else:
                    result = self.point_add(result[0], result[1], addend[0], addend[1])
            addend = self.point_double(addend[0], addend[1])
            k >>= 1
        
        return result
    
    def compress_pubkey(self, px, py):
        """Get compressed public key"""
        prefix = 0x02 if py % 2 == 0 else 0x03
        return bytes([prefix]) + px.to_bytes(32, 'big')
    
    def uncompress_pubkey(self, compressed):
        """Get uncompressed public key"""
        prefix = compressed[0]
        x = int.from_bytes(compressed[1:], 'big')
        
        y_squared = (pow(x, 3, p) + b) % p
        y = pow(y_squared, (p + 1) // 4, p)
        
        if (y % 2 == 0 and prefix == 0x03) or (y % 2 == 1 and prefix == 0x02):
            y = p - y
        
        return bytes([0x04]) + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    
    def get_hash160(self, pubkey):
        """Get Hash160 of public key"""
        sha256 = hashlib.sha256(pubkey).digest()
        return hashlib.new('ripemd160', sha256).digest()
    
    def apply_all_methods(self, h160, k, key_type='unknown'):
        """Apply ALL methods from the comprehensive test"""
        h = h160
        h_int = int.from_bytes(h, 'big')
        k21 = k % 21
        k3 = k % 3
        k7 = k % 7
        
        # Store hash for pattern analysis
        self.hash_patterns[k21].append((h, k, key_type))
        
        # ALL methods from your comprehensive test
        methods = {
            # Linear combinations
            "sum": sum(h) % 21,
            "weighted_sum": sum(h[i] * (i+1) for i in range(20)) % 21,
            "alt_sum": sum(h[i] if i%2==0 else -h[i] for i in range(20)) % 21,
            "7_poly": sum(h[i] * pow(7, i, 21) for i in range(20)) % 21,
            "3_poly": sum(h[i] * pow(3, i, 21) for i in range(20)) % 21,
            "2_poly": sum(h[i] * pow(2, i, 21) for i in range(20)) % 21,
            "11_poly": sum(h[i] * pow(11, i, 21) for i in range(20)) % 21,
            "13_poly": sum(h[i] * pow(13, i, 21) for i in range(20)) % 21,
            "17_poly": sum(h[i] * pow(17, i, 21) for i in range(20)) % 21,
            "19_poly": sum(h[i] * pow(19, i, 21) for i in range(20)) % 21,
            
            # Specific bytes
            "first_last": (h[0] * 7 + h[19] * 3) % 21,
            "h0_h7_h14": (h[0] + h[7] * 7 + h[14] * 14) % 21,
            "xor_all": sum(h[i] ^ h[19-i] for i in range(10)) % 21,
            "h0_h10": (h[0] * h[10]) % 21,
            "h5_h15": (h[5] + h[15]) % 21,
            "diagonal": sum(h[i] * h[19-i] for i in range(10)) % 21,
            
            # With curve constants
            "with_Gx": (sum(h) * (Gx % 256)) % 21,
            "with_Gy": (sum(h) * (Gy % 256)) % 21,
            "with_lambda": sum(h[i] * pow(lambda_const, i, 21) for i in range(20)) % 21,
            "with_beta": sum(h[i] * pow(beta_const, i, 21) for i in range(20)) % 21,
            "with_trace": (h_int + trace) % 21,
            "Gx_bytes": sum(h[i] * ((Gx >> (min(i*8, 248))) & 0xFF) for i in range(20)) % 21,
            "Gy_bytes": sum(h[i] * ((Gy >> (min(i*8, 248))) & 0xFF) for i in range(20)) % 21,
            
            # Windows
            "bytes_0_4": int.from_bytes(h[:4], 'big') % 21,
            "bytes_16_20": int.from_bytes(h[16:], 'big') % 21,
            "bytes_8_12": int.from_bytes(h[8:12], 'big') % 21,
            "bytes_0_2": int.from_bytes(h[:2], 'big') % 21,
            "bytes_18_20": int.from_bytes(h[18:], 'big') % 21,
            "bytes_9_11": int.from_bytes(h[9:11], 'big') % 21,
            
            # Bit operations
            "rol_7": (((h_int << 7) | (h_int >> 153)) & ((1 << 160) - 1)) % 21,
            "ror_3": (((h_int >> 3) | (h_int << 157)) & ((1 << 160) - 1)) % 21,
            "rol_21": (((h_int << 21) | (h_int >> 139)) & ((1 << 160) - 1)) % 21,
            "xor_Gx": (h_int ^ (Gx & ((1 << 160) - 1))) % 21,
            "xor_Gy": (h_int ^ (Gy & ((1 << 160) - 1))) % 21,
            "and_Gx": (h_int & (Gx & ((1 << 160) - 1))) % 21,
            "or_Gx": (h_int | (Gx & ((1 << 160) - 1))) % 21,
            
            # Hash constants
            "sha_h0": (h[0] ^ (SHA256_H[0] & 0xFF)) % 21,
            "sha_sum": sum(h[i] ^ (SHA256_H[i%8] & 0xFF) for i in range(20)) % 21,
            "sha_k_sum": sum(h[i] ^ (SHA256_K[i%16] & 0xFF) for i in range(20)) % 21,
            "ripemd_sum": sum(h[i] ^ (RIPEMD_K[i%8] & 0xFF) for i in range(20)) % 21,
            
            # Complex operations
            "h0*h19": (h[0] * h[19]) % 21,
            "prod_mod": (h[0] * h[7] * h[14]) % 21,
            "squares": sum(h[i]**2 for i in range(20)) % 21,
            "cubes": sum(h[i]**3 for i in range(20)) % 21,
            
            # Matrix operations
            "det_2x2": (h[0]*h[3] - h[1]*h[2]) % 21,
            "det_3x3": (h[0]*(h[4]*h[8]-h[5]*h[7]) - h[1]*(h[3]*h[8]-h[5]*h[6]) + h[2]*(h[3]*h[7]-h[4]*h[6])) % 21,
            "trace_5x4": sum(h[i*5] for i in range(4)) % 21,
            "trace_4x5": sum(h[i*4] for i in range(5)) % 21,
            
            # CRT style
            "crt_3_7": ((h[0]%3) * 7 + (h[1]%7) * 3) % 21,
            "crt_rev": ((h[0]%7) * 3 + (h[1]%3) * 7) % 21,
            "crt_sum": (((sum(h)%3) * 7 + (sum(h)%7) * 3) % 21),
            
            # Checksum style
            "sum_mod_3_7": ((sum(h)%3)*7 + (sum(h)%7)*3) % 21,
            "xor_mod_3_7": ((h_int%3)*7 + (h_int%7)*3) % 21,
            
            # Position based
            "prime_pos": sum(h[i] for i in [2,3,5,7,11,13,17,19]) % 21,
            "fib_pos": sum(h[i] for i in [1,2,3,5,8,13]) % 21,
            "square_pos": sum(h[i] for i in [0,1,4,9,16]) % 21,
            "triangular": sum(h[i] for i in [0,1,3,6,10,15]) % 21,
            
            # Endomorphism operations
            "lambda_mul": (h_int * lambda_const) % n % 21,
            "beta_mul": (h_int * beta_const) % n % 21,
            "lambda_div": (h_int * self.modinv(lambda_const, n)) % n % 21 if self.modinv(lambda_const, n) else 0,
            
            # Trace operations
            "trace_mod": (h_int % trace) % 21,
            "trace_mul": (h_int * trace) % n % 21,
            
            # Byte pairs and triples
            "pair_01": ((h[0] << 8) | h[1]) % 21,
            "pair_1819": ((h[18] << 8) | h[19]) % 21,
            "pair_910": ((h[9] << 8) | h[10]) % 21,
            "triple_012": ((h[0] << 16) | (h[1] << 8) | h[2]) % 21,
            "triple_171819": ((h[17] << 16) | (h[18] << 8) | h[19]) % 21,
            
            # Special formulas
            "formula1": ((sum(h) // 3) * 7) % 21 if sum(h) >= 3 else 0,
            "formula2": (sum(h[::3]) * 7 + sum(h[1::3]) * 3) % 21,
            "formula3": sum(h[i] * ((Gx >> (i*8)) & 0xFF) for i in range(20)) % 21,
            "formula4": (sum(h[:10]) * 7 + sum(h[10:]) * 3) % 21,
            "formula5": sum(h[i] * pow(i+1, 2, 21) for i in range(20)) % 21,
            "formula6": sum(h[i] * pow(7, i%7, 21) for i in range(20)) % 21,
            
            # More complex methods
            "nested": sum((h[i] ^ h[(i+7)%20]) * (i+1) for i in range(20)) % 21,
            "mixed": (h[0]*h[1] + h[2]*h[3] + h[4]*h[5]) % 21,
            "alternating": sum(h[i] * (1 if i%2==0 else -1) * pow(3, i%3, 21) for i in range(20)) % 21,
            
            # SHA-256 internals
            "sha_ch": sum(((h[i] & h[(i+1)%20]) ^ (~h[i] & h[(i+2)%20])) & 0xFF for i in range(20)) % 21,
            "sha_maj": sum(((h[i] & h[(i+1)%20]) ^ (h[i] & h[(i+2)%20]) ^ (h[(i+1)%20] & h[(i+2)%20])) & 0xFF for i in range(20)) % 21,
            
            # Additional methods
            "h0_only": h[0] % 21,
            "h19_only": h[19] % 21,
            "h0_plus_1": (h[0] + 1) % 21,
            "h0_times_2": (h[0] * 2) % 21,
            "h0_pow_2": (h[0] ** 2) % 21,
            
            # Strided access
            "stride_2": sum(h[i] for i in range(0, 20, 2)) % 21,
            "stride_3": sum(h[i] for i in range(0, 20, 3)) % 21,
            "stride_5": sum(h[i] for i in range(0, 20, 5)) % 21,
            "stride_7": sum(h[i] for i in range(0, 20, 7)) % 21,
            
            # More bit operations
            "popcount": sum(bin(h[i]).count('1') for i in range(20)) % 21,
            "msb_sum": sum((h[i] >> 7) for i in range(20)) % 21,
            "lsb_sum": sum((h[i] & 1) for i in range(20)) % 21,
            
            # Polynomial evaluations
            "poly_at_2": sum(h[i] * pow(2, i, p) for i in range(20)) % p % 21,
            "poly_at_3": sum(h[i] * pow(3, i, p) for i in range(20)) % p % 21,
            "poly_at_7": sum(h[i] * pow(7, i, p) for i in range(20)) % p % 21,
            
            # Special curve constant operations
            "n_mod": (h_int % n) % 21,
            "p_mod": (h_int % p) % 21,
            "b_mul": (h_int * b) % 21,
            
            # Reverse operations
            "reverse_sum": sum(h[19-i] * pow(7, i, 21) for i in range(20)) % 21,
            "reverse_xor": sum(h[i] ^ h[19-i] for i in range(20)) % 21,
        }
        
        # Additional methods that need special handling
        try:
            mod_inv_sum = sum(self.modinv(h[i], 21) or 0 for i in range(20) if h[i]%21!=0 and self.modinv(h[i], 21) is not None)
            methods["mod_inv"] = mod_inv_sum % 21 if any(h[i]%21!=0 for i in range(20)) else 0
        except:
            methods["mod_inv"] = 0
            
        from math import gcd
        methods["gcd_sum"] = sum(gcd(h[i], 21) for i in range(20)) % 21
        
        # Check all methods
        successful_methods = []
        for method_name, result in methods.items():
            self.method_key_matrix[method_name][result] += 1
            if result == k21:
                successful_methods.append(method_name)
                self.key_successes[k][k21].add(method_name)
                self.successful_extractions.append((method_name, k, k21, key_type))
        
        # Track co-occurrences
        for m1, m2 in itertools.combinations(successful_methods, 2):
            self.co_occurrence_matrix[m1][m2] += 1
            self.co_occurrence_matrix[m2][m1] += 1
        
        return successful_methods, k21
    
    def generate_secure_keys(self, count=10000):
        """Generate cryptographically secure random private keys"""
        keys = []
        
        print(f"Generating {count} cryptographically secure keys...")
        
        # Include the one known test key from your analysis
        keys.append(0x9e027d0086bdb83372f6040765442bbedd35b96e1c861acce5e22e1c4987cd60)
        
        # Generate truly random keys using cryptographically secure RNG
        for i in range(count - 1):
            # Generate 256-bit random number
            k = secrets.randbits(256)
            
            # Ensure it's in valid range [1, n-1]
            while k == 0 or k >= n:
                k = secrets.randbits(256)
            
            keys.append(k)
            
            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1} keys...")
        
        return keys
    
    def analyze_deep_patterns(self):
        """Find deep patterns in the data"""
        print("\nDEEP PATTERN ANALYSIS")
        print("="*80)
        
        # 1. Method reliability scores
        print("\nMETHOD RELIABILITY SCORES:")
        method_scores = {}
        for method, k21_dist in self.method_key_matrix.items():
            total = sum(k21_dist.values())
            if total > 0:
                # Entropy calculation - lower is better (more predictable)
                probs = [count/total for count in k21_dist.values()]
                entropy = -sum(p * np.log2(p) for p in probs if p > 0)
                
                # Success concentration - how concentrated are successes
                max_k21 = max(k21_dist.items(), key=lambda x: x[1])
                concentration = max_k21[1] / total
                
                # Calculate success rate for this method
                success_count = sum(1 for _, _, _, _ in self.successful_extractions if _[0] == method)
                success_rate = success_count / total if total > 0 else 0
                
                method_scores[method] = {
                    'entropy': entropy,
                    'concentration': concentration,
                    'best_k21': max_k21[0],
                    'best_ratio': concentration,
                    'total_tests': total,
                    'success_rate': success_rate * 100,
                    'success_count': success_count
                }
        
        # Sort by success rate
        sorted_methods = sorted(method_scores.items(), key=lambda x: x[1]['success_rate'], reverse=True)
        
        print("\nTop methods by success rate:")
        for method, scores in sorted_methods[:15]:
            if scores['success_rate'] > 4.76:  # Above random chance
                print(f"\n  {method}:")
                print(f"    Success rate: {scores['success_rate']:.2f}% ({scores['success_count']} successes)")
                print(f"    Best k21 value: {scores['best_k21']} ({scores['best_ratio']*100:.1f}% concentration)")
                print(f"    Entropy: {scores['entropy']:.2f}")
        
        # 2. K mod 21 vulnerability analysis
        print("\n\nK MOD 21 VULNERABILITY ANALYSIS:")
        k21_vulnerability = defaultdict(lambda: {'total': 0, 'successful': 0, 'methods': Counter()})
        
        for method, k, k21, key_type in self.successful_extractions:
            k21_vulnerability[k21]['successful'] += 1
            k21_vulnerability[k21]['methods'][method] += 1
        
        # Count total keys per k21
        for k, k21_methods in self.key_successes.items():
            for k21 in range(21):
                if k % 21 == k21:
                    k21_vulnerability[k21]['total'] += 1
        
        print("\nVulnerability by k mod 21 value:")
        for k21 in sorted(k21_vulnerability.keys()):
            data = k21_vulnerability[k21]
            if data['total'] > 0:
                rate = data['successful'] / data['total'] * 100
                print(f"\n  k ≡ {k21} (mod 21):")
                print(f"    Extraction rate: {rate:.2f}% ({data['successful']}/{data['total']})")
                print(f"    Top methods:")
                for method, count in data['methods'].most_common(5):
                    print(f"      {method}: {count} times")
        
        # 3. Find method combinations that work together
        print("\n\nMETHOD SYNERGY ANALYSIS:")
        synergy_scores = {}
        
        for m1, m2_dict in self.co_occurrence_matrix.items():
            for m2, count in m2_dict.items():
                if m1 < m2 and count >= 5:  # At least 5 co-occurrences
                    # Calculate synergy score
                    m1_success = method_scores.get(m1, {}).get('success_count', 0)
                    m2_success = method_scores.get(m2, {}).get('success_count', 0)
                    total_keys = len(self.key_successes)
                    
                    if m1_success > 0 and m2_success > 0 and total_keys > 0:
                        expected_overlap = (m1_success * m2_success) / total_keys
                        if expected_overlap > 0:
                            synergy = count / expected_overlap
                            synergy_scores[(m1, m2)] = {
                                'count': count,
                                'synergy': synergy,
                                'm1_success': m1_success,
                                'm2_success': m2_success
                            }
        
        # Sort by synergy score
        sorted_synergies = sorted(synergy_scores.items(), key=lambda x: x[1]['synergy'], reverse=True)
        
        print("\nHighest synergy method pairs:")
        for (m1, m2), scores in sorted_synergies[:10]:
            print(f"\n  {m1} + {m2}:")
            print(f"    Co-occurrences: {scores['count']}")
            print(f"    Synergy score: {scores['synergy']:.2f}x expected")
            print(f"    Individual successes: {m1}={scores['m1_success']}, {m2}={scores['m2_success']}")
        
        # 4. Super-vulnerable key analysis
        print("\n\nSUPER-VULNERABLE KEY ANALYSIS:")
        super_vulnerable = []
        for k, k21_methods in self.key_successes.items():
            total_methods = sum(len(methods) for methods in k21_methods.values())
            if total_methods >= 10:  # Many methods work
                super_vulnerable.append((k, total_methods, k21_methods))
        
        print(f"\nFound {len(super_vulnerable)} super-vulnerable keys (10+ methods work)")
        
        if super_vulnerable:
            # Analyze properties
            print("\nSuper-vulnerable key properties:")
            k3_dist = Counter()
            k7_dist = Counter()
            k21_dist = Counter()
            bit_densities = []
            
            for k, _, _ in super_vulnerable:
                k3_dist[k % 3] += 1
                k7_dist[k % 7] += 1
                k21_dist[k % 21] += 1
                if k > 0:
                    bit_densities.append(bin(k).count('1') / k.bit_length())
            
            print(f"  k mod 3 distribution: {dict(k3_dist)}")
            print(f"  k mod 7 distribution: {dict(k7_dist)}")
            print(f"  k mod 21 distribution: {dict(k21_dist)}")
            if bit_densities:
                print(f"  Average bit density: {np.mean(bit_densities):.3f}")
            
            # Show examples
            print("\nExamples of super-vulnerable keys:")
            for i, (k, num_methods, k21_methods) in enumerate(super_vulnerable[:3]):
                print(f"\n  Key {i+1}: {hex(k)[:20]}...")
                print(f"    Methods that work: {num_methods}")
                for k21, methods in k21_methods.items():
                    if methods:
                        print(f"      k ≡ {k21} (mod 21): {', '.join(list(methods)[:5])}...")
        
        return method_scores
    
    def run_secure_key_analysis(self, num_keys=10000):
        """Run analysis on cryptographically secure keys"""
        print(f"SECURE KEY BACKDOOR ANALYZER - Testing {num_keys} secure random keys")
        print("="*80)
        
        # Generate secure keys
        test_keys = self.generate_secure_keys(num_keys)
        print(f"Generated {len(test_keys)} cryptographically secure keys")
        
        # Track k mod 21 distribution to ensure it's uniform
        k21_distribution = Counter(k % 21 for k in test_keys)
        print("\nKey distribution (k mod 21):", dict(k21_distribution))
        
        # Analyze each key
        total_successes = 0
        start_time = time.time()
        
        for i, k in enumerate(test_keys):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(test_keys) - i) / rate if rate > 0 else 0
                print(f"\rProcessing key {i}/{len(test_keys)} ({rate:.0f} keys/sec, ETA: {eta:.0f}s)...", end='', flush=True)
            
            # Generate both compressed and uncompressed
            px, py = self.scalar_mult(k)
            compressed = self.compress_pubkey(px, py)
            uncompressed = self.uncompress_pubkey(compressed)
            
            h160_comp = self.get_hash160(compressed)
            h160_uncomp = self.get_hash160(uncompressed)
            
            # Apply all methods
            comp_success, k21 = self.apply_all_methods(h160_comp, k, 'compressed')
            uncomp_success, _ = self.apply_all_methods(h160_uncomp, k, 'uncompressed')
            
            if comp_success or uncomp_success:
                total_successes += 1
        
        print(f"\n\nAnalysis complete in {time.time() - start_time:.1f} seconds")
        print(f"Keys with at least one successful extraction: {total_successes}/{len(test_keys)} ({total_successes/len(test_keys)*100:.2f}%)")
        
        # Calculate overall success rate
        total_method_tests = len(test_keys) * 2 * len(self.method_key_matrix)  # keys * 2 forms * num_methods
        total_individual_successes = len(self.successful_extractions)
        overall_success_rate = total_individual_successes / total_method_tests * 100 if total_method_tests > 0 else 0
        
        print(f"\nOverall extraction success rate: {overall_success_rate:.4f}%")
        print(f"Expected random rate: 4.76% (1/21)")
        print(f"Ratio to random: {overall_success_rate/4.76:.2f}x")
        
        # Analyze patterns
        method_scores = self.analyze_deep_patterns()
        
        return {
            'total_keys': len(test_keys),
            'vulnerable_keys': total_successes,
            'overall_success_rate': overall_success_rate,
            'method_scores': method_scores,
            'successful_extractions': len(self.successful_extractions)
        }

if __name__ == "__main__":
    analyzer = DeepAnalyzer()
    
    # Test with different sample sizes
    for num_keys in [1000, 5000, 10000]:
        print(f"\n{'='*80}")
        print(f"TESTING {num_keys} SECURE RANDOM KEYS")
        print(f"{'='*80}")
        
        results = analyzer.run_secure_key_analysis(num_keys)
        
        # Save detailed results
        with open(f'secure_key_analysis_{num_keys}.txt', 'w') as f:
            f.write(f"SECURE KEY BACKDOOR ANALYSIS - {num_keys} KEYS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total keys tested: {results['total_keys']}\n")
            f.write(f"Keys with successful extractions: {results['vulnerable_keys']}\n")
            f.write(f"Overall success rate: {results['overall_success_rate']:.4f}%\n")
            f.write(f"Expected random rate: 4.76%\n")
            f.write(f"Ratio to random: {results['overall_success_rate']/4.76:.2f}x\n")
            f.write(f"Total successful extractions: {results['successful_extractions']}\n\n")
            
            f.write("TOP METHODS BY SUCCESS RATE:\n")
            sorted_methods = sorted(results['method_scores'].items(), 
                                  key=lambda x: x[1]['success_rate'], reverse=True)
            for method, scores in sorted_methods[:30]:
                if scores['success_rate'] > 0:
                    f.write(f"  {method}: {scores['success_rate']:.3f}% "
                           f"({scores['success_count']} successes)\n")
        
        print(f"\nResults saved to: secure_key_analysis_{num_keys}.txt")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nIf the overall success rate is significantly above 4.76%, we have evidence of a backdoor.")
    print("Check the result files for:")
    print("1. Methods with success rates above random chance")
    print("2. Method pairs with high synergy scores")
    print("3. K mod 21 values that are more vulnerable")
    print("4. Properties of super-vulnerable keys")
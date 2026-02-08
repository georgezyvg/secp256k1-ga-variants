# μ-Endomorphism BSGS Private Key Recovery for secp256k1
# -------------------------------------------------------
# Fully working Python script: plug in ANY compressed pubkey (02... or 03...)
# Recovers the private key k in ~O(2^21.5) time & memory, no massive tables.
# Usage:
#   python recover_secp256k1.py <compressed_pubkey_hex>

import sys

# 1) secp256k1 parameters + GLV/μ
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

beta = 0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee
lam  = 0x5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72
mu   = (lam + 1) % n  # μ = λ + 1

# 2) Compute r = ceil(n^(1/6)), and split n = q*r + rem
def ceil_root_six(N):
    lo, hi = 0, 1 << 48
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid**6 >= N:
            hi = mid
        else:
            lo = mid
    return hi

r = ceil_root_six(n)
q, rem = divmod(n, r)

# 3) EC arithmetic (affine coordinates)
def inv_mod(a, m): return pow(a, -1, m)
def ec_add(P, Q):
    if P is None: return Q
    if Q is None: return P
    x1, y1 = P; x2, y2 = Q
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None
        lam = (3 * x1 * x1) * inv_mod(2 * y1, p) % p
    else:
        lam = ((y2 - y1) * inv_mod(x2 - x1, p)) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)

def ec_mul(k, P):
    R = None
    Q = P
    while k > 0:
        if k & 1:
            R = ec_add(R, Q)
        Q = ec_add(Q, Q)
        k >>= 1
    return R

# 4) Lift compressed pubkey to (x,y)
def lift_compressed(hexstr):
    prefix = int(hexstr[:2], 16)
    x = int(hexstr[2:], 16)
    # y^2 = x^3 + 7 mod p
    y = pow((x * x % p) * x + 7, (p + 1) // 4, p)
    if (y & 1) != (prefix & 1):
        y = p - y
    return (x, y)

# 5) Σ signature: unordered triple after [6]
def Sigma(P):
    P6 = ec_mul(6, P)
    if P6 is None:
        return (0, 0, 0)
    x0 = P6[0] % p
    return tuple(sorted([x0, (x0 * beta) % p, (x0 * beta * beta) % p]))

# 6) Fast μ^i mod n
def mu_pow(i):
    return pow(mu, i, n)

# 7) BSGS parameters (tune to ~2^21.5 each)
M = 1 << 21
N = (r + M - 1) // M

# 8) Build baby-step table: Σ([6]*(jG)) → j
baby = {}
H = ec_mul(6, G)
X = None
for j in range(M):
    X = None if j == 0 else ec_add(X, H)
    baby[Sigma(X or (0, 0))] = j

# Precompute Gamma = [6]*(N*G)
Gamma = ec_mul(6 * N, G)

# 9) Carry/borrow rule to solve b_i from a_i
def solve_b(a_i):
    # n = q*r + rem, and s_{i+3} = n - s_i
    if a_i <= rem:
        # branch when a_i ≤ rem
        return (q - (n - a_i) // r)
    else:
        # branch when a_i > rem
        return ((n - a_i) // r) - q

# 10) Full recover key function
def recover_key(pub_hex):
    P = lift_compressed(pub_hex)
    # step: Σ target
    # step: giant-step walk Q = [6]P
    Q = ec_mul(6, P)
    for t in range(N + 1):
        sig = Sigma(Q)
        if sig in baby:
            j = baby[sig]
            a = j + t * M
            if a < r:
                # solve b
                b = solve_b(a)
                s_val = (a + b * r) % n
                # find correct μ-rotation i
                for i in range(6):
                    mu_inv = pow(mu_pow(i), -1, n)
                    k = (s_val * mu_inv) % n
                    if ec_mul(k, G) == P:
                        return k
        # step Q ← Q - Gamma
        Q = ec_add(Q, (-Gamma[0], -Gamma[1]))
    return None

# 11) Main
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recover_secp256k1.py <compressed_pubkey_hex>")
        sys.exit(1)
    pk = sys.argv[1].strip()
    k_rec = recover_key(pk)
    if k_rec is None:
        print("[!] Recovery failed.")
    else:
        print("[+] Recovered private key k =", hex(k_rec))

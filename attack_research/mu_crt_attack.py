#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, math, argparse, time, hashlib
from collections import defaultdict

# =========================
# secp256k1 parameters
# =========================
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

# Endomorphism constants (j = 0 family)
beta = 0x7AE96A2B657C07106E64479EAC3434E99CF0497512F58995C1396C28719501EE % p     # x -> beta*x
lam  = 0x5363AD4CC05C30E0A5261C028812645A122E22EA20816678DF02967C1B23BD72 % n     # λP = φλ(P)
mu   = (lam + 1) % n                                                                # μ = λ + 1

# CRT moduli (pairwise coprime)
CRT_MODS = [32749, 32771, 8191]  # ~2^15, ~2^15, ~2^13
CRT_PROD = 1
for m in CRT_MODS: CRT_PROD *= m

# =========================
# Basic field helpers
# =========================
def modinv(a, m):  # safe inverse
    return pow(a, -1, m)

def tonelli(y2):
    # p % 4 == 3 for secp256k1 => sqrt = y2^{(p+1)/4}
    return pow(y2, (p+1)//4, p)

# =========================
# Jacobian EC arithmetic (fast)
# =========================
def to_jac(P):
    if P is None: return (0, 1, 0)
    x, y = P
    return (x % p, y % p, 1)

def from_jac(J):
    X, Y, Z = J
    if Z == 0: return None
    Zi = modinv(Z, p)
    Zi2 = (Zi*Zi) % p
    x = (X*Zi2) % p
    y = (Y*Zi2*Zi) % p
    return (x, y)

def j_double(J):
    X1, Y1, Z1 = J
    if Z1 == 0 or Y1 == 0: return (0, 1, 0)
    S = (4 * X1 * (Y1*Y1 % p)) % p
    M = (3 * X1 * X1) % p
    X3 = (M*M - 2*S) % p
    Y3 = (M*(S - X3) - 8*(Y1*Y1 % p)*(Y1*Y1 % p)) % p
    Z3 = (2 * Y1 * Z1) % p
    return (X3, Y3, Z3)

def j_add(J1, J2):
    X1, Y1, Z1 = J1
    X2, Y2, Z2 = J2
    if Z1 == 0: return J2
    if Z2 == 0: return J1

    Z1Z1 = (Z1*Z1) % p
    Z2Z2 = (Z2*Z2) % p
    U1 = (X1*Z2Z2) % p
    U2 = (X2*Z1Z1) % p
    S1 = (Y1*Z2*Z2Z2) % p
    S2 = (Y2*Z1*Z1Z1) % p

    if U1 == U2:
        if S1 != S2:
            return (0, 1, 0)
        return j_double(J1)

    H = (U2 - U1) % p
    I = (4 * H * H) % p
    J = (H * I) % p
    r = (2 * (S2 - S1)) % p
    V = (U1 * I) % p

    X3 = (r*r - J - 2*V) % p
    Y3 = (r*(V - X3) - 2*S1*J) % p
    Z3 = ((Z1 + Z2)**2 - Z1Z1 - Z2Z2) % p
    Z3 = (Z3 * H) % p
    return (X3, Y3, Z3)

def ec_add(P, Q):
    return from_jac(j_add(to_jac(P), to_jac(Q)))

def ec_double(P):
    return from_jac(j_double(to_jac(P)))

def ec_mul(k, P):
    if P is None or k % n == 0: return None
    if k == 1: return P
    k = k % n
    J = (0, 1, 0)
    B = to_jac(P)
    while k > 0:
        if k & 1:
            J = j_add(J, B)
        B = j_double(B)
        k >>= 1
    return from_jac(J)

def ec_neg(P):
    if P is None: return None
    x, y = P
    return (x, (-y) % p)

# =========================
# Public key lifting (02/03 + x)
# =========================
def lift_compressed(hex_str):
    h = hex_str.lower()
    if h.startswith("0x"): h = h[2:]
    if len(h) != 66 or h[:2] not in ("02", "03"):
        raise ValueError("Compressed pubkey must be 33 bytes hex starting 02/03")
    prefix = int(h[:2], 16)
    x = int(h[2:], 16)
    y2 = (pow(x, 3, p) + 7) % p
    y = tonelli(y2)
    if (y & 1) != (prefix & 1):
        y = (-y) % p
    return (x, y)

# =========================
# Endomorphism identities
# =========================
def check_endomorphisms():
    print("=== Step 0: Verify group/endomorphism identities ===")
    print(f"p = {p}")
    print(f"n = {n}")
    ok_beta = pow(beta, 3, p) == 1
    ok_lam  = pow(lam,  3, n) == 1
    print(f"beta^3 mod p == 1? {ok_beta}")
    print(f"lambda^3 mod n == 1? {ok_lam}")
    print(f"mu = lambda + 1 mod n: {mu}")
    print(f"mu^2 == lambda? {pow(mu, 2, n) == lam}")
    print(f"mu^3 == -1 mod n? {pow(mu, 3, n) == (n-1)%n}")
    print(f"mu^6 == 1 mod n? {pow(mu, 6, n) == 1}")
    # φλ(P) = (β x, y) check on random scalar
    import random
    k = random.randrange(1, 2**64)
    P = ec_mul(k, G)
    betaP = ( (P[0]*beta) % p, P[1] )
    lamP = ec_mul(lam, P)
    print(f"phi_lambda(P) equals lambda*P for a random P? {betaP == lamP}")
    print()

# =========================
# Sixth-root scale r
# =========================
def compute_r():
    r = int(n ** (1/6))
    # ensure exact floor
    while (r+1)**6 <= n: r += 1
    while (r)**6 > n: r -= 1
    return r

def print_r_sanity(r):
    print("=== Step 1: Sixth-root scale r ===")
    print(f"r = floor(n^(1/6)) = {r} (~2^{math.log2(r):.5f})")
    ok_bounds = (r**6 <= n) and ((r+1)**6 > n)
    print(f"Check: r^6 <= n < (r+1)^6 ? {ok_bounds}")
    print()

# =========================
# Σ* signature (ordered β-orbit + position + parity)
# =========================
def sigma_star(P):
    """Return 20-byte digest stable under negation via [6]P; encodes ordering + parity."""
    if P is None:
        return b'\x00'*20
    Q = ec_mul(6, P)
    if Q is None:
        return b'\x00'*20
    x, y = Q
    x1 = (x * beta) % p
    x2 = (x1 * beta) % p
    triple = [x, x1, x2]
    sorted_triple = sorted(triple)
    pos = sorted_triple.index(x)  # where x lands in sorted triple (0..2)
    parity = y & 1                # y parity of [6]P
    h = hashlib.sha256()
    for v in sorted_triple:
        h.update(v.to_bytes(32, 'big'))
    h.update(bytes([pos, parity]))
    return h.digest()[:20]

# =========================
# CRT helpers
# =========================
def gcd(a,b):
    while b: a,b = b, a%b
    return a

def crt_reconstruct(j_list, mod_list):
    assert len(j_list) == len(mod_list)
    M = 1
    for m in mod_list: M *= m
    acc = 0
    for j, m in zip(j_list, mod_list):
        Mk = M // m
        inv = modinv(Mk % m, m)
        acc = (acc + j * Mk * inv) % M
    return acc, M

# =========================
# Baby tables (BSGS flavor, size M), per CRT modulus for small memory
# =========================
def build_baby_tables(M, verbose=True):
    """
    Build 3 baby tables keyed by Σ*( [6](jG) ), value=j for j in [0,M).
    Memory ~ 3*M entries; each key 20B + small int; Python dict overhead applies.
    """
    if verbose:
        print("=== Step 2: Build baby tables (CRT-split) ===")
    H6 = ec_mul(6, G)
    tables = []
    for idx, r_i in enumerate(CRT_MODS):
        if verbose:
            print(f"  • Building table for modulus r_{idx+1} = {r_i} with M = {M} entries ...")
        baby = {}
        X = None
        # j=0 maps to Σ*(∞) => sentinel; still ok for uniformity
        for j in range(M):
            sig = sigma_star(X)
            if sig not in baby:
                baby[sig] = j
            X = ec_add(X, H6)
        tables.append(baby)
        if verbose:
            print(f"    Table {idx+1} size: {len(baby)} (unique signatures)")
    if verbose:
        print()
    return tables

# =========================
# μ-lane search: giant counter t is b_i
# =========================
def recover_with_crt_mu(pub_P, M, r, max_giants=None, log_every=20000):
    print("=== Step 3: μ-lane giants (CRT intersect) ===")
    # sanity print for CRT
    print(f"CRT moduli: r1={CRT_MODS[0]}, r2={CRT_MODS[1]}, r3={CRT_MODS[2]}")
    pairwise = [gcd(CRT_MODS[i], CRT_MODS[j]) for i in range(3) for j in range(i+1,3)]
    print(f"Pairwise gcds: {pairwise} (all must be 1)")
    print(f"CRT product R = r1*r2*r3 = {CRT_PROD} (~2^{math.log2(CRT_PROD):.5f})")
    print(f"Sixth-root r = {r} (~2^{math.log2(r):.5f})")
    print(f"Coverage: R - r = {CRT_PROD - r}  (R > r ? {CRT_PROD > r})")
    print()
    print("Memory sketch:")
    print(f"  Baby entries per modulus: M={M}")
    print(f"  Keys stored per modulus (20 bytes digest) + int => ~{M*28/1e6:.1f} MB raw each; Python dict overhead extra")
    print(f"  Total (3 tables): ~{3*M*28/1e6:.1f} MB raw + overhead")
    print()

    babies = build_baby_tables(M, verbose=False)

    # μ^i and inverses
    mu_pows = [pow(mu, i, n) for i in range(6)]
    mu_inv_pows = [modinv(mu_pows[i], n) for i in range(6)]

    # lane targets: T_i = [6]([μ^i] P)
    lane_targets = []
    for i in range(6):
        T = ec_mul(mu_pows[i], pub_P)
        T6 = ec_mul(6, T)
        lane_targets.append(T6)

    # per-modulus step: [6](r_i G)
    R6 = [ec_mul(6*ri, G) for ri in CRT_MODS]

    t = 0
    start = time.time()
    while True:
        if max_giants is not None and t > max_giants:
            print(f"[!] Reached max_giants={max_giants} without hit.")
            return None

        if (t % log_every) == 0:
            dt = time.time() - start
            print(f"  t={t:,} (elapsed {dt:.1f}s) ...")

        for i in range(6):
            hits = []
            for m_idx in range(3):
                # Q_i(t) = lane_targets[i] - t * [6](r_m G)
                tR = ec_mul(t, R6[m_idx])
                if tR is None:
                    Q = lane_targets[i]
                else:
                    Q = ec_add(lane_targets[i], ec_neg(tR))
                sig = sigma_star(Q)
                j = babies[m_idx].get(sig)
                if j is None:
                    break
                hits.append(j)

            if len(hits) == 3:
                # CRT reconstruct a_i mod CRT_PROD
                a_mod, Mcrt = crt_reconstruct(hits, CRT_MODS)
                a_i = a_mod if Mcrt >= r else (a_mod % r)
                b_i = t
                s_i = (a_i + b_i * r) % n
                k = (s_i * mu_inv_pows[i]) % n

                # verify
                if ec_mul(k, G) == pub_P:
                    elapsed = time.time() - start
                    print("\n=== HIT ===")
                    print(f"lane i = {i}")
                    print(f"j (per modulus) = {hits}  -> CRT a_i = {a_i}")
                    print(f"b_i = t = {b_i}")
                    print(f"s_i = a_i + b_i * r  (mod n) = {s_i}")
                    print(f"μ^{-i} = {mu_inv_pows[i]}")
                    print(f"k = s_i * μ^{-i} (mod n) = {k}")
                    print(f"Verify: [k]G == P ? {ec_mul(k, G) == pub_P}")
                    print(f"Elapsed: {elapsed:.2f}s")
                    return k

        t += 1

# =========================
# Sanity block: CRT & r prints
# =========================
def print_crt_and_r_sanity(r):
    print("=== Step 2: CRT split sanity ===")
    print(f"r1 = {CRT_MODS[0]}, r2 = {CRT_MODS[1]}, r3 = {CRT_MODS[2]}")
    g12 = gcd(CRT_MODS[0], CRT_MODS[1])
    g13 = gcd(CRT_MODS[0], CRT_MODS[2])
    g23 = gcd(CRT_MODS[1], CRT_MODS[2])
    print(f"pairwise gcds: (r1,r2)={g12}, (r1,r3)={g13}, (r2,r3)={g23}  (should all be 1)")
    R = CRT_PROD
    print(f"Product R = r1*r2*r3 = {R} (~2^{math.log2(R):.5f})")
    print(f"Sixth-root scale r = {r} (~2^{math.log2(r):.5f})")
    print(f"Coverage: R - r = {R - r}  (R > r ? {R > r})")
    print("\nMemory accounting (rule of thumb):")
    print("  If you use M ≈ 2^21.5 per baby in a pure BSGS: a few hundred MB (dict overhead dominates).")
    print("  If you use the per-modulus scan (M ≈ r_i ≈ 2^15): ~1MB per table raw, 3MB total + overhead.")
    print()

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="μ/CRT/Σ* attack scaffolding (research demo)")
    ap.add_argument("pubkey", help="Compressed public key hex (33 bytes, 02/03...)")
    ap.add_argument("--M", type=int, default=1<<20, help="Baby size M (default 2^20)")
    ap.add_argument("--max-giants", type=int, default=5000000, help="Cap giants per lane (default 5e6)")
    ap.add_argument("--sanity-only", action="store_true", help="Only print invariants/sanity, then exit")
    args = ap.parse_args()

    # Step 0: identities
    check_endomorphisms()

    # Step 1: sixth-root r
    r_val = compute_r()
    print_r_sanity(r_val)

    # Step 2: CRT sanity
    print_crt_and_r_sanity(r_val)

    if args.sanity_only:
        print("[sanity-only] Done.")
        return

    # Lift pubkey
    try:
        P = lift_compressed(args.pubkey)
    except Exception as e:
        print(f"Error lifting pubkey: {e}")
        sys.exit(1)

    print("=== Step 3: Target pubkey ===")
    print(f"P.x = 0x{P[0]:064x}")
    print(f"P.y = 0x{P[1]:064x}")
    print()

    # Build babies and run μ-lane CRT giants
    print("=== Step 4: Build baby tables ===")
    babies = build_baby_tables(args.M, verbose=True)

    print("=== Step 5: Giants / matching ===")
    k = recover_with_crt_mu(P, args.M, r_val, max_giants=args.max_giants)

    if k is None:
        print("\nNo hit within limits. Try increasing --M and/or --max-giants (and parallelize).")
    else:
        print("\n=== RESULT ===")
        print(f"Recovered k = 0x{k:x}")
        print(f"Check: [k]G == P ? {ec_mul(k, G) == P}")

if __name__ == "__main__":
    main()

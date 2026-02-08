#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
secp256k1 μ/CRT recovery + BSGS a_i demo (choose with --mode)

Modes:
  --mode crt   : SOLVING mode. μ-lanes (i=0..5), per-modulus CRT tables.
                 Giant counter t equals b_i. When 3-way CRT hits, reconstruct a_i,
                 compute s_i = a_i + b_i*r, then k = s_i * μ^{-i} (mod n).
  --mode bsgs  : DEMO mode. Classic BSGS for a_i < r, stepping by M.
                 Prints (lane i, a_i) hits but does NOT recover k (b_i unknown in this mode).

CLI examples:
  python3 recover_k_mu_crt_bsgs.py <pubhex> --sanity-only
  python3 recover_k_mu_crt_bsgs.py <pubhex> --mode crt  --max-giants 20000000
  python3 recover_k_mu_crt_bsgs.py <pubhex> --mode bsgs --M 2097152
"""

import sys, math, argparse, time, hashlib
from collections import defaultdict
from itertools import product

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

# CRT moduli (pairwise coprime) → product ~ 2^43
CRT_MODS = [32749, 32771, 8191]
CRT_PROD = CRT_MODS[0]*CRT_MODS[1]*CRT_MODS[2]

# =========================
# Basic field helpers
# =========================
def modinv(a, m):
    return pow(a, -1, m)

def tonelli(y2):
    # p % 4 == 3 for secp256k1
    return pow(y2, (p+1)//4, p)

# =========================
# Jacobian EC arithmetic (fast & exact)
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
# Endomorphism sanity
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
# Injective signature over [6]P (compressed point digest)
# =========================
def sigma_star(P):
    """20-byte digest of the compressed [6]P. Injective for the exact point (2^-160 collision prob)."""
    if P is None:
        return b'\x00'*20
    Q = ec_mul(6, P)
    if Q is None:
        return b'\x00'*20
    x, y = Q
    prefix = 2 + (y & 1)            # 0x02 / 0x03
    h = hashlib.sha256()
    h.update(bytes([prefix]))
    h.update(x.to_bytes(32, 'big'))
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
# Build babies (two variants)
# =========================
def build_babies_crt(verbose=True):
    """
    Build 3 baby tables keyed by σ([6](jG)) with j in [0, r_i).
    Store a *list* of j’s per signature (do NOT drop collisions).
    """
    if verbose:
        print("=== Step 2A: Build baby tables (CRT-scan) ===")
    H6 = ec_mul(6, G)
    tables = []
    for idx, r_i in enumerate(CRT_MODS):
        if verbose:
            print(f"  • Building table for modulus r_{idx+1} = {r_i} (size = r_i)")
        baby = defaultdict(list)
        X = None
        for j in range(r_i):
            sig = sigma_star(X)
            baby[sig].append(j)          # keep *all* representatives for this signature
            X = ec_add(X, H6)
        if verbose:
            unique = sum(1 for _ in baby.keys())
            multi  = sum(1 for v in baby.values() if len(v) > 1)
            print(f"    Table {idx+1}: entries={r_i}, unique_sigs={unique}, multihit_sigs={multi}")
        tables.append(baby)
    if verbose:
        print()
    return tables

def build_baby_bsgs(M, verbose=True):
    """
    Classic BSGS baby: store σ([6](jG)) for j in [0, M). Keep all j’s per signature.
    """
    if verbose:
        print("=== Step 2B: Build baby table (BSGS for a_i) ===")
        print(f"  • M = {M}")
    H6 = ec_mul(6, G)
    baby = defaultdict(list)
    X = None
    for j in range(M):
        sig = sigma_star(X)
        baby[sig].append(j)
        X = ec_add(X, H6)
    if verbose:
        unique = sum(1 for _ in baby.keys())
        multi  = sum(1 for v in baby.values() if len(v) > 1)
        print(f"    Unique signatures = {unique}; multihit_sigs = {multi}\n")
    return baby

# =========================
# MODE 1: μ/CRT per-modulus scan (SOLVES k)
# =========================
def recover_crt_mode(pub_P, r, max_giants, log_every=20000):
    print("=== Step 3A: μ-lane giants (CRT intersect, solving mode) ===")
    print(f"CRT moduli: {CRT_MODS}")
    pairwise = [gcd(CRT_MODS[i], CRT_MODS[j]) for i in range(3) for j in range(i+1,3)]
    print(f"Pairwise gcds: {pairwise}  (all must be 1)")
    print(f"CRT product R = {CRT_PROD} (~2^{math.log2(CRT_PROD):.5f})")
    print(f"Sixth-root r  = {r} (~2^{math.log2(r):.5f})")
    print(f"Coverage: R - r = {CRT_PROD - r}  (R > r ? {CRT_PROD > r})\n")

    babies = build_babies_crt(verbose=False)

    mu_pows = [pow(mu, i, n) for i in range(6)]
    mu_inv_pows = [modinv(mu_pows[i], n) for i in range(6)]

    # Lane targets: [6]([μ^i]P)
    lane_targets = [ec_mul(6, ec_mul(mu_pows[i], pub_P)) for i in range(6)]
    # Per-modulus step: [6](r_i G)
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
            candidate_lists = []
            for m_idx in range(3):
                tR = ec_mul(t, R6[m_idx])
                Q = lane_targets[i] if tR is None else ec_add(lane_targets[i], ec_neg(tR))
                sig = sigma_star(Q)
                js = babies[m_idx].get(sig)
                if not js:
                    candidate_lists = []
                    break
                # reduce reps mod r_i to be safe
                candidate_lists.append([jj % CRT_MODS[m_idx] for jj in js])

            if len(candidate_lists) == 3:
                # Try all combinations of (j1, j2, j3)
                for j_trip in product(candidate_lists[0], candidate_lists[1], candidate_lists[2]):
                    a_mod, Mcrt = crt_reconstruct(list(j_trip), CRT_MODS)
                    a_i = a_mod if Mcrt >= r else (a_mod % r)
                    b_i = t
                    s_i = (a_i + b_i * r) % n
                    k = (s_i * mu_inv_pows[i]) % n
                    if ec_mul(k, G) == pub_P:
                        elapsed = time.time() - start
                        print("\n=== HIT (SOLVED) ===")
                        print(f"lane i = {i}")
                        print(f"hits lists sizes = {[len(lst) for lst in candidate_lists]}")
                        print(f"picked (j1,j2,j3) = {j_trip}")
                        print(f"CRT a_i = {a_i}")
                        print(f"b_i = t = {b_i}")
                        print(f"s_i = a_i + b_i * r (mod n) = {s_i}")
                        print(f"μ^{-i} = {mu_inv_pows[i]}")
                        print(f"k = s_i * μ^{-i} (mod n) = {k}")
                        print(f"Verify: [k]G == P ? {ec_mul(k, G) == pub_P}")
                        print(f"Elapsed: {elapsed:.2f}s")
                        return k

        t += 1

# =========================
# MODE 2: Classic BSGS for a_i (DEMO only)
# =========================
def demo_bsgs_ai(pub_P, r, M, log_every=50000):
    """
    Build a single baby table of size M on σ([6](jG)).
    For each μ-lane, walk Q_i(t) = σ([6]([μ^i]P - t*[M]G)).
    A match implies j + t*M == a_i (actual small residue < r).
    We output (i, a_i) when 0 <= a_i < r. Does NOT recover k (b_i unknown).
    """
    print("=== Step 3B: Classic BSGS for a_i (DEMO mode, not solving k) ===")
    print(f"√r target scale: r ≈ {r} (~2^{math.log2(r):.3f}); recommend M ≈ 2^{math.log2(r)/2:.1f}")
    baby = build_baby_bsgs(M, verbose=True)

    mu_pows = [pow(mu, i, n) for i in range(6)]
    lane_targets = [ec_mul(6, ec_mul(mu_pows[i], pub_P)) for i in range(6)]
    # BSGS step: [6](M G)
    step = ec_mul(6*M, G)

    found = []
    t = 0
    start = time.time()
    t_limit = (r + M - 1)//M
    print(f"Giants per lane (≈ r/M) = {t_limit}")
    while t <= t_limit:
        if (t % log_every) == 0:
            dt = time.time() - start
            print(f"  t={t:,} (elapsed {dt:.1f}s) ...")

        tStep = ec_mul(t, step)  # [6](t*M G)
        for i in range(6):
            Q = ec_add(lane_targets[i], ec_neg(tStep))
            sig = sigma_star(Q)
            js = baby.get(sig)
            if js:
                for j in js:
                    a_i = j + t*M
                    if a_i < r:
                        print(f"[*] lane i={i}: a_i = {a_i}  (j={j}, t={t})")
                        found.append((i, a_i))
        t += 1

    if not found:
        print("No a_i hit found within limits.")
    else:
        print("\nSummary of found a_i (lane, a_i):")
        for rec in found:
            print(" ", rec)
    print("\nNOTE: This DEMO does not recover k; it only exhibits the < 2^43 residues a_i.")

# =========================
# CLI
# =========================
def main():
    ap = argparse.ArgumentParser(description="μ/CRT (solve) and BSGS (demo) for secp256k1")
    ap.add_argument("pubkey", help="Compressed public key hex (33 bytes, 02/03...)")
    ap.add_argument("--mode", choices=["crt","bsgs"], default="crt",
                    help="crt = solve k via μ/CRT; bsgs = demo a_i only")
    ap.add_argument("--M", type=int, default=1<<20,
                    help="baby size: for crt ignored (uses r_i); for bsgs default 2^20")
    ap.add_argument("--max-giants", type=int, default=5_000_000,
                    help="[crt] cap giants per lane (default 5e6)")
    ap.add_argument("--sanity-only", action="store_true",
                    help="Only print invariants/sanity, then exit")
    args = ap.parse_args()

    # Step 0: identities
    check_endomorphisms()

    # Step 1: sixth-root r
    r_val = compute_r()
    print_r_sanity(r_val)

    # CRT sanity
    print("=== Step 2: CRT split sanity ===")
    print(f"r1 = {CRT_MODS[0]}, r2 = {CRT_MODS[1]}, r3 = {CRT_MODS[2]}")
    g12 = gcd(CRT_MODS[0], CRT_MODS[1])
    g13 = gcd(CRT_MODS[0], CRT_MODS[2])
    g23 = gcd(CRT_MODS[1], CRT_MODS[2])
    print(f"pairwise gcds: (r1,r2)={g12}, (r1,r3)={g13}, (r2,r3)={g23}  (should all be 1)")
    R = CRT_PROD
    print(f"Product R = r1*r2*r3 = {R} (~2^{math.log2(R):.5f})")
    print(f"Sixth-root scale r = {r_val} (~2^{math.log2(r_val):.5f})")
    print(f"Coverage: R - r = {R - r_val}  (R > r ? {R > r_val})\n")

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
    print(f"P.y = 0x{P[1]:064x}\n")

    if args.mode == "crt":
        # Solve with μ/CRT scan (tables = r_i each)
        k = recover_crt_mode(P, r_val, args.max_giants)
        if k is None:
            print("\nNo hit within limits. Increase --max-giants and/or parallelize.")
        else:
            print("\n=== RESULT ===")
            print(f"Recovered k = 0x{k:x}")
            print(f"Check: [k]G == P ? {ec_mul(k, G) == P}")

    else:
        # Demo classic BSGS (a_i only)
        demo_bsgs_ai(P, r_val, args.M)

if __name__ == "__main__":
    main()

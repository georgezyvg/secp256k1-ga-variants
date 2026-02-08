import numpy as np
from collections import Counter
from math import log2

def hex_to_binary_array(hex_str):
    scale = 16
    num_of_bits = len(hex_str) * 4
    bin_str = bin(int(hex_str, scale))[2:].zfill(num_of_bits)
    return np.array([int(b) for b in bin_str])

def extract_bits_at_interval(bit_array, interval):
    return bit_array[::interval]

def entropy(bits):
    count = Counter(bits)
    total = len(bits)
    ent = 0
    for c in count.values():
        p = c / total
        ent -= p * log2(p)
    return ent

def correlation_test(bits, nonce_candidates):
    correlations = []
    for candidate in nonce_candidates:
        min_len = min(len(bits), len(candidate))
        match = np.sum(bits[:min_len] == candidate[:min_len])
        corr = match / min_len
        correlations.append(corr)
    return correlations

def narrow_keyspace(correlations, threshold=0.8):
    return [i for i, corr in enumerate(correlations) if corr >= threshold]

def generate_nonce_candidates(length, count):
    np.random.seed(42)
    return [np.random.randint(0, 2, length) for _ in range(count)]

# Parameters
hash160 = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"  # example hash160
bit_array = hex_to_binary_array(hash160)
intervals = [1, 15, 30]  # example intervals from harmonic peaks

# Generate nonce candidates with length matching smallest extracted sequence
min_interval = min(intervals)
nonce_length = len(bit_array) // min_interval
nonce_candidates = generate_nonce_candidates(nonce_length, 1000)  # generate 1000 candidates

for interval in intervals:
    extracted = extract_bits_at_interval(bit_array, interval)
    ent = entropy(extracted)
    print(f"Interval {interval}: Extracted bits count = {len(extracted)}, Entropy = {ent:.4f}")

    correlations = correlation_test(extracted, nonce_candidates)
    narrowed = narrow_keyspace(correlations, threshold=0.8)
    print(f"Correlation scores (top 5): {sorted(correlations, reverse=True)[:5]}")
    print(f"Candidates passing threshold: {len(narrowed)}")
    print("-"*40)

import hashlib
from Crypto.Hash import RIPEMD160
from coincurve import PrivateKey

# Your data
best_key_hex = "91a9e8edebe35a36fd8931e49e6d59ef28dce0db10af57ab62e581406fafccf9"
target_hash160_hex = "ad0cd5cef7d55cf09455be4c97581b28483b8361"
COMPRESSED = True

def hash160(pubkey_bytes):
    sha = hashlib.sha256(pubkey_bytes).digest()
    rip = RIPEMD160.new(sha).digest()
    return rip

def hamming_distance(b1, b2):
    return sum(bin(a ^ b).count('1') for a, b in zip(b1, b2))

key_int = int(best_key_hex, 16)
target_hash = bytes.fromhex(target_hash160_hex)
WALK_RANGE = 2**40

print(f"Walking ±2^40 ({WALK_RANGE:,}) from best key: {best_key_hex}")
print("Logs every 100,000 steps. Ctrl+C to interrupt.")

found = False
try:
    for delta in range(WALK_RANGE + 1):
        for sign in [1, -1]:
            candidate = key_int + sign * delta
            if candidate <= 0 or candidate >= 2**256:
                continue
            key_bytes = candidate.to_bytes(32, "big")
            try:
                priv = PrivateKey(key_bytes)
                pub = priv.public_key.format(compressed=COMPRESSED)
                h160 = hash160(pub)
                if h160 == target_hash:
                    print(f"\n🎉 FOUND! Key: {key_bytes.hex()}")
                    print(f"Decimal: {candidate}")
                    print(f"Steps from GA: {sign * delta} ({'up' if sign == 1 else 'down'})")
                    found = True
                    break
                if delta % 100_000 == 0 and sign == 1:
                    hd = hamming_distance(h160, target_hash)
                    print(f"Step {delta:,} {('up' if sign == 1 else 'down')}, Key: {key_bytes.hex()}, Hamming: {hd}")
            except Exception:
                continue
        if found:
            break
    if not found:
        print(f"\nNo match found within ±2^40 steps.")
except KeyboardInterrupt:
    print(f"\nWalk interrupted by user. No match found.")


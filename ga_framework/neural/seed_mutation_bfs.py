import hashlib
import string
import base58
from ecdsa import SigningKey, SECP256k1
import heapq

# CONFIG:
TARGET_ADDRESS = '1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF'
YOUR_BEST_SEED = 'mtgox-tx-1298975179.003214574-e67a0550848b7932d7796aeea16ab0e48a5cfe81c4e8cca2b5b03e0416850114'
CHARS = string.ascii_letters + string.digits + ' _-.'
MAX_EDITS = 94
TOP_N = 20

def sha256(data):
    return hashlib.sha256(data.encode('utf-8')).digest()

def privkey_to_address(privkey_bytes):
    sk = SigningKey.from_string(privkey_bytes, curve=SECP256k1)
    vk = sk.verifying_key
    pubkey_bytes = b'\x04' + vk.to_string()
    h160 = hashlib.new('ripemd160', hashlib.sha256(pubkey_bytes).digest()).digest()
    prefix_h160 = b'\x00' + h160
    checksum = hashlib.sha256(hashlib.sha256(prefix_h160).digest()).digest()[:4]
    addr_bytes = prefix_h160 + checksum
    return base58.b58encode(addr_bytes).decode()

def generate_mutations(seed, max_edits=1):
    seen = set()
    queue = [(seed, 0)]
    while queue:
        s, edits = queue.pop(0)
        if (s, edits) in seen or edits > max_edits:
            continue
        seen.add((s, edits))
        yield s
        if edits == max_edits:
            continue
        # Substitution
        for i in range(len(s)):
            for c in CHARS:
                if c != s[i]:
                    queue.append((s[:i] + c + s[i+1:], edits + 1))
        # Insertion
        for i in range(len(s)+1):
            for c in CHARS:
                queue.append((s[:i] + c + s[i:], edits + 1))
        # Deletion
        for i in range(len(s)):
            queue.append((s[:i] + s[i+1:], edits + 1))
        # Swap adjacent
        for i in range(len(s)-1):
            queue.append((s[:i] + s[i+1] + s[i] + s[i+2:], edits + 1))
        # Case toggle
        for i in range(len(s)):
            if s[i].isalpha():
                swapped = s[:i] + (s[i].upper() if s[i].islower() else s[i].lower()) + s[i+1:]
                queue.append((swapped, edits + 1))

def match_score(addr1, addr2):
    # Number of matching chars from the start (prefix)
    score = 0
    for a, b in zip(addr1, addr2):
        if a == b:
            score += 1
        else:
            break
    return score

if __name__ == '__main__':
    import heapq

    tried = set()
    count = 0
    top_candidates = []

    for candidate in generate_mutations(YOUR_BEST_SEED, MAX_EDITS):
        if candidate in tried:
            continue
        tried.add(candidate)
        try:
            priv = sha256(candidate)
            addr = privkey_to_address(priv)
            count += 1
            if addr == TARGET_ADDRESS:
                print(f'\nFOUND IT!\nSeed: {candidate}\n')
                break
            else:
                score = match_score(addr, TARGET_ADDRESS)
                if len(top_candidates) < TOP_N:
                    heapq.heappush(top_candidates, (score, candidate, addr))
                else:
                    heapq.heappushpop(top_candidates, (score, candidate, addr))
                if count % 1000 == 0:
                    print(f"Tried {count} seeds so far. Latest: {candidate} -> {addr} (score: {score})")
        except Exception as e:
            continue

    # After brute, print top 20
    print("\n==== Top 20 Closest Results ====")
    top_candidates = sorted(top_candidates, key=lambda x: -x[0])
    for i, (score, candidate, addr) in enumerate(top_candidates, 1):
        print(f"{i:2d}. Seed: {candidate}")
        print(f"    Addr: {addr}")
        print(f"    Match score: {score}\n")

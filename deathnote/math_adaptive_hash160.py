import hashlib
import hmac
import itertools
from datetime import datetime, timedelta
import time
import struct
import os
import gc

# Set up disk-based working directory
WORK_DIR = "brain_wallet_search"
if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)

print("=== BITCOIN BRAIN WALLET EXHAUSTIVE RECOVERY - SSD OPTIMIZED ===")
print(f"Using disk at: {os.path.abspath(WORK_DIR)}")
print()
target_address = input("Enter your Bitcoin address (starts with 1): ").strip()

# Save target to disk
with open(os.path.join(WORK_DIR, "target.txt"), "w") as f:
    f.write(target_address)

print(f"\nTarget address: {target_address}")
print("\nStarting SSD-optimized search...\n")

# Bitcoin functions (same as before)
def modular_inverse(a, m):
    def extended_gcd(a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y
    
    _, x, _ = extended_gcd(a % m, m)
    return (x % m + m) % m

def point_add(p1, p2, p_mod):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    
    x1, y1 = p1
    x2, y2 = p2
    
    if x1 == x2:
        if y1 == y2:
            s = (3 * x1 * x1 * modular_inverse(2 * y1, p_mod)) % p_mod
        else:
            return None
    else:
        s = ((y2 - y1) * modular_inverse(x2 - x1, p_mod)) % p_mod
    
    x3 = (s * s - x1 - x2) % p_mod
    y3 = (s * (x1 - x3) - y1) % p_mod
    
    return (x3, y3)

def point_multiply(k, point, p_mod):
    if k == 0:
        return None
    if k == 1:
        return point
    
    result = None
    addend = point
    
    while k:
        if k & 1:
            result = point_add(result, addend, p_mod)
        addend = point_add(addend, addend, p_mod)
        k >>= 1
    
    return result

def private_key_to_public_key_uncompressed(private_key_hex):
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
         0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
    
    private_key = int(private_key_hex, 16)
    public_key_point = point_multiply(private_key, G, p)
    
    if public_key_point is None:
        return None
    
    x, y = public_key_point
    return b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')

def public_key_to_address(public_key_bytes):
    sha256_hash = hashlib.sha256(public_key_bytes).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    public_key_hash = ripemd160.digest()
    versioned = b'\x00' + public_key_hash
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    address_bytes = versioned + checksum
    
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    num = int.from_bytes(address_bytes, 'big')
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = alphabet[remainder] + encoded
    
    for byte in address_bytes:
        if byte == 0:
            encoded = '1' + encoded
        else:
            break
    
    return encoded

def private_key_to_address_uncompressed(private_key_hex):
    public_key = private_key_to_public_key_uncompressed(private_key_hex)
    if public_key:
        return public_key_to_address(public_key)
    return None

def check_similarity(address1, address2):
    if not address1 or not address2:
        return False, ""
    
    if address1 == address2:
        return True, "EXACT MATCH!!!"
    
    if address1.lower() == address2.lower():
        return True, "EXACT MATCH (case insensitive)"
    
    if len(address2) > 10 and address2 in address1:
        return True, f"TARGET IN GENERATED"
    if len(address1) > 10 and address1 in address2:
        return True, f"GENERATED IN TARGET"
    
    for n in range(3, min(len(address1), len(address2))):
        if address1[:n] == address2[:n]:
            match_quality = "STRONG" if n >= 8 else "GOOD" if n >= 6 else "WEAK"
            return True, f"FIRST {n} CHARS MATCH ({match_quality})"
    
    for n in range(3, min(len(address1), len(address2))):
        if address1[-n:] == address2[-n:]:
            match_quality = "STRONG" if n >= 6 else "GOOD" if n >= 4 else "WEAK"
            return True, f"LAST {n} CHARS MATCH ({match_quality})"
    
    matches = sum(1 for a, b in zip(address1, address2) if a == b)
    similarity = matches / max(len(address1), len(address2))
    if similarity > 0.5:
        return True, f"SIMILARITY: {similarity:.1%} ({matches}/{max(len(address1), len(address2))} chars match)"
    
    return False, ""

# GENERATORS - Don't store in memory!
def generate_timestamps_streaming():
    """Generator that yields timestamps one at a time"""
    start = 1298851200  # Feb 28, 2011 00:00:00
    end = 1299110400    # Mar 2, 2011 23:59:59
    
    for ts in range(start, end + 1):
        yield str(ts)
        
        # Generate microseconds in chunks to avoid memory issues
        for micro_chunk_start in range(0, 1000000, 1000):
            for micro in range(micro_chunk_start, min(micro_chunk_start + 1000, 1000000)):
                yield f"{ts}.{micro:06d}"
                yield f"{ts}.{micro:05d}"
                yield f"{ts}.{micro:04d}"
                yield f"{ts}.{micro:03d}"
                yield f"{ts}.{micro:02d}"
                yield f"{ts}.{micro:01d}"
                yield f"{ts}.{micro}"
                yield f"{ts}.{str(micro)}"
                yield f"{ts}.{str(micro).zfill(6)}"
                yield f"{ts}.{str(micro).zfill(5)}"
                yield f"{ts}.{str(micro).zfill(4)}"
                yield f"{ts}.{str(micro).zfill(3)}"
                yield f"{ts}.{str(micro).zfill(2)}"
                
                yield f"0.{micro:06d} {ts}"
                yield f"0.{micro:05d} {ts}"
                yield f"0.{micro:04d} {ts}"
                yield f"0.{micro:03d} {ts}"
                yield f"0.{micro:02d} {ts}"
                yield f"0.{micro:01d} {ts}"
                yield f"0.{micro} {ts}"
                
                decimal_value = micro / 1000000
                yield f"{decimal_value:.6f} {ts}"
                yield f"{decimal_value:.5f} {ts}"
                yield f"{decimal_value:.4f} {ts}"
                yield f"{decimal_value:.3f} {ts}"
                yield f"{decimal_value:.2f} {ts}"
                yield f"{decimal_value:.1f} {ts}"
                yield f"{decimal_value} {ts}"
        
        # Date formats
        dt = datetime.fromtimestamp(ts)
        date_formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y_%m_%d", "%Y %m %d",
            "%m-%d-%Y", "%m/%d/%Y", "%m.%d.%Y", "%m_%d_%Y", "%m %d %Y",
            "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d_%m_%Y", "%d %m %Y",
            "%Y%m%d", "%y%m%d", "%m%d%Y", "%d%m%Y", "%m%d%y", "%d%m%y",
            "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y.%m.%d %H:%M:%S",
            "%Y-%m-%d-%H-%M-%S", "%Y/%m/%d/%H/%M/%S", "%Y.%m.%d.%H.%M.%S",
            "%Y%m%d%H%M%S", "%y%m%d%H%M%S", "%s"
        ]
        
        for fmt in date_formats:
            try:
                yield dt.strftime(fmt)
            except:
                pass
        
        yield str(int(ts * 1000))
        yield str(int(ts * 1000000))

def generate_pids_streaming():
    """Generator that yields PIDs one at a time"""
    for pid in range(0, 65536):
        yield str(pid)
        for width in range(1, 7):
            yield str(pid).zfill(width)
        
        yield hex(pid)
        yield hex(pid)[2:]
        yield hex(pid)[2:].upper()
        yield f"0x{pid:x}"
        yield f"0x{pid:X}"
        for width in range(1, 6):
            yield f"0x{pid:0{width}x}"
            yield f"0x{pid:0{width}X}"
        
        yield oct(pid)
        yield oct(pid)[2:]
    
    special_pids = [
        '$$', '$PID', '${PID}', 'pid', 'PID', 'getmypid()', 'getmypid',
        'process', 'PROCESS', 'null', 'NULL', 'none', 'NONE', '', '-', '0'
    ]
    for sp in special_pids:
        yield sp

def generate_phrase_variants(timestamp, pid):
    """Generate phrase variants on-the-fly"""
    mtgox_variants = [
        'mtgox', 'MtGox', 'MTGOX', 'mtGox', 'Mt.Gox', 'mt.gox', 'Mt-Gox'
    ]
    
    separators = ['-', '_', '.', ':', '', ' ', ',', '|', '/']
    brackets = [('', ''), ('(', ')'), ('[', ']'), ('{', '}')]
    
    for mtgox in mtgox_variants:
        for components in itertools.permutations([mtgox, timestamp, pid]):
            for sep in separators:
                phrase = sep.join(map(str, components))
                for start_bracket, end_bracket in brackets:
                    yield f"{start_bracket}{phrase}{end_bracket}"

def derive_keypool_key(seed_phrase, index):
    """Generate keypool keys on-the-fly"""
    # Direct hash
    yield ("direct", hashlib.sha256(seed_phrase.encode()).hexdigest())
    
    # With index
    separators = ['', ':', '-', '_', '.']
    for sep in separators:
        yield (f"concat_{sep}", hashlib.sha256(f"{seed_phrase}{sep}{index}".encode()).hexdigest())
        yield (f"index_first_{sep}", hashlib.sha256(f"{index}{sep}{seed_phrase}".encode()).hexdigest())
    
    # HMAC
    yield ("hmac_sha256", hmac.new(seed_phrase.encode(), str(index).encode(), hashlib.sha256).hexdigest())
    
    # Iterations
    for iterations in [1, 2, 5, 10, 25, 50, 100]:
        temp = seed_phrase
        for i in range(iterations):
            temp = hashlib.sha256(f"{temp}{index}".encode()).hexdigest()
        yield (f"iter_{iterations}", temp)

def main_search():
    """Main search using generators to save memory"""
    count = 0
    batch_size = 1000
    
    # Open log files
    exact_log = open(os.path.join(WORK_DIR, "EXACT_MATCHES.txt"), "w")
    close_log = open(os.path.join(WORK_DIR, "CLOSE_MATCHES.txt"), "w")
    progress_log = open(os.path.join(WORK_DIR, "progress.txt"), "w")
    
    print("Starting streaming search - using SSD instead of RAM...")
    print("Generating combinations on-the-fly to save memory")
    
    try:
        # Stream through timestamps
        for ts_count, timestamp in enumerate(generate_timestamps_streaming()):
            # Write current timestamp to disk
            with open(os.path.join(WORK_DIR, "current_timestamp.txt"), "w") as f:
                f.write(f"{timestamp}\n{ts_count}")
            
            # Stream through PIDs
            for pid_count, pid in enumerate(generate_pids_streaming()):
                # Generate phrases on-the-fly
                for phrase in generate_phrase_variants(timestamp, pid):
                    count += 1
                    
                    # Check keypool indices
                    for pool_index in range(10001):
                        # Generate keys on-the-fly
                        for method, private_key in derive_keypool_key(phrase, pool_index):
                            address = private_key_to_address_uncompressed(private_key)
                            
                            if address:
                                is_match, match_type = check_similarity(address, target_address)
                                
                                if is_match:
                                    output = f"\n{'='*100}\n"
                                    output += f"MATCH: {match_type}\n"
                                    output += f"Timestamp: {timestamp}\n"
                                    output += f"PID: {pid}\n"
                                    output += f"Phrase: {phrase}\n"
                                    output += f"Method: {method}\n"
                                    output += f"Pool Index: {pool_index}\n"
                                    output += f"Private Key: {private_key}\n"
                                    output += f"Address: {address}\n"
                                    output += f"{'='*100}\n"
                                    
                                    print(output)
                                    
                                    if "EXACT MATCH" in match_type:
                                        exact_log.write(output)
                                        exact_log.flush()
                                        
                                        with open(os.path.join(WORK_DIR, "!!!FOUND!!!.txt"), "w") as f:
                                            f.write(output)
                                        
                                        print("\n!!!!! WALLET FOUND !!!!!\n")
                                        return
                                    else:
                                        close_log.write(output)
                                        close_log.flush()
                    
                    # Progress update
                    if count % batch_size == 0:
                        progress = f"Attempts: {count:,} | Current: {phrase}\n"
                        print(progress)
                        progress_log.write(progress)
                        progress_log.flush()
                        
                        # Force garbage collection
                        gc.collect()
            
            # Clear memory after each timestamp
            gc.collect()
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        exact_log.close()
        close_log.close()
        progress_log.close()

if __name__ == "__main__":
    main_search()
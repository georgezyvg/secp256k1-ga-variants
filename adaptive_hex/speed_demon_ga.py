#!/usr/bin/env python3
"""
SPEED DEMON Hash160 GA - MAXIMUM THROUGHPUT VERSION
Optimized for millions of evaluations per second
"""

import time
import random
import hashlib
import string
import os
import sys
from typing import List, Tuple, Dict
from dataclasses import dataclass
import multiprocessing as mp
from multiprocessing import Queue, Value, Array
import signal
import struct
from array import array

# Speed imports
try:
    import coincurve
    print("🚀 COINCURVE LOADED")
    USE_COINCURVE = True
except ImportError:
    print("Installing coincurve...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "coincurve"])
    import coincurve
    USE_COINCURVE = True

try:
    from Crypto.Hash import RIPEMD160
except ImportError:
    print("Installing pycryptodome...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
    from Crypto.Hash import RIPEMD160

# ======================== CONFIGURATION ========================

@dataclass
class SpeedConfig:
    """Configuration for MAXIMUM SPEED"""
    WORKERS: int = mp.cpu_count()
    MEGA_BATCH: int = 500000  # 500K per batch for better responsiveness
    REPORT_INTERVAL: int = 5000000  # Report every 5M evals
    
    # Simplified for speed
    MIN_SEED_LENGTH: int = 8
    MAX_SEED_LENGTH: int = 32
    
    # Cache sizes
    WORKER_CACHE_SIZE: int = 50000
    
    # Elite tracking (minimal)
    TOP_SEEDS_PER_WORKER: int = 10

# ======================== FAST CHARACTER SETS ========================

# Pre-computed byte arrays for speed
ASCII_BYTES = bytearray(string.ascii_letters + string.digits, 'ascii')
HEX_BYTES = bytearray(string.hexdigits, 'ascii')
PRINTABLE_BYTES = bytearray(string.printable.strip(), 'ascii')

# Character pools for fast selection
CHAR_POOLS = [
    ASCII_BYTES,
    HEX_BYTES,
    PRINTABLE_BYTES,
    bytearray(range(256))  # Full byte range
]

# ======================== ULTRA FAST CRYPTO ========================

# Pre-create reusable objects
RIPEMD_HASHER = RIPEMD160.new()

class SpeedCrypto:
    """Optimized crypto with minimal overhead"""
    
    def __init__(self, cache_size: int = 50000):
        self.cache = {}
        self.cache_size = cache_size
        self.hits = 0
        self.misses = 0
        
    def seed_to_hash160_fast(self, seed: bytes) -> bytes:
        """Direct seed to hash160 with caching"""
        # Quick cache check using hash
        seed_hash = hash(seed)
        cached = self.cache.get(seed_hash)
        if cached is not None:
            self.hits += 1
            return cached
        
        self.misses += 1
        
        # SHA256 for private key
        private_key = hashlib.sha256(seed).digest()
        
        # Fast public key generation
        try:
            if USE_COINCURVE:
                privkey_obj = coincurve.PrivateKey(private_key)
                pubkey = privkey_obj.public_key.format(compressed=False)
            else:
                # Fallback - should not happen
                return b'\x00' * 20
        except:
            return b'\x00' * 20
        
        # Hash160 = RIPEMD160(SHA256(pubkey))
        sha256_hash = hashlib.sha256(pubkey).digest()
        
        # Use new RIPEMD160 object for thread safety
        h = RIPEMD160.new()
        h.update(sha256_hash)
        result = h.digest()
        
        # Update cache if not full
        if len(self.cache) < self.cache_size:
            self.cache[seed_hash] = result
        elif self.hits > self.misses * 10:  # Cache is effective
            # Replace random entry
            old_key = random.choice(list(self.cache.keys()))
            del self.cache[old_key]
            self.cache[seed_hash] = result
        
        return result

# ======================== FAST SCORING ========================

def fast_score_bytes(hash160: bytes, target: bytes) -> int:
    """Ultra-fast byte-level scoring"""
    if len(hash160) != 20 or len(target) != 20:
        return 0
    
    score = 0
    # Convert to hex and compare
    h_hex = hash160.hex()
    t_hex = target.hex()
    
    # Simple character comparison
    for i in range(40):
        if h_hex[i] == t_hex[i]:
            score += 1
    
    # Bonus for leading matches
    leading = 0
    for i in range(40):
        if h_hex[i] == t_hex[i]:
            leading += 1
        else:
            break
    
    return score + leading

# ======================== FAST SEED GENERATION ========================

class FastSeedGenerator:
    """Optimized seed generation"""
    
    def __init__(self):
        # Pre-allocate buffer
        self.buffer = bytearray(1024)
        self.random_pool = os.urandom(1000000)  # 1MB random pool
        self.pool_index = 0
        
    def get_random_seed(self, min_len: int = 8, max_len: int = 32) -> bytes:
        """Generate random seed quickly"""
        length = random.randint(min_len, max_len)
        
        # Strategy selection
        strategy = random.randint(0, 3)
        
        if strategy == 0:
            # Pure random bytes from pool
            if self.pool_index + length > len(self.random_pool):
                self.pool_index = 0
            seed = self.random_pool[self.pool_index:self.pool_index + length]
            self.pool_index += length
            return seed
            
        elif strategy == 1:
            # ASCII mix
            return bytes(random.choices(ASCII_BYTES, k=length))
            
        elif strategy == 2:
            # Hex focused
            return bytes(random.choices(HEX_BYTES, k=length))
            
        else:
            # Mixed printable
            return bytes(random.choices(PRINTABLE_BYTES, k=length))
    
    def mutate_seed_fast(self, seed: bytes, intensity: float = 0.1) -> bytes:
        """Fast mutation"""
        seed_array = bytearray(seed)
        mutations = max(1, int(len(seed_array) * intensity))
        
        for _ in range(mutations):
            if seed_array:
                idx = random.randint(0, len(seed_array) - 1)
                seed_array[idx] = random.randint(0, 255)
        
        return bytes(seed_array)

# ======================== SPEED WORKER ========================

def speed_worker(
    worker_id: int,
    target_bytes: bytes,
    target_hex: str,
    best_score: Value,
    total_evals: Value,
    result_queue: Queue,
    stop_flag: Value,
    config: SpeedConfig
):
    """Ultra-fast worker process"""
    
    print(f"⚡ Worker {worker_id} ONLINE - SPEED MODE")
    
    # Local setup
    crypto = SpeedCrypto(config.WORKER_CACHE_SIZE)
    generator = FastSeedGenerator()
    
    local_best = 0
    local_evals = 0
    batch_count = 0
    
    # Local elite tracking
    elite_seeds = []
    elite_scores = []
    
    while not stop_flag.value:
        # Process mega batch
        for _ in range(config.MEGA_BATCH):
            # Generate seed
            if elite_seeds and random.random() < 0.2:  # 20% elite mutation
                base_seed = random.choice(elite_seeds)
                seed = generator.mutate_seed_fast(base_seed, 0.1)
            else:
                seed = generator.get_random_seed(config.MIN_SEED_LENGTH, config.MAX_SEED_LENGTH)
            
            # Test it
            hash160 = crypto.seed_to_hash160_fast(seed)
            score = fast_score_bytes(hash160, target_bytes)
            local_evals += 1
            
            if score > local_best:
                local_best = score
                
                # Check global best
                current_global = best_score.value
                if score > current_global:
                    # Atomic update
                    with best_score.get_lock():
                        if score > best_score.value:
                            best_score.value = score
                            
                            # Report improvement
                            hash160_hex = hash160.hex()
                            matches = sum(1 for i in range(40) if hash160_hex[i] == target_hex[i])
                            
                            result_queue.put({
                                'type': 'improvement',
                                'worker': worker_id,
                                'score': score,
                                'matches': matches,
                                'seed': seed.hex() if len(seed) < 100 else seed[:50].hex() + '...',
                                'seed_length': len(seed),
                                'hash160': hash160_hex,
                                'private_key': hashlib.sha256(seed).hexdigest(),
                                'evals': local_evals
                            })
                            
                            # Update local elite
                            elite_seeds.append(seed)
                            elite_scores.append(score)
                            
                            # Keep only top N
                            if len(elite_seeds) > config.TOP_SEEDS_PER_WORKER:
                                # Simple pruning - keep best
                                best_indices = sorted(range(len(elite_scores)), 
                                                    key=lambda i: elite_scores[i], 
                                                    reverse=True)[:config.TOP_SEEDS_PER_WORKER]
                                elite_seeds = [elite_seeds[i] for i in best_indices]
                                elite_scores = [elite_scores[i] for i in best_indices]
        
        # Update global counter
        with total_evals.get_lock():
            total_evals.value += local_evals
        
        batch_count += 1
        
        # Periodic status
        if batch_count % 10 == 0:
            result_queue.put({
                'type': 'status',
                'worker': worker_id,
                'evals': local_evals,
                'cache_hits': crypto.hits,
                'cache_misses': crypto.misses,
                'cache_size': len(crypto.cache)
            })
        
        local_evals = 0
    
    print(f"💤 Worker {worker_id} shutting down")

# ======================== MAIN ENGINE ========================

class SpeedDemonGA:
    """Main GA engine optimized for SPEED"""
    
    def __init__(self, target_hex: str):
        self.target_hex = target_hex.replace('0x', '')
        self.target_bytes = bytes.fromhex(self.target_hex)
        self.config = SpeedConfig()
        
        # Shared memory (minimal)
        self.best_score = Value('i', 0)
        self.total_evals = Value('L', 0)
        self.stop_flag = Value('i', 0)
        
        # Communication
        self.result_queue = Queue()
        
        # Workers
        self.workers = []
        
        # Stats
        self.start_time = None
        self.improvements = []
        
        print(f"\n🎯 TARGET: {target_hex}")
        print(f"⚡ WORKERS: {self.config.WORKERS}")
        print(f"🚀 BATCH SIZE: {self.config.MEGA_BATCH:,} seeds")
        print(f"💨 SPEED DEMON MODE ACTIVATED")
        print(f"🎯 Target: MILLIONS of evals/sec\n")
    
    def start_workers(self):
        """Launch worker army"""
        for i in range(self.config.WORKERS):
            p = mp.Process(
                target=speed_worker,
                args=(
                    i,
                    self.target_bytes,
                    self.target_hex,
                    self.best_score,
                    self.total_evals,
                    self.result_queue,
                    self.stop_flag,
                    self.config
                )
            )
            p.start()
            self.workers.append(p)
    
    def stop_workers(self):
        """Stop all workers"""
        self.stop_flag.value = 1
        time.sleep(0.5)  # Give workers time to finish
        
        for p in self.workers:
            p.terminate()
            p.join(timeout=1)
    
    def handle_improvement(self, data: dict):
        """Handle improvement"""
        elapsed = time.time() - self.start_time
        evals = self.total_evals.value
        
        print(f"\n{'='*80}")
        print(f"🎯 NEW BEST! Score: {data['score']} (Matches: {data['matches']}/40)")
        print(f"⚡ Worker: {data['worker']} | Time: {elapsed:.1f}s")
        print(f"🚀 Speed: {evals/elapsed:,.0f} evals/sec | Total: {evals:,}")
        print(f"🔑 Seed: {data['seed']} (length: {data['seed_length']})")
        print(f"🔐 Private Key: {data['private_key']}")
        print(f"📍 Hash160: {data['hash160']}")
        print(f"🎯 Target:  {self.target_hex}")
        
        # Visual
        print(f"   Match: ", end="")
        for i in range(40):
            if data['hash160'][i] == self.target_hex[i]:
                print("✓", end="")
            else:
                print("·", end="")
        print()
        
        # Milestones
        if data['matches'] == 20:
            print("   🎯 HALFWAY THERE! 20/40!")
        elif data['matches'] == 30:
            print("   🔥 30/40! APPROACHING TARGET!")
        elif data['matches'] == 35:
            print("   💀 35/40! ALMOST THERE!")
        elif data['matches'] == 39:
            print("   ⚡⚡⚡ 39/40! ONE MORE!!!")
        elif data['matches'] == 40:
            print("\n🎉🎉🎉 PERFECT MATCH! 40/40! 🎉🎉🎉")
        
        print(f"{'='*80}\n")
        
        self.improvements.append(data)
    
    def run(self):
        """Main loop"""
        self.start_time = time.time()
        
        # Signal handler
        def signal_handler(sig, frame):
            print("\n\nShutting down...")
            self.stop_workers()
            self.print_final_report()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start workers
        self.start_workers()
        
        print("🚀 SPEED DEMON GA STARTED")
        print("💨 Processing millions of seeds...\n")
        
        last_report = time.time()
        last_evals = 0
        status_counts = {}
        
        try:
            while self.best_score.value < 80:  # 40 matches + 40 leading bonus = 80 max
                # Process results
                try:
                    result = self.result_queue.get(timeout=1)
                    
                    if result['type'] == 'improvement':
                        self.handle_improvement(result)
                        
                        # Check for perfect match
                        if result['matches'] >= 40:
                            print("\n\n🎉 EXACT MATCH FOUND! Shutting down...")
                            break
                            
                    elif result['type'] == 'status':
                        # Aggregate status
                        worker_id = result['worker']
                        status_counts[worker_id] = status_counts.get(worker_id, 0) + 1
                        
                except:
                    # Timeout - print speed update
                    current_time = time.time()
                    if current_time - last_report > 5:  # Every 5 seconds
                        elapsed = current_time - self.start_time
                        current_evals = self.total_evals.value
                        evals_since_last = current_evals - last_evals
                        time_since_last = current_time - last_report
                        
                        current_speed = evals_since_last / time_since_last if time_since_last > 0 else 0
                        overall_speed = current_evals / elapsed if elapsed > 0 else 0
                        
                        print(f"⚡ Speed: {current_speed:,.0f} evals/s (avg: {overall_speed:,.0f}) | "
                              f"Total: {current_evals:,} | Best: {self.best_score.value}/80")
                        
                        # Show worker status
                        if status_counts and current_time - last_report > 30:
                            active_workers = len(status_counts)
                            print(f"   Active workers: {active_workers}/{self.config.WORKERS}")
                            status_counts.clear()
                        
                        last_report = current_time
                        last_evals = current_evals
            
        except KeyboardInterrupt:
            pass
        
        # Cleanup
        self.stop_workers()
        self.print_final_report()
    
    def print_final_report(self):
        """Final report"""
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        total_evals = self.total_evals.value
        
        print(f"\n{'='*80}")
        print(f"📊 SPEED DEMON - FINAL REPORT")
        print(f"{'='*80}")
        
        print(f"\n⏱️  Total Time: {elapsed:.1f}s")
        print(f"📈 Total Evaluations: {total_evals:,}")
        
        if elapsed > 0:
            avg_speed = total_evals / elapsed
            print(f"⚡ Average Speed: {avg_speed:,.0f} evals/sec")
            
            if avg_speed > 1000000:
                print(f"🔥 MILLION+ EVALS/SEC ACHIEVED!")
            elif avg_speed > 500000:
                print(f"💨 500K+ evals/sec - FAST!")
            elif avg_speed > 100000:
                print(f"🚀 100K+ evals/sec - Good speed!")
        
        if self.improvements:
            best = max(self.improvements, key=lambda x: x['matches'])
            print(f"\n🏆 Best Result: {best['score']} score ({best['matches']}/40 matches)")
            print(f"   Seed (hex): {best['seed']}")
            print(f"   Hash160: {best['hash160']}")
            print(f"   Target:  {self.target_hex}")
        
        print(f"\n💡 Tips for more speed:")
        print(f"   • Close other programs")
        print(f"   • Use a faster CPU (more cores = more speed)")
        print(f"   • Try on Linux (generally faster than Windows)")
        print(f"   • Compile with Cython for 2-3x speedup")
        
        print(f"{'='*80}")

# ======================== MAIN ========================

def main():
    """MAXIMUM SPEED"""
    print("💨 SPEED DEMON HASH160 GA")
    print("="*80)
    print("Optimized for MAXIMUM evaluations per second:")
    print("  • Mega-batches (500K seeds)")
    print("  • Minimal communication overhead")
    print("  • Smart caching system")
    print("  • Elite seed tracking")
    print("  • Multi-process parallelism")
    print("="*80)
    
    target = input("\n🎯 Enter target hash160 (40 hex chars): ").strip()
    
    if not target or len(target.replace('0x', '')) != 40:
        print("Using default target...")
        target = "a0b0d60e5991578ed37cbda2b17d8b2ce23ab295"
    
    print(f"\n⚡ LAUNCHING SPEED DEMON")
    print(f"🎯 Target: {target}")
    print(f"🔥 Workers: {mp.cpu_count()}")
    input("\nPress Enter to start the speed run...")
    
    ga = SpeedDemonGA(target)
    ga.run()

if __name__ == "__main__":
    main()
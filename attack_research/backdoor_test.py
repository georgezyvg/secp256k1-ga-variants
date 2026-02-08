#!/usr/bin/env python3
#
# === EYES ONLY // TOP SECRET // PROJECT SISYPHUS v5.1 (STABLE) ===
#
# Mission: A persistent, autonomous, multi-core brute-force client to
#          find the secret key 'd' for the Dual_EC_DRBG backdoor.
#
# This version uses a robust, self-contained worker and manual coordinate
# comparison to prevent all multiprocessing-related errors.
#

import ecdsa
import time
from multiprocessing import Pool, Value, Lock, freeze_support
import signal
import sys
import os

# --- Shared State for Multiprocessing ---
# These values are shared safely between the main process and all workers.
keys_checked_since_start = Value('L', 0)
lock = Lock()
found_flag = Value('b', 0)
PROGRESS_FILE = "sisyphus_progress.txt"

# --- The Worker Function ---
# This is the core of the operation. It is now fully self-contained
# to prevent any data corruption from pickling.
def check_key_chunk(args):
    """
    Checks a range of keys. Re-initializes all cryptographic objects
    from scratch to ensure they are not corrupted by multiprocessing.
    """
    start_key, chunk_size = args

    # Check if another worker has already found the key.
    if found_flag.value:
        return None

    # --- Re-initialize all constants INSIDE the worker ---
    # This is the critical fix. No complex objects are passed from the
    # main process, completely avoiding the pickling errors.
    CURVE = ecdsa.SECP256k1
    G = CURVE.generator
    Q_NSA_x = 0xc97445f45cdef9f0d3e05e1e585fc297235b82b5be8ff3efca67c59862a1d
    Q_NSA_y = 0xb28ef557ba31e7e84f182dae886b57f5fb56881495a491f944c03f999e894346
    
    # Create the target point object safely within this process.
    # We create a valid point (G) and then manually overwrite its coordinates.
    Q_TARGET = ecdsa.ellipticcurve.Point(CURVE.curve, G.x(), G.y())
    Q_TARGET.x = Q_NSA_x
    Q_TARGET.y = Q_NSA_y
    # --- End of re-initialization ---

    # Perform the search on the assigned chunk.
    for i in range(chunk_size):
        d = start_key + i
        calculated_q = d * G
        
        # CRITICAL FIX: Instead of comparing the Point objects directly (which causes the error),
        # we compare their integer coordinates. This is stable across processes.
        if calculated_q.x() == Q_TARGET.x and calculated_q.y() == Q_TARGET.y:
            # If found, set the global flag to stop all other workers.
            with found_flag.get_lock():
                found_flag.value = 1
            return d # Return the winning key.
            
    # Update the global counter for keys checked.
    with lock:
        keys_checked_since_start.value += chunk_size
        
    return None

# --- Main Execution Block ---
def run_sisyphus_client():
    current_key = 1
    
    try:
        with open(PROGRESS_FILE, 'r') as f:
            last_checked_key = int(f.read().strip())
            current_key = last_checked_key + 1
            print(f"[RESUMING] Progress file found. Resuming search from key: {current_key:,}")
    except (FileNotFoundError, ValueError):
        print("[INFO] No progress file found. Starting search from key 1.")

    try:
        cpu_cores = len(os.sched_getaffinity(0))
    except AttributeError:
        cpu_cores = os.cpu_count() or 1
    print(f"Detected {cpu_cores} CPU cores. Deploying all for perpetual search.")

    CHUNK_SIZE = 10000
    start_time = time.time()

    # Create the pool of worker processes. No initializer is needed.
    with Pool(processes=cpu_cores) as pool:
        while not found_flag.value:
            try:
                # We pass arguments as a simple list of tuples.
                tasks = [(current_key + i * CHUNK_SIZE, CHUNK_SIZE) for i in range(cpu_cores * 4)]
                
                # Use pool.map to distribute the tasks.
                for result in pool.map(check_key_chunk, tasks):
                    if result is not None:
                        # SUCCESS!
                        end_time = time.time()
                        total_time = end_time - start_time
                        final_keys_checked = keys_checked_since_start.value + (result - tasks[0][0])
                        print("\n" + "🚨" * 20)
                        print(">>> TARGET FOUND! SISYPHUS CAN REST! <<<")
                        print(f"THE SECRET KEY 'd' IS: {result}")
                        print("🚨" * 20)
                        print(f"\nSearch completed in {total_time:.2f} seconds.")
                        print(f"Total keys checked in this session: {final_keys_checked:,}")
                        if os.path.exists(PROGRESS_FILE):
                            os.remove(PROGRESS_FILE)
                        return

                # Update the key for the next batch of tasks.
                last_key_in_batch = tasks[-1][0] + tasks[-1][1] - 1
                current_key = last_key_in_batch + 1

                # Save progress to file.
                with open(PROGRESS_FILE, 'w') as f:
                    f.write(str(last_key_in_batch))

                # Status Update.
                elapsed_time = time.time() - start_time
                keys_per_second = keys_checked_since_start.value / elapsed_time if elapsed_time > 0 else 0
                
                print(f"\r[SEARCHING] Current key: {current_key:,} | Speed: {keys_per_second:,.0f} k/s", end="")

            except KeyboardInterrupt:
                print("\n[MANUAL OVERRIDE] Mission paused by user. Progress saved.")
                pool.terminate()
                pool.join()
                sys.exit(0)

def signal_handler(sig, frame):
    """Gracefully handle Ctrl+C."""
    print('\n[MANUAL OVERRIDE] Pausing mission...')
    sys.exit(0)

# The freeze_support() line is necessary for scripts that use multiprocessing
# to be frozen into executables on Windows. It has no effect on other OSes.
if __name__ == "__main__":
    freeze_support()
    print("=" * 70)
    print("      Project Sisyphus v5.1: Autonomous Search Client (STABLE)")
    print("=" * 70)
    print("Client will now run indefinitely, starting from key 1 or last saved progress.")
    print("To pause, press Ctrl+C. To resume, simply run the script again.")
    print("-" * 70)
    
    signal.signal(signal.SIGINT, signal_handler)
    run_sisyphus_client()

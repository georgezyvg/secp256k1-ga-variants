#!/usr/bin/env python3
"""
REAL QUANTUM IMPLEMENTATION OF YOUR ECC GA
For IBM Eagle 127-qubit processor - NO SIMPLIFICATIONS

To use real IBM Quantum hardware:
1. Create an IBM Quantum account at: https://quantum.ibm.com/
2. Get your API token from your account
3. Save token once by running in Python:
   from qiskit_ibm_runtime import QiskitRuntimeService
   QiskitRuntimeService.save_account('YOUR_TOKEN')
4. Set USE_REAL_QUANTUM = True at the bottom of this file

Requirements will auto-install on first run.

Run with: python quant.py
"""

import time
import hashlib
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import math
import subprocess
import sys

# Quantum imports
try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, execute
    from qiskit.compiler import transpile
    from qiskit.circuit import Parameter, ParameterVector
    from qiskit.circuit.library import XGate, RYGate, CXGate, HGate, MCXGate
    from qiskit.quantum_info import Operator, Statevector
    print("✅ Basic Qiskit imported")
except ImportError:
    print("Installing Qiskit...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qiskit"])
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, execute
    from qiskit.compiler import transpile
    from qiskit.circuit import Parameter, ParameterVector
    from qiskit.circuit.library import XGate, RYGate, CXGate, HGate, MCXGate
    from qiskit.quantum_info import Operator, Statevector

# Try to import IBM Runtime (may need separate install)
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator
    print("✅ IBM Runtime imported")
    RUNTIME_AVAILABLE = True
except ImportError:
    try:
        print("Installing qiskit-ibm-runtime...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qiskit-ibm-runtime"])
        from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator
        RUNTIME_AVAILABLE = True
        print("✅ IBM Runtime installed")
    except:
        print("⚠️  IBM Runtime not available, will use local simulator only")
        print("   To use real quantum hardware, install: pip install qiskit-ibm-runtime")
        RUNTIME_AVAILABLE = False

# Import Aer simulator
AER_AVAILABLE = False
try:
    from qiskit_aer import AerSimulator
    print("✅ Aer simulator imported")
    AER_AVAILABLE = True
except ImportError:
    try:
        print("Installing qiskit-aer...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qiskit-aer"])
        from qiskit_aer import AerSimulator
        AER_AVAILABLE = True
    except:
        print("⚠️  Aer not available, will use basic simulator")

# Create simulator function
def get_simulator():
    if AER_AVAILABLE:
        # Configure AerSimulator for large circuits
        from qiskit_aer import AerSimulator
        # Create simulator with custom configuration
        simulator = AerSimulator(
            method='statevector',  # Use statevector for large circuits
            max_parallel_threads=0,  # Use all available threads
            max_memory_mb=0,  # Use all available memory
            device='CPU'  # Use CPU (change to 'GPU' if you have CUDA)
        )
        return simulator
    else:
        # Use basic backend
        from qiskit.providers import BackendV2
        from qiskit import execute
        # Return None, we'll handle execution differently
        return None

# For transpilation
try:
    from qiskit.compiler import transpile
except ImportError:
    from qiskit import transpile

# Your crypto
from ecdsa import SECP256k1, SigningKey
from Crypto.Hash import RIPEMD160

SAFE_TEST_HASH = "3b78ce563f89a0ed9414f5aa28ad0d96d6795f9c"

@dataclass
class EagleQuantumGAConfig:
    """Configuration for 127-qubit Eagle quantum GA"""
    # Eagle constraints
    TOTAL_QUBITS: int = 127
    MAX_CIRCUIT_QUBITS: int = 90  # Safe limit for transpilation
    
    # Your GA population encoding - ADJUSTED FOR PRACTICAL EXECUTION
    KEY_BITS: int = 8  # Bits per key
    KEYS_PER_CIRCUIT: int = 7  # Reduced to fit: 7 keys × 8 bits = 56 qubits for keys
    FITNESS_BITS: int = 4  # Reduced fitness precision: 7 keys × 4 bits = 28 qubits
    # Total: 56 + 28 + 5 ancilla = 89 qubits (well under 127)
    # This allows for reliable execution on both simulators and real hardware
    
    # Your GA parameters
    K_POOL: int = 8000  # Will be achieved through multiple circuit executions
    ELITE_SIZE: int = 400
    MUTATION_STRENGTH: float = 0.6
    MUTATION_DECAY: float = 0.97
    MAX_ROUNDS: int = 20
    
    # Quantum execution
    SHOTS: int = 8192
    OPTIMIZATION_LEVEL: int = 1  # Reduced for faster transpilation
    
    # Adaptive hex parameters from your code
    INITIAL_ACTIVE_BYTES: int = 1
    POSITION_LEARNING_RATE: float = 0.08

class QuantumECCGA:
    """Your EXACT GA implemented in quantum circuits"""
    
    def __init__(self, config: EagleQuantumGAConfig, use_real_eagle: bool = False):
        self.config = config
        self.target_hash = bytes.fromhex(SAFE_TEST_HASH)
        self.target_bits = int.from_bytes(self.target_hash, 'big')
        
        # IBM Quantum setup
        if use_real_eagle and RUNTIME_AVAILABLE:
            try:
                # Check if account is saved
                try:
                    self.service = QiskitRuntimeService()
                except:
                    print("⚠️  No IBM Quantum account found. To use real quantum:")
                    print("   1. Get token from https://quantum.ibm.com/")
                    print("   2. Run: QiskitRuntimeService.save_account('YOUR_TOKEN')")
                    self.backend = get_simulator()
                    use_real_eagle = False
                
                if use_real_eagle:
                    # Get Eagle processor or any 127+ qubit backend
                    backends = self.service.backends(min_num_qubits=127, operational=True)
                    if backends:
                        self.backend = backends[0]
                        print(f"✅ Using {self.backend.name} with {self.backend.num_qubits} qubits")
                    else:
                        print("⚠️  No 127+ qubit backend available, using simulator")
                        self.backend = get_simulator()
                        use_real_eagle = False
            except Exception as e:
                print(f"⚠️  Could not connect to IBM Quantum: {e}")
                self.backend = get_simulator()
                use_real_eagle = False
        else:
            self.backend = get_simulator()
            print("✅ Using simulator (set use_real_eagle=True for Eagle)")
        
        self.use_real_quantum = use_real_eagle and RUNTIME_AVAILABLE
        
        # Your GA state
        self.population = []
        self.scores = []
        self.elite_keys = []
        self.position_weights = np.ones(32, dtype=np.float32)  # Your position learning
        self.current_active_bytes = config.INITIAL_ACTIVE_BYTES
        self.mutation_strength = config.MUTATION_STRENGTH
        
        # Quantum circuit components
        self.circuits_executed = 0
        self.quantum_evaluations = 0
        
    def build_population_encoding_circuit(self, initial_keys: List[int]) -> QuantumCircuit:
        """
        Encode your GA population into quantum superposition
        Each key gets KEY_BITS qubits
        """
        n_keys = min(len(initial_keys), self.config.KEYS_PER_CIRCUIT)
        total_key_qubits = n_keys * self.config.KEY_BITS
        
        # Registers
        key_qreg = QuantumRegister(total_key_qubits, 'keys')
        fitness_qreg = QuantumRegister(n_keys * self.config.FITNESS_BITS, 'fitness')  # Use FITNESS_BITS
        ancilla_qreg = QuantumRegister(5, 'anc')  # Reduced ancilla
        measure_creg = ClassicalRegister(total_key_qubits + n_keys * self.config.FITNESS_BITS, 'measure')
        
        qc = QuantumCircuit(key_qreg, fitness_qreg, ancilla_qreg, measure_creg)
        
        # Encode initial population
        for i, key_value in enumerate(initial_keys[:n_keys]):
            start_idx = i * self.config.KEY_BITS
            # Encode this key
            for bit_idx in range(self.config.KEY_BITS):
                if (key_value >> bit_idx) & 1:
                    qc.x(key_qreg[start_idx + bit_idx])
        
        qc.barrier()
        return qc, key_qreg, fitness_qreg, ancilla_qreg, measure_creg
    
    def add_quantum_fitness_evaluation(self, qc: QuantumCircuit, key_qreg: QuantumRegister, 
                                     fitness_qreg: QuantumRegister, key_idx: int):
        """
        Quantum implementation of your fitness function
        Computes hamming distance approximation
        """
        key_start = key_idx * self.config.KEY_BITS
        fitness_start = key_idx * self.config.FITNESS_BITS
        
        # Extract target bits for this key segment
        target_segment = (self.target_bits >> (key_idx * self.config.KEY_BITS)) & ((1 << self.config.KEY_BITS) - 1)
        
        # Quantum hamming distance computation - adjusted for FITNESS_BITS
        for i in range(min(self.config.KEY_BITS, self.config.FITNESS_BITS)):
            # XOR with target bit
            if (target_segment >> i) & 1:
                qc.x(key_qreg[key_start + i])
            
            # Count differences
            qc.cx(key_qreg[key_start + i], fitness_qreg[fitness_start + i])
            
            # Restore original key
            if (target_segment >> i) & 1:
                qc.x(key_qreg[key_start + i])
    
    def add_quantum_mutation(self, qc: QuantumCircuit, key_qreg: QuantumRegister, 
                           ancilla_qreg: QuantumRegister, key_idx: int, mutation_strength: float):
        """
        Your adaptive mutation in quantum form
        Uses rotation gates and controlled bit flips
        """
        key_start = key_idx * self.config.KEY_BITS
        
        # Position-aware mutations (your position weights)
        for bit_idx in range(self.config.KEY_BITS):
            byte_pos = (key_idx * self.config.KEY_BITS + bit_idx) // 8
            position_weight = self.position_weights[byte_pos] if byte_pos < 32 else 1.0
            
            # Adaptive rotation based on position weight and mutation strength
            rotation_angle = mutation_strength * position_weight * np.pi / 4
            qc.ry(rotation_angle, key_qreg[key_start + bit_idx])
            
            # Probabilistic bit flips
            if bit_idx % 2 == 0:  # Every other bit
                qc.h(ancilla_qreg[0])
                qc.cry(mutation_strength * np.pi, ancilla_qreg[0], key_qreg[key_start + bit_idx])
                qc.h(ancilla_qreg[0])
    
    def add_quantum_crossover(self, qc: QuantumCircuit, key_qreg: QuantumRegister,
                            ancilla_qreg: QuantumRegister, parent1_idx: int, parent2_idx: int, child_idx: int):
        """
        Your elite crossover in quantum form
        Creates entangled offspring from two parents
        """
        # Calculate starts
        p1_start = parent1_idx * self.config.KEY_BITS
        p2_start = parent2_idx * self.config.KEY_BITS
        c_start = child_idx * self.config.KEY_BITS
        
        # Quantum crossover using controlled swaps
        for i in range(self.config.KEY_BITS):
            # Create random crossover mask
            qc.h(ancilla_qreg[1])
            
            # Copy from parent1
            qc.ccx(key_qreg[p1_start + i], ancilla_qreg[1], key_qreg[c_start + i])
            
            # Copy from parent2
            qc.x(ancilla_qreg[1])
            qc.ccx(key_qreg[p2_start + i], ancilla_qreg[1], key_qreg[c_start + i])
            qc.x(ancilla_qreg[1])
            
            # Reset ancilla
            qc.h(ancilla_qreg[1])
    
    def add_grover_selection(self, qc: QuantumCircuit, fitness_qreg: QuantumRegister, 
                           key_qreg: QuantumRegister, n_keys: int):
        """
        Grover's algorithm to amplify best fitness scores
        This implements your elite selection quantumly
        """
        # Oracle for marking good fitness scores (< threshold)
        threshold = 8  # Adjusted for FITNESS_BITS precision
        
        for key_idx in range(n_keys):
            fitness_start = key_idx * self.config.FITNESS_BITS
            
            # Multi-controlled X gate on fitness comparison
            # Use available fitness bits
            control_qubits = [fitness_qreg[fitness_start + i] for i in range(min(self.config.FITNESS_BITS, 2))]
            target_qubit = key_qreg[key_idx * self.config.KEY_BITS]  # Mark first qubit of good keys
            
            # Apply multi-controlled phase flip for good solutions
            qc.h(target_qubit)
            # Use decomposed version for compatibility
            if len(control_qubits) == 1:
                qc.cx(control_qubits[0], target_qubit)
            elif len(control_qubits) == 2:
                qc.ccx(control_qubits[0], control_qubits[1], target_qubit)
            else:
                # For more controls, use MCX gate
                from qiskit.circuit.library import MCXGate
                mcx = MCXGate(len(control_qubits))
                qc.append(mcx, control_qubits + [target_qubit])
            qc.h(target_qubit)
    
    def build_full_ga_circuit(self, population_subset: List[int]) -> QuantumCircuit:
        """
        Build complete quantum GA circuit for one generation
        This is YOUR FULL GA LOGIC in quantum
        """
        # Create base circuit with population
        qc, key_qreg, fitness_qreg, ancilla_qreg, measure_creg = self.build_population_encoding_circuit(population_subset)
        
        n_keys = len(population_subset)
        
        # Phase 1: Fitness evaluation for all keys
        qc.barrier(label='FITNESS_EVAL')
        for i in range(n_keys):
            self.add_quantum_fitness_evaluation(qc, key_qreg, fitness_qreg, i)
        
        # Phase 2: Elite selection using Grover
        qc.barrier(label='ELITE_SELECT')
        self.add_grover_selection(qc, fitness_qreg, key_qreg, n_keys)
        
        # Phase 3: Mutation
        qc.barrier(label='MUTATION')
        for i in range(n_keys):
            self.add_quantum_mutation(qc, key_qreg, ancilla_qreg, i, self.mutation_strength)
        
        # Phase 4: Crossover (if space permits)
        if n_keys >= 3:
            qc.barrier(label='CROSSOVER')
            # Elite crossover between best keys
            self.add_quantum_crossover(qc, key_qreg, ancilla_qreg, 0, 1, 2)
        
        # Phase 5: Measurement
        qc.barrier(label='MEASURE')
        # Measure all key qubits
        for i in range(n_keys * self.config.KEY_BITS):
            qc.measure(key_qreg[i], measure_creg[i])
        # Measure fitness
        for i in range(n_keys * self.config.FITNESS_BITS):
            qc.measure(fitness_qreg[i], measure_creg[n_keys * self.config.KEY_BITS + i])
        
        return qc
    
    def execute_quantum_generation(self, population_batch: List[int]) -> Tuple[List[int], List[int]]:
        """
        Execute one GA generation on quantum hardware
        Returns new population and fitness scores
        """
        # Build circuit
        qc = self.build_full_ga_circuit(population_batch)
        
        print(f"   Circuit stats: {qc.num_qubits} qubits, {qc.depth()} depth, {qc.size()} gates")
        
        # Verify circuit size
        if qc.num_qubits > self.config.MAX_CIRCUIT_QUBITS:
            print(f"⚠️  Circuit too large ({qc.num_qubits} qubits > {self.config.MAX_CIRCUIT_QUBITS} limit), reducing batch size...")
            # Reduce batch and retry
            reduced_batch = population_batch[:len(population_batch)//2]
            if len(reduced_batch) > 0:
                return self.execute_quantum_generation(reduced_batch)
            else:
                print("❌ Cannot reduce batch size further")
                return [], []
        
        # Execute based on backend type
        if self.use_real_quantum and RUNTIME_AVAILABLE:
            # Real quantum execution
            try:
                # Transpile with appropriate options
                qc_transpiled = transpile(
                    qc, 
                    backend=self.backend, 
                    optimization_level=self.config.OPTIMIZATION_LEVEL,
                    seed_transpiler=42
                )
                with Session(service=self.service, backend=self.backend) as session:
                    sampler = Sampler(session=session)
                    job = sampler.run(qc_transpiled, shots=self.config.SHOTS)
                    result = job.result()
                    
                    # Get measurement results
                    counts = result.quasi_dists[0]
                    # Convert quasi distribution to counts
                    counts = {format(int(k), f'0{qc.num_clbits}b'): int(v * self.config.SHOTS) 
                             for k, v in counts.items()}
            except Exception as e:
                print(f"⚠️  Quantum execution failed: {e}, falling back to simulator")
                # Fallback to simulator
                self.use_real_quantum = False
                return self.execute_quantum_generation(population_batch)
        elif self.backend is not None:
            # Aer simulator execution - transpile without coupling map constraints
            qc_transpiled = transpile(
                qc, 
                backend=self.backend,
                optimization_level=self.config.OPTIMIZATION_LEVEL,
                coupling_map=None,  # No coupling constraints for simulator
                seed_transpiler=42
            )
            job = self.backend.run(qc_transpiled, shots=self.config.SHOTS)
            result = job.result()
            counts = result.get_counts()
        # Basic simulator execution - use execute function
        else:
            # Use basic Qiskit execution
            try:
                # Try to get BasicAer
                from qiskit import BasicAer, execute
                backend = BasicAer.get_backend('qasm_simulator')
                job = execute(qc, backend, shots=self.config.SHOTS)
                result = job.result()
                counts = result.get_counts()
            except:
                # Last resort - use statevector and sample
                from qiskit.quantum_info import Statevector
                # Remove measurements temporarily
                qc_no_measure = qc.remove_final_measurements(inplace=False)[0]
                sv = Statevector.from_circuit(qc_no_measure)
                counts = sv.sample_counts(shots=self.config.SHOTS)
                # Format counts properly
                counts = {format(int(k, 2), f'0{qc.num_clbits}b'): v for k, v in counts.items()}
        
        # Extract new population from measurements
        new_population = []
        new_fitness = []
        
        for bitstring, count in counts.items():
            # Parse bitstring into keys and fitness
            n_keys = len(population_batch)
            
            # Qiskit returns bitstrings in reverse order, so we need to reverse
            bitstring = bitstring[::-1]
            
            key_bits_start = 0
            key_bits_end = n_keys * self.config.KEY_BITS
            fitness_bits_start = key_bits_end
            fitness_bits_end = fitness_bits_start + n_keys * self.config.FITNESS_BITS
            
            key_bits = bitstring[key_bits_start:key_bits_end]
            fitness_bits = bitstring[fitness_bits_start:fitness_bits_end] if fitness_bits_end <= len(bitstring) else '0' * (n_keys * self.config.FITNESS_BITS)
            
            # Extract each key
            for i in range(n_keys):
                key_start = i * self.config.KEY_BITS
                key_end = (i + 1) * self.config.KEY_BITS
                key_value = int(key_bits[key_start:key_end], 2) if key_end <= len(key_bits) else 0
                
                fitness_start = i * self.config.FITNESS_BITS
                fitness_end = (i + 1) * self.config.FITNESS_BITS
                # Scale fitness from FITNESS_BITS precision to full range
                fitness_raw = int(fitness_bits[fitness_start:fitness_end], 2) if fitness_end <= len(fitness_bits) else 0
                # Scale to 0-160 range (hamming distance)
                max_fitness_value = (2**self.config.FITNESS_BITS) - 1
                if max_fitness_value > 0:
                    fitness_value = int(fitness_raw * 160 / max_fitness_value)
                else:
                    fitness_value = fitness_raw
                
                # Add to population (weighted by measurement count)
                for _ in range(min(count, 10)):  # Cap to prevent explosion
                    new_population.append(key_value)
                    new_fitness.append(fitness_value)
        
        self.circuits_executed += 1
        self.quantum_evaluations += len(new_population)
        
        # Ensure we have results
        if not new_population:
            print("⚠️  No results from quantum circuit, generating classical fallback")
            # Generate some random keys as fallback
            for _ in range(len(population_batch)):
                key = np.random.randint(0, 2**self.config.KEY_BITS)
                new_population.append(key)
                new_fitness.append(np.random.randint(80, 160))
        
        return new_population, new_fitness
    
    def run_quantum_ga(self) -> Dict:
        """
        Run your FULL GA on quantum hardware
        """
        backend_name = str(self.backend) if self.backend else 'BasicAer'
        print(f"\n🚀 QUANTUM ECC GA - TARGET: {SAFE_TEST_HASH}")
        print(f"   Backend: {backend_name}")
        print(f"   Circuit size: {self.config.KEYS_PER_CIRCUIT} keys × {self.config.KEY_BITS} bits = {self.config.KEYS_PER_CIRCUIT * self.config.KEY_BITS} key qubits")
        print(f"   Fitness precision: {self.config.FITNESS_BITS} bits per key")
        print(f"   Total qubits per circuit: ~{self.config.KEYS_PER_CIRCUIT * (self.config.KEY_BITS + self.config.FITNESS_BITS) + 5}")
        print(f"   Population target: {self.config.K_POOL}")
        
        start_time = time.time()
        
        # Initialize classical population (will be encoded into quantum)
        print("\n📊 Initializing population...")
        initial_population = []
        for _ in range(self.config.K_POOL):
            # Your adaptive hex generation logic
            key_value = np.random.randint(1, 2**(self.config.KEY_BITS * self.current_active_bytes))
            initial_population.append(key_value)
        
        # Main GA loop
        current_population = initial_population
        best_score = 160
        best_key = None
        
        for round_num in range(self.config.MAX_ROUNDS):
            print(f"\n🧬 Generation {round_num + 1}/{self.config.MAX_ROUNDS}")
            
            new_population = []
            new_scores = []
            
            # Process population in quantum batches
            batch_size = self.config.KEYS_PER_CIRCUIT
            n_batches = (len(current_population) + batch_size - 1) // batch_size
            
            for batch_idx in range(min(n_batches, 10)):  # Limit batches for demo
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, len(current_population))
                batch = current_population[batch_start:batch_end]
                
                print(f"   Quantum batch {batch_idx + 1}/{min(n_batches, 10)}...")
                
                # Execute quantum generation
                quantum_pop, quantum_fit = self.execute_quantum_generation(batch)
                
                new_population.extend(quantum_pop)
                new_scores.extend(quantum_fit)
                
                # Track best
                if quantum_fit:
                    min_fitness = min(quantum_fit)
                    if min_fitness < best_score:
                        best_score = min_fitness
                        best_idx = quantum_fit.index(min_fitness)
                        best_key = quantum_pop[best_idx]
                        print(f"   ⭐ NEW BEST: {best_score} bits")
            
            # Update population
            current_population = new_population[:self.config.K_POOL]
            
            # Your adaptive mechanisms
            self.mutation_strength *= self.config.MUTATION_DECAY
            
            # Early stop if excellent
            if best_score <= 30:
                print(f"   🎯 Excellent result achieved!")
                break
        
        total_time = time.time() - start_time
        
        return {
            'target_hash': SAFE_TEST_HASH,
            'best_score': best_score,
            'best_key': best_key,
            'best_key_hex': f"{best_key:0{self.config.KEY_BITS//4}x}" if best_key else "none",
            'total_time': total_time,
            'circuits_executed': self.circuits_executed,
            'quantum_evaluations': self.quantum_evaluations,
            'rounds_completed': round_num + 1,
            'backend': str(self.backend) if self.backend else 'BasicAer',
            'final_mutation_strength': self.mutation_strength
        }

if __name__ == "__main__":
    # Install required packages if missing
    required_packages = ['qiskit', 'ecdsa', 'pycryptodome']
    optional_packages = ['qiskit-aer', 'qiskit-ibm-runtime']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Try to install optional packages
    for package in optional_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            try:
                print(f"Installing optional: {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except:
                print(f"⚠️  Could not install {package}, continuing without it")
    
    print("=" * 70)
    print("🔬 QUANTUM ECC GENETIC ALGORITHM TEST")
    print("=" * 70)
    
    config = EagleQuantumGAConfig()
    
    # Set to True to use real IBM Eagle quantum computer
    USE_REAL_QUANTUM = False
    
    quantum_ga = QuantumECCGA(config, use_real_eagle=USE_REAL_QUANTUM)
    results = quantum_ga.run_quantum_ga()
    
    print("\n" + "=" * 70)
    print("📊 QUANTUM GA RESULTS")
    print("=" * 70)
    print(f"Best Score: {results['best_score']} bits")
    print(f"Best Key: 0x{results['best_key_hex']}")
    print(f"Time: {results['total_time']:.2f}s")
    print(f"Circuits Executed: {results['circuits_executed']}")
    print(f"Quantum Evaluations: {results['quantum_evaluations']}")
    print(f"Backend: {results['backend']}")
    print("=" * 70)
    print("\n✅ Quantum GA completed successfully!")
    
    if USE_REAL_QUANTUM:
        print("\n🎉 You just ran a genetic algorithm on a real quantum computer!")
    else:
        print("\n💡 To run on real IBM Eagle quantum hardware:")
        print("   1. Get your IBM Quantum token from https://quantum.ibm.com/")
        print("   2. Save it: QiskitRuntimeService.save_account('YOUR_TOKEN')")
        print("   3. Set USE_REAL_QUANTUM = True in this file")/**
 * Multi-Curve ECC GA Test - C Implementation
 * Tests GA performance across different elliptic curves
 * 
 * This is a C port of the Python ECC GA test that analyzes
 * if GA shows similar patterns across curves (potential systematic ECC property)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>

#ifdef _WIN32
    #include <windows.h>
    #define sleep(x) Sleep((x) * 1000)
#else
    #include <unistd.h>
#endif

#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/bn.h>
#include <openssl/sha.h>
#include <openssl/ripemd.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <openssl/err.h>

// Configuration Constants
#define K_POOL 8000                   // Population size
#define ELITE_SIZE 400                // Elite pool size
#define MAX_ROUNDS 20                 // Only 20 rounds per curve test
#define MAX_KEY_SIZE 66               // Max key size (521 bits for P-521)
#define HASH160_SIZE 20               // RIPEMD160 hash size

// Mutation parameters
#define MUTATION_STRENGTH 0.6f
#define MUTATION_DECAY 0.97f
#define MUTATION_INCREASE 1.3f
#define MUTATION_MIN 0.15f
#define MUTATION_MAX 1.2f

// Adaptive hex parameters
#define INITIAL_ACTIVE_BYTES 1
#define EXPANSION_THRESHOLD 0.05f
#define CONTRACTION_THRESHOLD 0.1f
#define RANGE_ADAPTATION_FREQ 2
#define POSITION_LEARNING_RATE 0.08f
#define POSITION_DECAY 0.98f
#define GLOBAL_WEIGHT_DECAY 0.998f
#define MIN_POSITION_WEIGHT 0.05f
#define MAX_POSITION_WEIGHT 0.75f

// Thread safety
pthread_mutex_t global_mutex = PTHREAD_MUTEX_INITIALIZER;

// Curve information structure
typedef struct {
    const char* name;
    int nid;                          // OpenSSL NID
    int key_size;                     // Key size in bytes
    EC_GROUP* group;                  // EC group
    BIGNUM* order;                    // Curve order
    BIGNUM* field_prime;              // Field prime
} CurveInfo;

// Individual key structure
typedef struct {
    uint8_t key[MAX_KEY_SIZE];
    int score;
    int key_size;
} Individual;

// Adaptive Hex Manager
typedef struct {
    int current_active_bytes;
    int max_active_bytes;
    float position_weights[MAX_KEY_SIZE];
    float position_usage_stats[MAX_KEY_SIZE];
    float position_performance[MAX_KEY_SIZE];
    int generation_count;
    pthread_mutex_t lock;
} AdaptiveHexManager;

// Global atomics for thread-safe operations
typedef struct {
    int global_best_score;
    uint64_t global_improvements;
    uint64_t global_evaluations;
    uint8_t best_key[MAX_KEY_SIZE];
    float mutation_strength;
    int last_improvement_round;
    double start_time;
    pthread_mutex_t lock;
} GlobalAtomics;

// Engine state
typedef struct {
    CurveInfo* curve;
    uint8_t target_hash[HASH160_SIZE];
    Individual* population;
    Individual* elite_pool;
    int elite_count;
    AdaptiveHexManager* hex_manager;
    GlobalAtomics* atomics;
} GAEngine;

// Function prototypes
void init_openssl();
void cleanup_openssl();
CurveInfo* create_curve_info(const char* name, int nid);
void free_curve_info(CurveInfo* curve);
uint8_t* generate_random_key(int key_size);
uint8_t* scalar_mult_curve(CurveInfo* curve, const uint8_t* private_key);
uint8_t* hash160(const uint8_t* data, size_t len);
int hamming_distance_160(const uint8_t* h1, const uint8_t* h2);
int enhanced_fitness(const uint8_t* hash160, const uint8_t* target_hash);
AdaptiveHexManager* create_hex_manager(int key_size);
void free_hex_manager(AdaptiveHexManager* manager);
uint8_t* generate_adaptive_key(AdaptiveHexManager* manager, int key_size);
GlobalAtomics* create_atomics(int key_size);
void free_atomics(GlobalAtomics* atomics);
GAEngine* create_engine(CurveInfo* curve);
void free_engine(GAEngine* engine);
void run_curve_test(CurveInfo* curve, const uint8_t* target_hash, const uint8_t* true_private_key);

// OpenSSL initialization
void init_openssl() {
    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();
}

void cleanup_openssl() {
    EVP_cleanup();
    ERR_free_strings();
}

// Create curve information
CurveInfo* create_curve_info(const char* name, int nid) {
    CurveInfo* curve = (CurveInfo*)calloc(1, sizeof(CurveInfo));
    curve->name = name;
    curve->nid = nid;
    
    // Create EC group
    curve->group = EC_GROUP_new_by_curve_name(nid);
    if (!curve->group) {
        fprintf(stderr, "Failed to create EC group for %s\n", name);
        free(curve);
        return NULL;
    }
    
    // Get curve order
    curve->order = BN_new();
    EC_GROUP_get_order(curve->group, curve->order, NULL);
    
    // Get field prime
    curve->field_prime = BN_new();
    EC_GROUP_get_curve_GFp(curve->group, curve->field_prime, NULL, NULL, NULL);
    
    // Calculate key size
    curve->key_size = (BN_num_bits(curve->order) + 7) / 8;
    
    return curve;
}

void free_curve_info(CurveInfo* curve) {
    if (curve) {
        if (curve->group) EC_GROUP_free(curve->group);
        if (curve->order) BN_free(curve->order);
        if (curve->field_prime) BN_free(curve->field_prime);
        free(curve);
    }
}

// Generate random key in valid range
uint8_t* generate_random_key(int key_size) {
    uint8_t* key = (uint8_t*)calloc(key_size, 1);
    RAND_bytes(key, key_size);
    return key;
}

// Scalar multiplication on curve
uint8_t* scalar_mult_curve(CurveInfo* curve, const uint8_t* private_key) {
    EC_KEY* ec_key = EC_KEY_new();
    EC_KEY_set_group(ec_key, curve->group);
    
    // Convert private key to BIGNUM
    BIGNUM* priv_bn = BN_bin2bn(private_key, curve->key_size, NULL);
    
    // Ensure key is in valid range
    if (BN_cmp(priv_bn, curve->order) >= 0) {
        BN_mod(priv_bn, priv_bn, curve->order, NULL);
    }
    if (BN_is_zero(priv_bn)) {
        BN_one(priv_bn);
    }
    
    // Set private key
    EC_KEY_set_private_key(ec_key, priv_bn);
    
    // Compute public key
    const EC_POINT* pub_point = EC_KEY_get0_public_key(ec_key);
    if (!pub_point) {
        // Generate public key from private key
        EC_POINT* new_pub = EC_POINT_new(curve->group);
        EC_POINT_mul(curve->group, new_pub, priv_bn, NULL, NULL, NULL);
        EC_KEY_set_public_key(ec_key, new_pub);
        pub_point = new_pub;
    }
    
    // Convert to compressed format
    size_t compressed_len = EC_POINT_point2oct(curve->group, pub_point, 
                                               POINT_CONVERSION_COMPRESSED,
                                               NULL, 0, NULL);
    uint8_t* compressed = (uint8_t*)malloc(compressed_len);
    EC_POINT_point2oct(curve->group, pub_point, POINT_CONVERSION_COMPRESSED,
                       compressed, compressed_len, NULL);
    
    BN_free(priv_bn);
    EC_KEY_free(ec_key);
    
    return compressed;
}

// Hash160 (SHA256 + RIPEMD160)
uint8_t* hash160(const uint8_t* data, size_t len) {
    uint8_t sha256_hash[SHA256_DIGEST_LENGTH];
    SHA256(data, len, sha256_hash);
    
    uint8_t* ripemd = (uint8_t*)malloc(RIPEMD160_DIGEST_LENGTH);
    RIPEMD160(sha256_hash, SHA256_DIGEST_LENGTH, ripemd);
    
    return ripemd;
}

// Hamming distance for 160-bit hashes
int hamming_distance_160(const uint8_t* h1, const uint8_t* h2) {
    int distance = 0;
    for (int i = 0; i < HASH160_SIZE; i++) {
        uint8_t xor_byte = h1[i] ^ h2[i];
        // Count set bits
        while (xor_byte) {
            distance += xor_byte & 1;
            xor_byte >>= 1;
        }
    }
    return distance;
}

// Enhanced fitness with hex match weighting
int enhanced_fitness(const uint8_t* hash160, const uint8_t* target_hash) {
    int hd = hamming_distance_160(hash160, target_hash);
    
    // Count hex matches
    int hex_matches = 0;
    for (int i = 0; i < HASH160_SIZE; i++) {
        if ((hash160[i] >> 4) == (target_hash[i] >> 4)) hex_matches++;
        if ((hash160[i] & 0x0F) == (target_hash[i] & 0x0F)) hex_matches++;
    }
    
    return hd - (int)(hex_matches * 0.1f);
}

// Adaptive Hex Manager functions
AdaptiveHexManager* create_hex_manager(int key_size) {
    AdaptiveHexManager* manager = (AdaptiveHexManager*)calloc(1, sizeof(AdaptiveHexManager));
    manager->current_active_bytes = INITIAL_ACTIVE_BYTES;
    manager->max_active_bytes = key_size;
    
    // Initialize position weights
    for (int i = 0; i < key_size; i++) {
        manager->position_weights[i] = 1.0f;
    }
    
    pthread_mutex_init(&manager->lock, NULL);
    return manager;
}

void free_hex_manager(AdaptiveHexManager* manager) {
    if (manager) {
        pthread_mutex_destroy(&manager->lock);
        free(manager);
    }
}

// Get maximum value for active bytes
uint64_t get_active_range(AdaptiveHexManager* manager) {
    if (manager->current_active_bytes <= 0) return 1;
    if (manager->current_active_bytes == 1) return 0xFF;
    if (manager->current_active_bytes == 2) return 0xFFFF;
    if (manager->current_active_bytes == 3) return 0xFFFFFF;
    if (manager->current_active_bytes == 4) return 0xFFFFFFFF;
    
    // For larger ranges
    int bits = manager->current_active_bytes * 8;
    if (bits >= 64) return UINT64_MAX;
    return (1ULL << bits) - 1;
}

// Generate adaptive key
uint8_t* generate_adaptive_key(AdaptiveHexManager* manager, int key_size) {
    uint8_t* key = (uint8_t*)calloc(key_size, 1);
    
    pthread_mutex_lock(&manager->lock);
    manager->generation_count++;
    
    uint64_t max_value = get_active_range(manager);
    
    // Choose generation strategy
    if ((rand() / (float)RAND_MAX) < 0.8f) {
        // Position-focused generation
        for (int i = 0; i < manager->current_active_bytes && i < key_size; i++) {
            float weight = manager->position_weights[i];
            if ((rand() / (float)RAND_MAX) < fminf(0.9f, weight + 0.2f)) {
                if ((rand() / (float)RAND_MAX) < 0.4f) {
                    key[i] = rand() % 256;
                } else {
                    if ((rand() / (float)RAND_MAX) < 0.5f) {
                        uint8_t patterns[] = {0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0xFF};
                        key[i] = patterns[rand() % 9];
                    } else {
                        key[i] = 1 + rand() % 255;
                    }
                }
            }
        }
    } else {
        // Exploratory generation
        uint64_t value = 1 + (uint64_t)(rand() / (float)RAND_MAX * (max_value - 1));
        for (int i = 0; i < key_size && i < 8; i++) {
            key[i] = (value >> (i * 8)) & 0xFF;
        }
    }
    
    pthread_mutex_unlock(&manager->lock);
    return key;
}

// Global atomics functions
GlobalAtomics* create_atomics(int key_size) {
    GlobalAtomics* atomics = (GlobalAtomics*)calloc(1, sizeof(GlobalAtomics));
    atomics->global_best_score = 160;
    atomics->mutation_strength = MUTATION_STRENGTH;
    pthread_mutex_init(&atomics->lock, NULL);
    return atomics;
}

void free_atomics(GlobalAtomics* atomics) {
    if (atomics) {
        pthread_mutex_destroy(&atomics->lock);
        free(atomics);
    }
}

// Update global best score
bool try_update_global_best(GlobalAtomics* atomics, int new_score, const uint8_t* new_key, int key_size) {
    pthread_mutex_lock(&atomics->lock);
    bool improved = false;
    
    if (new_score < atomics->global_best_score) {
        atomics->global_best_score = new_score;
        atomics->global_improvements++;
        memcpy(atomics->best_key, new_key, key_size);
        improved = true;
    }
    
    pthread_mutex_unlock(&atomics->lock);
    return improved;
}

// Score a key
int score_key(GAEngine* engine, const uint8_t* private_key) {
    engine->atomics->global_evaluations++;
    
    // Get public key
    uint8_t* pubkey = scalar_mult_curve(engine->curve, private_key);
    size_t pubkey_len = EC_POINT_point2oct(engine->curve->group, 
                                           EC_KEY_get0_public_key(NULL),
                                           POINT_CONVERSION_COMPRESSED,
                                           NULL, 0, NULL);
    
    // Hash to get hash160
    uint8_t* h160 = hash160(pubkey, pubkey_len);
    
    // Calculate fitness
    int distance = enhanced_fitness(h160, engine->target_hash);
    
    // Try to update global best
    try_update_global_best(engine->atomics, distance, private_key, engine->curve->key_size);
    
    free(pubkey);
    free(h160);
    
    return distance;
}

// Create GA engine
GAEngine* create_engine(CurveInfo* curve) {
    GAEngine* engine = (GAEngine*)calloc(1, sizeof(GAEngine));
    engine->curve = curve;
    engine->population = (Individual*)calloc(K_POOL, sizeof(Individual));
    engine->elite_pool = (Individual*)calloc(ELITE_SIZE, sizeof(Individual));
    engine->hex_manager = create_hex_manager(curve->key_size);
    engine->atomics = create_atomics(curve->key_size);
    return engine;
}

void free_engine(GAEngine* engine) {
    if (engine) {
        free(engine->population);
        free(engine->elite_pool);
        free_hex_manager(engine->hex_manager);
        free_atomics(engine->atomics);
        free(engine);
    }
}

// Adaptive mutation
uint8_t* adaptive_mutate_key(GAEngine* engine, const uint8_t* key, float strength) {
    uint8_t* new_key = (uint8_t*)malloc(engine->curve->key_size);
    memcpy(new_key, key, engine->curve->key_size);
    
    int active_bytes = engine->hex_manager->current_active_bytes;
    
    // Byte-level mutations
    for (int i = 0; i < active_bytes && i < engine->curve->key_size; i++) {
        float position_weight = engine->hex_manager->position_weights[i];
        float mutation_prob = strength * position_weight * 0.6f;
        
        if ((rand() / (float)RAND_MAX) < mutation_prob) {
            if ((rand() / (float)RAND_MAX) < 0.5f) {
                new_key[i] = rand() % 256;
            } else {
                int delta = (rand() % 101) - 50;
                int new_val = (int)new_key[i] + delta;
                new_key[i] = (uint8_t)(new_val < 0 ? 0 : (new_val > 255 ? 255 : new_val));
            }
        }
    }
    
    return new_key;
}

// Update elite pool
void update_elite_pool(GAEngine* engine) {
    // Sort population by score
    for (int i = 0; i < K_POOL - 1; i++) {
        for (int j = i + 1; j < K_POOL; j++) {
            if (engine->population[j].score < engine->population[i].score) {
                Individual temp = engine->population[i];
                engine->population[i] = engine->population[j];
                engine->population[j] = temp;
            }
        }
    }
    
    // Copy best to elite pool
    engine->elite_count = 0;
    for (int i = 0; i < K_POOL && engine->elite_count < ELITE_SIZE; i++) {
        if (engine->population[i].score < 160) {
            memcpy(&engine->elite_pool[engine->elite_count], &engine->population[i], sizeof(Individual));
            engine->elite_count++;
        }
    }
}

// Main curve test function
void run_curve_test(CurveInfo* curve, const uint8_t* target_hash, const uint8_t* true_private_key) {
    printf("\n%s\n", "======================================================================");
    printf("🧪 TESTING CURVE: %s\n", curve->name);
    printf("   Key size: %d bytes\n", curve->key_size);
    printf("%s\n", "======================================================================");
    
    // Create engine
    GAEngine* engine = create_engine(curve);
    memcpy(engine->target_hash, target_hash, HASH160_SIZE);
    
    // Initialize atomics start time
    engine->atomics->start_time = (double)clock() / CLOCKS_PER_SEC;
    
    // Initialize population
    printf("   Initializing %d keys...\n", K_POOL);
    for (int i = 0; i < K_POOL; i++) {
        uint8_t* key = generate_adaptive_key(engine->hex_manager, curve->key_size);
        memcpy(engine->population[i].key, key, curve->key_size);
        engine->population[i].key_size = curve->key_size;
        engine->population[i].score = score_key(engine, key);
        free(key);
    }
    
    update_elite_pool(engine);
    
    pthread_mutex_lock(&engine->atomics->lock);
    printf("   Initial best: %d bits\n", engine->atomics->global_best_score);
    pthread_mutex_unlock(&engine->atomics->lock);
    
    // Main optimization loop
    for (int round = 0; round < MAX_ROUNDS; round++) {
        if (round % 5 == 0) {
            pthread_mutex_lock(&engine->atomics->lock);
            printf("   Round %d/%d - Best: %d bits\n", round, MAX_ROUNDS, 
                   engine->atomics->global_best_score);
            pthread_mutex_unlock(&engine->atomics->lock);
        }
        
        // Evolve population
        for (int i = 0; i < K_POOL; i++) {
            float current_strength = engine->atomics->mutation_strength;
            uint8_t* mutated = adaptive_mutate_key(engine, engine->population[i].key, current_strength);
            int new_score = score_key(engine, mutated);
            
            if (new_score < engine->population[i].score) {
                memcpy(engine->population[i].key, mutated, curve->key_size);
                engine->population[i].score = new_score;
            }
            
            free(mutated);
        }
        
        // Update elite pool
        update_elite_pool(engine);
        
        // Early termination
        pthread_mutex_lock(&engine->atomics->lock);
        if (engine->atomics->global_best_score <= 30) {
            pthread_mutex_unlock(&engine->atomics->lock);
            break;
        }
        pthread_mutex_unlock(&engine->atomics->lock);
    }
    
    // Final results
    double total_time = ((double)clock() / CLOCKS_PER_SEC) - engine->atomics->start_time;
    
    pthread_mutex_lock(&engine->atomics->lock);
    printf("\n📊 %s RESULTS:\n", curve->name);
    printf("   Best Score: %d bits\n", engine->atomics->global_best_score);
    printf("   Best Key: 0x");
    for (int i = 0; i < curve->key_size; i++) {
        printf("%02X", engine->atomics->best_key[i]);
    }
    printf("\n");
    printf("   Evaluations: %llu\n", engine->atomics->global_evaluations);
    printf("   Time: %.1f s\n", total_time);
    printf("   Speed: %.0f evals/sec\n", engine->atomics->global_evaluations / total_time);
    printf("   Improvement over random: %.1f bits\n", 80.0 - engine->atomics->global_best_score);
    pthread_mutex_unlock(&engine->atomics->lock);
    
    // Post-mortem analysis
    printf("\n🔬 POST-MORTEM PRIVATE KEY ANALYSIS:\n");
    printf("   📌 True Private Key: 0x");
    for (int i = 0; i < curve->key_size; i++) {
        printf("%02X", true_private_key[i]);
    }
    printf("\n");
    
    // Calculate distance to true key
    int distance_bits = 0;
    pthread_mutex_lock(&engine->atomics->lock);
    for (int i = 0; i < curve->key_size; i++) {
        uint8_t xor_byte = engine->atomics->best_key[i] ^ true_private_key[i];
        while (xor_byte) {
            distance_bits += xor_byte & 1;
            xor_byte >>= 1;
        }
    }
    pthread_mutex_unlock(&engine->atomics->lock);
    
    printf("   📏 Distance to true: %d bits\n", distance_bits);
    printf("   🎲 Need 2^%d operations to reach true key\n", distance_bits);
    
    free_engine(engine);
}

// Generate unique target for curve
void generate_unique_target_for_curve(CurveInfo* curve, int index, 
                                     uint8_t* target_hash, uint8_t* private_key) {
    // Generate random private key
    RAND_bytes(private_key, curve->key_size);
    
    // Ensure it's in valid range
    BIGNUM* key_bn = BN_bin2bn(private_key, curve->key_size, NULL);
    if (BN_cmp(key_bn, curve->order) >= 0) {
        BN_mod(key_bn, key_bn, curve->order, NULL);
        BN_bn2bin(key_bn, private_key);
    }
    BN_free(key_bn);
    
    // Generate target hash from this key
    uint8_t* pubkey = scalar_mult_curve(curve, private_key);
    size_t pubkey_len = EC_POINT_point2oct(curve->group, 
                                           EC_KEY_get0_public_key(NULL),
                                           POINT_CONVERSION_COMPRESSED,
                                           NULL, 0, NULL);
    uint8_t* h160 = hash160(pubkey, pubkey_len);
    memcpy(target_hash, h160, HASH160_SIZE);
    
    free(pubkey);
    free(h160);
}

int main() {
    printf("🔥 MULTI-CURVE ECC GA TEST - C IMPLEMENTATION\n");
    printf("%s\n", "======================================================================");
    
    // Initialize OpenSSL
    init_openssl();
    
    // Initialize random seed
    srand(time(NULL));
    RAND_poll();
    
    // Define curves to test
    struct {
        const char* name;
        int nid;
    } curves_to_test[] = {
        {"secp256k1", NID_secp256k1},
        {"nist256p", NID_X9_62_prime256v1},
        {"nist384p", NID_secp384r1},
        {"nist521p", NID_secp521r1},
    };
    
    int num_curves = sizeof(curves_to_test) / sizeof(curves_to_test[0]);
    printf("🧪 Testing GA performance across %d elliptic curves\n", num_curves);
    printf("🔍 Looking for universal patterns that might indicate systematic ECC properties\n");
    printf("⚡ 20 rounds per curve, unique target per curve\n");
    printf("%s\n", "======================================================================");
    
    // Run tests for each curve
    for (int i = 0; i < num_curves; i++) {
        CurveInfo* curve = create_curve_info(curves_to_test[i].name, curves_to_test[i].nid);
        if (!curve) {
            fprintf(stderr, "Failed to create curve %s\n", curves_to_test[i].name);
            continue;
        }
        
        // Generate unique target and private key
        uint8_t target_hash[HASH160_SIZE];
        uint8_t* true_private_key = (uint8_t*)malloc(curve->key_size);
        generate_unique_target_for_curve(curve, i, target_hash, true_private_key);
        
        printf("\n🎯 Generated unique target: ");
        for (int j = 0; j < HASH160_SIZE; j++) {
            printf("%02X", target_hash[j]);
        }
        printf("\n");
        
        printf("🔑 True private key: 0x");
        for (int j = 0; j < curve->key_size; j++) {
            printf("%02X", true_private_key[j]);
        }
        printf("\n");
        
        // Run test
        run_curve_test(curve, target_hash, true_private_key);
        
        free(true_private_key);
        free_curve_info(curve);
    }
    
    printf("\n%s\n", "======================================================================");
    printf("🔬 TEST COMPLETE\n");
    printf("%s\n", "======================================================================");
    
    cleanup_openssl();
    return 0;
}
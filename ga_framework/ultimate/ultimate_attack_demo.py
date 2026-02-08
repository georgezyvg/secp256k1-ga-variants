import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import hashlib
from scipy.spatial import distance
from scipy.stats import chi2
import warnings
warnings.filterwarnings('ignore')

# secp256k1 parameters (Bitcoin's elliptic curve)
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F  # Field prime
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # Order
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798  # Generator x
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8  # Generator y
a = 0  # Curve parameter a
b = 7  # Curve parameter b

class BitcoinGeometryAnalyzer:
    def __init__(self, sample_size=10000):
        self.sample_size = sample_size
        self.results = {}
        
    def mod_inverse(self, a, m):
        """Modular inverse using extended Euclidean algorithm"""
        if a < 0:
            a = (a % m + m) % m
        g, x, _ = self.extended_gcd(a, m)
        if g != 1:
            raise Exception('Modular inverse does not exist')
        return x % m
    
    def extended_gcd(self, a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = self.extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y
    
    def point_add(self, p1, p2):
        """Add two points on the elliptic curve"""
        if p1 is None:
            return p2
        if p2 is None:
            return p1
        
        x1, y1 = p1
        x2, y2 = p2
        
        if x1 == x2:
            if y1 == y2:
                # Point doubling
                s = (3 * x1 * x1 + a) * self.mod_inverse(2 * y1, p) % p
            else:
                # Points are inverses
                return None
        else:
            # Point addition
            s = (y2 - y1) * self.mod_inverse(x2 - x1, p) % p
        
        x3 = (s * s - x1 - x2) % p
        y3 = (s * (x1 - x3) - y1) % p
        
        return (x3, y3)
    
    def scalar_mult(self, k, point):
        """Scalar multiplication on elliptic curve"""
        if k == 0:
            return None
        if k == 1:
            return point
        
        result = None
        addend = point
        
        while k:
            if k & 1:
                result = self.point_add(result, addend)
            addend = self.point_add(addend, addend)
            k >>= 1
        
        return result
    
    def hash160(self, data):
        """SHA256 followed by RIPEMD160"""
        sha256_hash = hashlib.sha256(data).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        return ripemd160.digest()
    
    def generate_samples(self):
        """Generate sample points across the cryptographic space"""
        print("Generating sample points...")
        # Generate random private keys using Python's random instead of numpy
        # to handle large integers properly on all platforms
        import random
        self.private_keys = []
        for _ in range(self.sample_size):
            # Generate random private key in range [1, n-1]
            priv_key = random.randint(1, n - 1)
            self.private_keys.append(priv_key)
        self.private_keys = np.array(self.private_keys, dtype=object)
        self.public_points = []
        self.hash160_values = []
        
        for i, priv_key in enumerate(self.private_keys):
            if i % 1000 == 0:
                print(f"Processing {i}/{self.sample_size}")
            
            # Generate public key
            pub_point = self.scalar_mult(int(priv_key), (Gx, Gy))
            self.public_points.append(pub_point)
            
            # Generate hash160
            if pub_point:
                x, y = pub_point
                # Compressed public key format
                prefix = b'\x02' if y % 2 == 0 else b'\x03'
                pub_key_bytes = prefix + x.to_bytes(32, 'big')
                h160 = self.hash160(pub_key_bytes)
                self.hash160_values.append(int.from_bytes(h160, 'big'))
            else:
                self.hash160_values.append(0)
    
    def normalize_coordinates(self, coords, max_val):
        """Normalize coordinates to [0, 1] range"""
        # Handle both regular arrays and object arrays with large integers
        coords_array = np.array(coords, dtype=np.float64)
        return coords_array / float(max_val)
    
    def test_torus_mapping(self):
        """Test if the structure maps to a torus"""
        print("\nTesting torus mapping...")
        
        # Map private keys to angle theta [0, 2π]
        theta = 2 * np.pi * self.normalize_coordinates(self.private_keys, n)
        
        # Map hash160 to angle phi [0, 2π]
        phi = 2 * np.pi * self.normalize_coordinates(self.hash160_values, 2**160)
        
        # Torus parameters
        R = 3  # Major radius
        r = 1  # Minor radius
        
        # Convert to 3D torus coordinates
        x = (R + r * np.cos(phi)) * np.cos(theta)
        y = (R + r * np.cos(phi)) * np.sin(theta)
        z = r * np.sin(phi)
        
        # Visualize
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z, c=theta, cmap='viridis', s=1, alpha=0.6)
        ax.set_title('Bitcoin Security Structure as Torus')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.colorbar(scatter, label='Private Key (normalized)')
        plt.savefig('btc_torus_mapping.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Test uniformity on torus surface
        self.results['torus_uniformity'] = self.test_uniformity_3d(x, y, z)
    
    def test_sphere_mapping(self):
        """Test if the structure maps to a sphere"""
        print("\nTesting sphere mapping...")
        
        # Map to spherical coordinates
        theta = 2 * np.pi * self.normalize_coordinates(self.private_keys, n)
        phi = np.pi * self.normalize_coordinates(self.hash160_values, 2**160)
        
        # Convert to 3D sphere coordinates
        x = np.sin(phi) * np.cos(theta)
        y = np.sin(phi) * np.sin(theta)
        z = np.cos(phi)
        
        # Visualize
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z, c=theta, cmap='plasma', s=1, alpha=0.6)
        ax.set_title('Bitcoin Security Structure as Sphere')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.colorbar(scatter, label='Private Key (normalized)')
        plt.savefig('btc_sphere_mapping.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Test uniformity on sphere surface
        self.results['sphere_uniformity'] = self.test_uniformity_3d(x, y, z)
    
    def test_klein_bottle_mapping(self):
        """Test if the structure maps to a Klein bottle"""
        print("\nTesting Klein bottle mapping...")
        
        u = 2 * np.pi * self.normalize_coordinates(self.private_keys, n)
        v = 2 * np.pi * self.normalize_coordinates(self.hash160_values, 2**160)
        
        # Klein bottle immersion in 3D
        x = (2 + np.cos(v)) * np.cos(u)
        y = (2 + np.cos(v)) * np.sin(u)
        z = np.sin(v) * (1 + np.sin(u))
        
        # Visualize
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z, c=u, cmap='coolwarm', s=1, alpha=0.6)
        ax.set_title('Bitcoin Security Structure as Klein Bottle')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.colorbar(scatter, label='Private Key (normalized)')
        plt.savefig('btc_klein_bottle_mapping.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.results['klein_bottle_uniformity'] = self.test_uniformity_3d(x, y, z)
    
    def test_mobius_strip_mapping(self):
        """Test if the structure maps to a Möbius strip"""
        print("\nTesting Möbius strip mapping...")
        
        s = 2 * self.normalize_coordinates(self.private_keys, n) - 1  # [-1, 1]
        t = 2 * np.pi * self.normalize_coordinates(self.hash160_values, 2**160)
        
        # Möbius strip parametrization
        x = (1 + s/2 * np.cos(t/2)) * np.cos(t)
        y = (1 + s/2 * np.cos(t/2)) * np.sin(t)
        z = s/2 * np.sin(t/2)
        
        # Visualize
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z, c=t, cmap='twilight', s=1, alpha=0.6)
        ax.set_title('Bitcoin Security Structure as Möbius Strip')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.colorbar(scatter, label='Hash160 (normalized)')
        plt.savefig('btc_mobius_strip_mapping.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.results['mobius_uniformity'] = self.test_uniformity_3d(x, y, z)
    
    def test_projective_plane_mapping(self):
        """Test mapping to projective plane (Boy's surface)"""
        print("\nTesting projective plane (Boy's surface) mapping...")
        
        u = np.pi * self.normalize_coordinates(self.private_keys, n)
        v = np.pi * self.normalize_coordinates(self.hash160_values, 2**160)
        
        # Boy's surface parametrization
        denom = 3 + np.sqrt(2) * (np.sin(2*u) * np.cos(v) - np.sin(u) * np.sin(2*v))
        x = (np.sqrt(2) * np.cos(2*u) * np.cos(v)**2 + np.cos(u) * np.sin(2*v)) / denom
        y = (np.sqrt(2) * np.sin(2*u) * np.cos(v)**2 - np.sin(u) * np.sin(2*v)) / denom
        z = (3 * np.cos(v)**2) / denom
        
        # Visualize
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x, y, z, c=u, cmap='rainbow', s=1, alpha=0.6)
        ax.set_title("Bitcoin Security Structure as Boy's Surface (Projective Plane)")
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.colorbar(scatter, label='Private Key (normalized)')
        plt.savefig('btc_projective_plane_mapping.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        self.results['projective_plane_uniformity'] = self.test_uniformity_3d(x, y, z)
    
    def test_elliptic_curve_structure(self):
        """Visualize the actual elliptic curve structure"""
        print("\nVisualizing elliptic curve structure...")
        
        # Extract x, y coordinates from public points
        x_coords = []
        y_coords = []
        for point in self.public_points:
            if point:
                x, y = point
                x_coords.append(x)
                y_coords.append(y)
        
        # Normalize to [0, 1]
        x_norm = np.array(x_coords) / p
        y_norm = np.array(y_coords) / p
        
        # 2D visualization
        plt.figure(figsize=(12, 10))
        # Convert private keys to float for colormap
        priv_keys_float = np.array(self.private_keys[:len(x_coords)], dtype=np.float64)
        plt.scatter(x_norm, y_norm, c=priv_keys_float, 
                   cmap='viridis', s=1, alpha=0.6)
        plt.title('Elliptic Curve Points Distribution')
        plt.xlabel('X coordinate (normalized)')
        plt.ylabel('Y coordinate (normalized)')
        plt.colorbar(label='Private Key')
        plt.savefig('btc_elliptic_curve_2d.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3D visualization with hash160 as z-axis
        z_coords = self.normalize_coordinates(self.hash160_values[:len(x_coords)], 2**160)
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x_norm, y_norm, z_coords, 
                           c=priv_keys_float, 
                           cmap='viridis', s=1, alpha=0.6)
        ax.set_title('Bitcoin Security Structure: EC + Hash160')
        ax.set_xlabel('Public Key X (normalized)')
        ax.set_ylabel('Public Key Y (normalized)')
        ax.set_zlabel('Hash160 (normalized)')
        plt.colorbar(scatter, label='Private Key')
        plt.savefig('btc_elliptic_curve_3d.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def test_uniformity_3d(self, x, y, z):
        """Test uniformity of distribution in 3D space"""
        # Compute nearest neighbor distances
        points = np.column_stack((x, y, z))
        sample_indices = np.random.choice(len(points), min(1000, len(points)), replace=False)
        
        nn_distances = []
        for i in sample_indices:
            dists = distance.cdist([points[i]], points)
            # Get second smallest (first is 0 - distance to itself)
            nn_dist = np.partition(dists[0], 1)[1]
            nn_distances.append(nn_dist)
        
        # Chi-square test for uniformity
        hist, _ = np.histogram(nn_distances, bins=20)
        expected = len(nn_distances) / 20
        chi2_stat = np.sum((hist - expected)**2 / expected)
        p_value = 1 - chi2.cdf(chi2_stat, df=19)
        
        return {
            'mean_nn_distance': np.mean(nn_distances),
            'std_nn_distance': np.std(nn_distances),
            'chi2_statistic': chi2_stat,
            'p_value': p_value,
            'is_uniform': p_value > 0.05
        }
    
    def test_phase_space_topology(self):
        """Analyze the topology of the phase space"""
        print("\nAnalyzing phase space topology...")
        
        # Create phase space: (private_key, public_key_x, hash160)
        phase_points = []
        for i, (priv, pub, h160) in enumerate(zip(self.private_keys, 
                                                   self.public_points, 
                                                   self.hash160_values)):
            if pub:
                x, _ = pub
                phase_points.append([
                    float(priv) / float(n),
                    float(x) / float(p),
                    float(h160) / float(2**160)
                ])
        
        phase_points = np.array(phase_points)
        
        # Visualize phase space
        fig = plt.figure(figsize=(15, 5))
        
        # Private key vs Public key X
        ax1 = fig.add_subplot(131)
        ax1.scatter(phase_points[:, 0], phase_points[:, 1], s=1, alpha=0.5)
        ax1.set_xlabel('Private Key (normalized)')
        ax1.set_ylabel('Public Key X (normalized)')
        ax1.set_title('Private Key vs Public Key X')
        
        # Private key vs Hash160
        ax2 = fig.add_subplot(132)
        ax2.scatter(phase_points[:, 0], phase_points[:, 2], s=1, alpha=0.5)
        ax2.set_xlabel('Private Key (normalized)')
        ax2.set_ylabel('Hash160 (normalized)')
        ax2.set_title('Private Key vs Hash160')
        
        # Public key X vs Hash160
        ax3 = fig.add_subplot(133)
        ax3.scatter(phase_points[:, 1], phase_points[:, 2], s=1, alpha=0.5)
        ax3.set_xlabel('Public Key X (normalized)')
        ax3.set_ylabel('Hash160 (normalized)')
        ax3.set_title('Public Key X vs Hash160')
        
        plt.tight_layout()
        plt.savefig('btc_phase_space_topology.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def summarize_results(self):
        """Summarize and save analysis results"""
        print("\n" + "="*50)
        print("BITCOIN SECURITY GEOMETRY ANALYSIS RESULTS")
        print("="*50)
        
        shapes = ['torus', 'sphere', 'klein_bottle', 'mobius', 'projective_plane']
        uniformity_scores = {}
        
        for shape in shapes:
            key = f'{shape}_uniformity'
            if key in self.results:
                uniformity = self.results[key]
                uniformity_scores[shape] = uniformity['p_value']
                print(f"\n{shape.upper()} MAPPING:")
                print(f"  - Mean NN distance: {uniformity['mean_nn_distance']:.6f}")
                print(f"  - Std NN distance: {uniformity['std_nn_distance']:.6f}")
                print(f"  - Chi-square stat: {uniformity['chi2_statistic']:.4f}")
                print(f"  - P-value: {uniformity['p_value']:.4f}")
                print(f"  - Uniform distribution: {'YES' if uniformity['is_uniform'] else 'NO'}")
        
        # Find best fitting shape
        if uniformity_scores:
            best_shape = max(uniformity_scores, key=uniformity_scores.get)
            print(f"\n{'='*50}")
            print(f"BEST FITTING SHAPE: {best_shape.upper()}")
            print(f"Confidence (p-value): {uniformity_scores[best_shape]:.4f}")
            print("="*50)
        
        # Save results to file
        with open('btc_geometry_analysis_results.txt', 'w') as f:
            f.write("BITCOIN SECURITY GEOMETRY ANALYSIS RESULTS\n")
            f.write("="*50 + "\n\n")
            for shape, score in uniformity_scores.items():
                f.write(f"{shape}: p-value = {score:.6f}\n")
            f.write(f"\nBest fitting shape: {best_shape}\n")
    
    def run_full_analysis(self):
        """Run complete geometric analysis"""
        self.generate_samples()
        self.test_elliptic_curve_structure()
        self.test_phase_space_topology()
        self.test_torus_mapping()
        self.test_sphere_mapping()
        self.test_klein_bottle_mapping()
        self.test_mobius_strip_mapping()
        self.test_projective_plane_mapping()
        self.summarize_results()
        print("\nAnalysis complete! Check the generated PNG files.")

# Run the analysis
if __name__ == "__main__":
    analyzer = BitcoinGeometryAnalyzer(sample_size=10000)
    analyzer.run_full_analysis()
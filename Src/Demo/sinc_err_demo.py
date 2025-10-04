import numpy as np
import matplotlib.pyplot as plt

from Allocator.Interpreter.poly.sinc_err import sinc_err


x_values = np.linspace(0.1, 5, 200)
N = 50  # Number of terms (sum goes to 2N)
results = sinc_err(x_values, N)
real_parts = results.real
imag_parts = results.imag
fig = plt.figure(figsize=(15, 10))

# 1. Real and Imaginary parts vs x
ax1 = plt.subplot(2, 2, 1)
ax1.plot(x_values, real_parts, 'b-', linewidth=2, label='Real part')
ax1.plot(x_values, imag_parts, 'r-', linewidth=2, label='Imaginary part')
ax1.grid(True, alpha=0.3)
ax1.set_xlabel('x', fontsize=12)
ax1.set_ylabel('Value', fontsize=12)
ax1.set_title('Real and Imaginary Parts vs x', fontsize=14, fontweight='bold')
ax1.legend(fontsize=11)
ax1.axhline(y=0, color='k', linestyle='--', alpha=0.3)

# 2. 3D Complex plot (Real, Imaginary, x)
ax2 = plt.subplot(2, 2, 2, projection='3d')
scatter = ax2.scatter(real_parts, imag_parts, x_values, c=x_values,
                      cmap='viridis', s=20, alpha=0.6)
ax2.plot(real_parts, imag_parts, x_values, 'k-', alpha=0.3, linewidth=0.5)
ax2.set_xlabel('Real part', fontsize=10)
ax2.set_ylabel('Imaginary part', fontsize=10)
ax2.set_zlabel('x', fontsize=10)
ax2.set_title('3D Complex Plot', fontsize=14, fontweight='bold')
cbar = plt.colorbar(scatter, ax=ax2, shrink=0.6, pad=0.1)
cbar.set_label('x value', fontsize=10)

# Mark start and end points
ax2.scatter(real_parts[0], imag_parts[0], x_values[0],
            color='green', s=100, marker='o', label=f'x={x_values[0]:.1f}',
            edgecolors='black', linewidths=2, zorder=5)
ax2.scatter(real_parts[-1], imag_parts[-1], x_values[-1],
            color='red', s=100, marker='o', label=f'x={x_values[-1]:.1f}',
            edgecolors='black', linewidths=2, zorder=5)
ax2.legend(fontsize=9)

# 3. Magnitude vs x
ax3 = plt.subplot(2, 2, 3)
magnitude = np.abs(results)
ax3.plot(x_values, magnitude, 'g-', linewidth=2)
ax3.grid(True, alpha=0.3)
ax3.set_xlabel('x', fontsize=12)
ax3.set_ylabel('|f(x)|', fontsize=12)
ax3.set_title('Magnitude vs x', fontsize=14, fontweight='bold')

# 4. Phase (argument) vs x
ax4 = plt.subplot(2, 2, 4)
phase = np.angle(results)
ax4.plot(x_values, phase, 'm-', linewidth=2)
ax4.grid(True, alpha=0.3)
ax4.set_xlabel('x', fontsize=12)
ax4.set_ylabel('arg(f(x)) [radians]', fontsize=12)
ax4.set_title('Phase vs x', fontsize=14, fontweight='bold')
ax4.axhline(y=0, color='k', linestyle='--', alpha=0.3)
ax4.axhline(y=np.pi, color='k', linestyle='--', alpha=0.3)
ax4.axhline(y=-np.pi, color='k', linestyle='--', alpha=0.3)

plt.tight_layout()
plt.show()

print('\nStatistics:')
print(f"x range: [{x_values[0]:.2f}, {x_values[-1]:.2f}]")
print(f"Real part range: [{real_parts.min():.6f}, {real_parts.max():.6f}]")
print(f"Imaginary part range: [{imag_parts.min():.6f}, {imag_parts.max():.6f}]")
print(f"Magnitude range: [{magnitude.min():.6f}, {magnitude.max():.6f}]")
print(f"Number of terms in sum: 2N = {2*N}")

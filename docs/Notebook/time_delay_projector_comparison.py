#!/usr/bin/env python3
"""
Visualize the time-delay projector for exponential kernels H_a(ω) = e^(aω).

Compares:
1. Hyperbolic form (complex ω-plane integrals with cosh/sinh)
2. Trigonometric form (real z, residues give cos/sin)
3. Both poles enclosed (ω = ±iz) vs single pole (ω = iz)

For time-delay kernel h_a(t) = δ(t - t₀), we have a = -t₀.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import gamma
import matplotlib.gridspec as gridspec

# Parameters
N = 5  # Truncation order
t0 = 0.5  # Time delay
z_min, z_max = -4, 4
num_points = 500

z_vals = np.linspace(z_min, z_max, num_points)
z_vals = z_vals[z_vals != 0]  # Avoid singularity at z=0


def sinc_N_even(z, N):
    """Even part of truncated sinc: sum_{k=0}^{N} (-1)^k z^(2k) / (2k+1)!"""
    result = np.zeros_like(z, dtype=complex)
    for k in range(N + 1):
        result += ((-1) ** k * z ** (2 * k)) / gamma(2 * k + 2)
    return result


def sinc_N_odd(z, N):
    """Odd part from S_odd (even powers only): sum_{k=0}^{N-1} (-1)^k z^(2k) / (2k+1)!"""
    result = np.zeros_like(z, dtype=complex)
    for k in range(N):
        result += ((-1) ** k * z ** (2 * k)) / gamma(2 * k + 2)
    return result


def S_odd_full(omega):
    """Full S_odd(ω) = sum_{n=0}^{2N-1} ω^n / (n+1)!"""
    result = np.zeros_like(omega, dtype=complex)
    for n in range(2 * N):
        result += omega**n / gamma(n + 2)
    return result


# ==============================================================================
# Case 1: Trigonometric form (z ∈ ℝ, residues at ω = ±iz)
# ==============================================================================

# Both poles enclosed: ω = iz and ω = -iz
P_even_trig_both = np.cos(t0 * z_vals) * sinc_N_even(z_vals, N)
P_odd_trig_both = -1j * np.sin(t0 * z_vals) * sinc_N_odd(z_vals, N)
P_total_trig_both = P_even_trig_both + P_odd_trig_both

# Single pole enclosed: ω = iz only
# Res at ω=iz for even: S_even(iz)·cosh(a·iz) / (2iz) = S_even(iz)·cos(az) / (2iz)
# With prefactor 1/(2πi), result is: cos(az)·sinc_N_even(z) / (2iz) · (2πi) = π·cos(az)·sinc_N_even(z) / z
P_even_trig_single = (np.pi / z_vals) * np.cos(t0 * z_vals) * sinc_N_even(z_vals, N)

# Res at ω=iz for odd: S_odd(iz)·sinh(a·iz) / (2iz) = S_odd(iz)·i·sin(az) / (2iz)
# S_odd(iz) is complex, let's use the full form
omega_at_pole = 1j * z_vals
S_odd_iz = S_odd_full(omega_at_pole)
# Residue: S_odd(iz)·i·sin(az) / (2iz), prefactor z/(2π), gives: z·i·sin(az)·S_odd(iz) / (2iz) · (2πi) = -π·sin(az)·S_odd(iz) / 2
P_odd_trig_single = -(np.pi / 2) * np.sin(t0 * z_vals) * S_odd_iz

P_total_trig_single = P_even_trig_single + P_odd_trig_single


# ==============================================================================
# Case 2: Hyperbolic form (complex z, evaluate with hyperbolic functions)
# ==============================================================================

# For complex z, we evaluate at the poles but keep hyperbolic form
# This is more relevant when z is complex, but we'll show it for real z too

# Both poles: same as trigonometric (they're equivalent for real z)
# But let's compute it using the hyperbolic identities to show equivalence
z_complex = z_vals.astype(complex)  # Treat as complex even though real

# At ω = iz: cosh(a·iz) = cos(az), sinh(a·iz) = i·sin(az)
P_even_hyp_both = np.cos(-t0 * z_complex) * sinc_N_even(z_complex, N)  # a = -t₀
P_odd_hyp_both = -1j * np.sin(-t0 * z_complex) * sinc_N_odd(z_complex, N)
P_total_hyp_both = P_even_hyp_both + P_odd_hyp_both

# Single pole (hyperbolic form, showing same result)
P_even_hyp_single = (np.pi / z_complex) * np.cos(-t0 * z_complex) * sinc_N_even(
    z_complex, N
)
omega_poles = 1j * z_complex
P_odd_hyp_single = -(np.pi / 2) * np.sin(-t0 * z_complex) * S_odd_full(omega_poles)
P_total_hyp_single = P_even_hyp_single + P_odd_hyp_single


# ==============================================================================
# Plotting
# ==============================================================================

fig = plt.figure(figsize=(16, 12))
gs = gridspec.GridSpec(3, 2, hspace=0.3, wspace=0.3)

# Color scheme
color_both = "#2E86AB"  # Blue for both poles
color_single = "#A23B72"  # Purple for single pole
color_even = "#F18F01"  # Orange for even
color_odd = "#C73E1D"  # Red for odd

# ------------------------- Trigonometric Form -------------------------
# Row 1: Even projector
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(
    z_vals, np.real(P_even_trig_both), color=color_both, linewidth=2, label="Both poles"
)
ax1.plot(
    z_vals,
    np.real(P_even_trig_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    label="Single pole (ω=iz)",
)
ax1.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax1.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax1.set_xlabel("z", fontsize=12)
ax1.set_ylabel("Re(P_even)", fontsize=12)
ax1.set_title(
    f"Even Projector (Trigonometric)\ncos(t₀z)·sinc_N(z), t₀={t0}, N={N}",
    fontsize=13,
    fontweight="bold",
)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# Row 1: Odd projector
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(
    z_vals,
    np.imag(P_odd_trig_both),
    color=color_both,
    linewidth=2,
    label="Both poles (imaginary part)",
)
ax2.plot(
    z_vals,
    np.imag(P_odd_trig_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    label="Single pole (imaginary part)",
)
ax2.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax2.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax2.set_xlabel("z", fontsize=12)
ax2.set_ylabel("Im(P_odd)", fontsize=12)
ax2.set_title(
    f"Odd Projector (Trigonometric)\n-i·sin(t₀z)·sinc_N(z), t₀={t0}, N={N}",
    fontsize=13,
    fontweight="bold",
)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# ------------------------- Combined Projectors -------------------------
# Row 2: Total projector (real part)
ax3 = fig.add_subplot(gs[1, 0])
ax3.plot(
    z_vals,
    np.real(P_total_trig_both),
    color=color_both,
    linewidth=2.5,
    label="Both poles (symmetric)",
)
ax3.plot(
    z_vals,
    np.real(P_total_trig_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    label="Single pole (causal)",
)
ax3.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax3.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax3.set_xlabel("z", fontsize=12)
ax3.set_ylabel("Re(P_N)", fontsize=12)
ax3.set_title(
    f"Total Projector - Real Part\nP_N[sinc * δ(t-t₀)](z), t₀={t0}",
    fontsize=13,
    fontweight="bold",
)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# Row 2: Total projector (imaginary part)
ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(
    z_vals,
    np.imag(P_total_trig_both),
    color=color_both,
    linewidth=2.5,
    label="Both poles (symmetric)",
)
ax4.plot(
    z_vals,
    np.imag(P_total_trig_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    label="Single pole (causal)",
)
ax4.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax4.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax4.set_xlabel("z", fontsize=12)
ax4.set_ylabel("Im(P_N)", fontsize=12)
ax4.set_title(
    f"Total Projector - Imaginary Part\nP_N[sinc * δ(t-t₀)](z), t₀={t0}",
    fontsize=13,
    fontweight="bold",
)
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3)

# ------------------------- Magnitude and Phase -------------------------
# Row 3: Magnitude
ax5 = fig.add_subplot(gs[2, 0])
ax5.plot(
    z_vals,
    np.abs(P_total_trig_both),
    color=color_both,
    linewidth=2.5,
    label="Both poles (linear phase)",
)
ax5.plot(
    z_vals,
    np.abs(P_total_trig_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    label="Single pole (non-linear phase)",
)
ax5.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax5.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax5.set_xlabel("z", fontsize=12)
ax5.set_ylabel("|P_N|", fontsize=12)
ax5.set_title("Magnitude Response", fontsize=13, fontweight="bold")
ax5.legend(fontsize=10)
ax5.grid(True, alpha=0.3)

# Row 3: Phase
ax6 = fig.add_subplot(gs[2, 1])
phase_both = np.angle(P_total_trig_both)
phase_single = np.angle(P_total_trig_single)
ax6.plot(z_vals, phase_both, color=color_both, linewidth=2.5, label="Both poles")
ax6.plot(
    z_vals, phase_single, color=color_single, linewidth=2, linestyle="--", label="Single pole"
)
ax6.axhline(0, color="black", linewidth=0.5, linestyle=":")
ax6.axvline(0, color="black", linewidth=0.5, linestyle=":")
ax6.set_xlabel("z", fontsize=12)
ax6.set_ylabel("Phase (radians)", fontsize=12)
ax6.set_title("Phase Response", fontsize=13, fontweight="bold")
ax6.legend(fontsize=10)
ax6.grid(True, alpha=0.3)

plt.suptitle(
    f"Time-Delay Projector Comparison: h_a(t) = δ(t - {t0})\n"
    f"Hyperbolic vs Trigonometric Forms, Both Poles vs Single Pole",
    fontsize=16,
    fontweight="bold",
    y=0.995,
)

plt.savefig(
    "/home/tophurt/Desktop/Thesis/docs/resources/imgs/time_delay_projector_comparison.png",
    dpi=300,
    bbox_inches="tight",
)
print(
    "✓ Saved: docs/resources/imgs/time_delay_projector_comparison.png"
)

# ==============================================================================
# Additional plot: Direct comparison of hyperbolic vs trigonometric
# ==============================================================================

fig2, axes = plt.subplots(2, 2, figsize=(14, 10))

# Verify they're identical for real z
axes[0, 0].plot(
    z_vals, np.real(P_total_trig_both), color=color_both, linewidth=2, label="Trigonometric"
)
axes[0, 0].plot(
    z_vals,
    np.real(P_total_hyp_both),
    color=color_single,
    linewidth=2,
    linestyle="--",
    alpha=0.7,
    label="Hyperbolic",
)
axes[0, 0].set_title("Both Poles - Real Part\n(Should overlap for z ∈ ℝ)", fontsize=12)
axes[0, 0].set_xlabel("z")
axes[0, 0].set_ylabel("Re(P_N)")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].plot(
    z_vals, np.imag(P_total_trig_both), color=color_both, linewidth=2, label="Trigonometric"
)
axes[0, 1].plot(
    z_vals,
    np.imag(P_total_hyp_both),
    color=color_single,
    linewidth=2,
    linestyle="--",
    alpha=0.7,
    label="Hyperbolic",
)
axes[0, 1].set_title("Both Poles - Imaginary Part", fontsize=12)
axes[0, 1].set_xlabel("z")
axes[0, 1].set_ylabel("Im(P_N)")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].plot(
    z_vals,
    np.real(P_total_trig_single),
    color=color_both,
    linewidth=2,
    label="Trigonometric",
)
axes[1, 0].plot(
    z_vals,
    np.real(P_total_hyp_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    alpha=0.7,
    label="Hyperbolic",
)
axes[1, 0].set_title("Single Pole (ω=iz) - Real Part", fontsize=12)
axes[1, 0].set_xlabel("z")
axes[1, 0].set_ylabel("Re(P_N)")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].plot(
    z_vals,
    np.imag(P_total_trig_single),
    color=color_both,
    linewidth=2,
    label="Trigonometric",
)
axes[1, 1].plot(
    z_vals,
    np.imag(P_total_hyp_single),
    color=color_single,
    linewidth=2,
    linestyle="--",
    alpha=0.7,
    label="Hyperbolic",
)
axes[1, 1].set_title("Single Pole (ω=iz) - Imaginary Part", fontsize=12)
axes[1, 1].set_xlabel("z")
axes[1, 1].set_ylabel("Im(P_N)")
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.suptitle(
    "Trigonometric-Hyperbolic Equivalence for z ∈ ℝ\n"
    f"(Curves should overlap perfectly, t₀={t0}, N={N})",
    fontsize=14,
    fontweight="bold",
)
plt.tight_layout()

plt.savefig(
    "/home/tophurt/Desktop/Thesis/docs/resources/imgs/trig_hyp_equivalence.png",
    dpi=300,
    bbox_inches="tight",
)
print("✓ Saved: docs/resources/imgs/trig_hyp_equivalence.png")

plt.show()

print("\n" + "=" * 70)
print("Summary:")
print("=" * 70)
print(f"Time delay: t₀ = {t0}")
print(f"Truncation order: N = {N}")
print(f"\nFor z ∈ ℝ, hyperbolic and trigonometric forms are IDENTICAL")
print("because cosh(iz) = cos(z) and sinh(iz) = i·sin(z)")
print("\nKey differences:")
print("  • Both poles enclosed → Symmetric response (linear phase)")
print("  • Single pole (ω=iz) → Asymmetric response (causal, non-linear phase)")
print("=" * 70)

"""
Plot the truncation error R_N(z) = sinc(pi*z) - P_N(z) = (-1)^{N+1} (pi*z)^S / Gamma(S+2) * H_S(pi*z),
with S = 2(N+1) and H_S(w) = {}_1F_2(1; S/2+1, S/2+3/2; -w^2/4), using a stable series for {}_1F_2.
Saves a 3D surface and a log10-magnitude heatmap (PNG and PDF) for LaTeX inclusion.
"""

import numpy as np
import matplotlib.pyplot as plt

from scipy.special import gammaln
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from consts import IMGS_DIR


def hyp1f2_series_w(w, S, tol=1e-12, max_terms=5000):
    w = np.asarray(w, dtype=np.float64)
    x = -0.25 * w**2
    b = 0.5 * S + 1.0
    c = 0.5 * S + 1.5
    term = np.ones_like(w)
    s = term.copy()
    m = 0
    while m < max_terms:
        term = term * x / ((b + m) * (c + m))
        s += term
        if np.max(np.abs(term)) < tol:
            break
        m += 1
    return s


def truncation_error_grid(N_vals, z_vals):
    N_vals = np.asarray(N_vals, dtype=int)
    z_vals = np.asarray(z_vals, dtype=np.float64)
    W = np.pi * z_vals
    R = np.empty((len(N_vals), len(z_vals)), dtype=np.float64)
    with np.errstate(divide='ignore', invalid='ignore'):
        logW = np.where(W > 0.0, np.log(W), 0.0)
    for i, N in enumerate(N_vals):
        S = 2 * (N + 1)
        H = hyp1f2_series_w(W, S)
        with np.errstate(divide='ignore', invalid='ignore'):
            logcoef = S * logW - gammaln(S + 2.0)
            coef = np.where(W > 0.0, np.exp(logcoef), 0.0)
        R[i, :] = ((-1) ** (N + 1)) * coef * H
    return R


if __name__ == '__main__':
    N_vals = np.arange(0, 26, 1)
    z_vals = np.linspace(0.0, 12.0, 480)
    R = truncation_error_grid(N_vals, z_vals)
    Z, NN = np.meshgrid(z_vals, N_vals)

    eps = 1e-300
    Rlog = np.log10(np.abs(R) + eps)

    fig1, ax1 = plt.subplots(figsize=(8.4, 4.8))
    im = ax1.imshow(Rlog, extent=[z_vals.min(), z_vals.max(), N_vals.min(), N_vals.max()], origin='lower', aspect='auto')
    z_line = np.linspace(z_vals.min(), z_vals.max(), 400)
    N_star = (np.pi * z_line - 3.0) / 2.0
    ax1.plot(z_line, N_star, linestyle='--', linewidth=1.2, color='w')
    ax1.set_xlabel(r'$z$')
    ax1.set_ylabel(r'$N$')
    ax1.set_title(r'$\log_{10}\!\left|R_N(z)\right|,\quad R_N(z)=(-1)^{N+1}\,(\pi z)^S/\Gamma(S{+}2)\cdot{}_1F_2\!\left(1;\,S/2+1,\,S/2+3/2;\,-(\pi z)^2/4\right)$'+'\n'+r'with $S=2(N+1)$ and guide $N^\star\approx(\pi z-3)/2$')
    cbar = plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label(r'$\log_{10}|R_N(z)|$')
    plt.tight_layout()
    plt.savefig(IMGS_DIR / 'truncation_error_heatmap.png', dpi=300, bbox_inches='tight')

    z_samples = np.array([1.0, 2.0, 3.0, 4.5, 6.0, 8.0, 10.0])
    fig2, ax2 = plt.subplots(figsize=(8.4, 4.8))
    for z0 in z_samples:
        idx = np.argmin(np.abs(z_vals - z0))
        y = Rlog[:, idx]
        ax2.plot(N_vals, y, label=fr"$z={z0:g}$")
        Nstar = (np.pi * z0 - 3.0) / 2.0
        ax2.axvline(Nstar, linestyle='--', linewidth=1.0, color=ax2.lines[-1].get_color(), alpha=0.7)

    ax2.set_xlabel(r'$N$')
    ax2.set_ylabel(r'$\log_{10}|R_N(z)|$')
    ax2.set_title(r'Fixed-$z$ slices: truncation error decays beyond $N^\star\approx(\pi z-3)/2$')
    ax2.legend(ncol=3, fontsize=9)
    plt.tight_layout()
    plt.savefig(IMGS_DIR / 'truncation_error_slices.png', dpi=300, bbox_inches='tight')
    plt.show()

"""
Plot A(N,z) = (-1)^N * z^S / Gamma(S+2) * H_S(z) with S=2(N+1) and H_S(z) = 1F2(1; S/2+1, S/2+3/2; -z^2/4).
Saves both PNG (raster) and PDF (vector) for LaTeX inclusion.
"""

import numpy as np
from scipy import special as sp
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

def H_S(z, S):
    return sp.hyp1f2(1.0, S/2.0 + 1.0, S/2.0 + 1.5, - (z**2) / 4.0)

def A_grid(N_vals, z_vals):
    A = np.empty((len(N_vals), len(z_vals)), dtype=np.float64)
    for i, N in enumerate(N_vals):
        S = 2 * (N + 1)
        H = H_S(z_vals, S)
        coef = ((-1) ** N) * (z_vals ** S) / np.exp(sp.gammaln(S + 2.0))
        A[i, :] = coef * H
    return A

if __name__ == "__main__":
    N_vals = np.arange(0, 13, 1)
    z_vals = np.linspace(0.0, 10.0, 200)
    A = A_grid(N_vals, z_vals)

    Z, NN = np.meshgrid(z_vals, N_vals)

    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(Z, NN, A, linewidth=0, antialiased=True)

    ax.set_xlabel(r"$z$")
    ax.set_ylabel(r"$N$")
    ax.set_zlabel(r"$(-1)^{N} z^{S}/\Gamma(S{+}2)\,\mathcal{H}_{S}(z)$" + "\n" + r"$(S=2(N{+}1))$")
    ax.set_title(r"$A(N,z)=(-1)^{N} z^{S}/\Gamma(S{+}2)\cdot{}_1F_2\!\left(1;\,S/2+1,\,S/2+3/2;\,-z^{2}/4\right)$")

    ax.view_init(elev=25, azim=-60)
    plt.tight_layout()

    # plt.savefig("sinc_projector_remainder_surface.png", dpi=300, bbox_inches="tight")
    # plt.savefig("sinc_projector_remainder_surface.pdf", bbox_inches="tight")
    plt.show()

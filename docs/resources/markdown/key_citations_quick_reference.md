# Key Citations Quick Reference

## Essential References by Topic

### Shannon Wavelets & Bandlimited Reconstruction

1. **Unser2000** - "Sampling—50 Years After Shannon"
   - **THE** comprehensive review of Shannon wavelets
   - Perfect reconstruction from samples
   - Reproducing kernel property
   - **USE FOR:** Justifying Shannon wavelet choice, sampling theory foundations

2. **Walter1992Shannon** - "A sampling theorem for wavelet subspaces"
   - Proves Shannon wavelets enable perfect reconstruction
   - Sampling in wavelet subspaces
   - **USE FOR:** Theoretical foundation of your wavelet decomposition

3. **Daubechies1992** - "Ten Lectures on Wavelets"
   - Standard comprehensive wavelet reference
   - Orthonormality, multiresolution analysis
   - **USE FOR:** General wavelet theory (already cited)

4. **Mallat1989** - "A Theory for Multiresolution Signal Decomposition"
   - Multiresolution analysis (MRA) framework
   - Fast wavelet transform algorithm
   - **USE FOR:** Fast implementation via filter banks (already cited)

### Paley-Wiener Theory (Bandlimited → Entire Functions)

5. **PaleyWiener1934** - "Fourier Transforms in the Complex Domain"
   - **FOUNDATIONAL** - bandlimited functions are entire
   - Proves: entire function determined by values on any interval
   - **USE FOR:** Justifying fundamental domain reconstruction possibility

6. **Rudin1987** - "Real and Complex Analysis" (Ch. 19-20)
   - Modern treatment of Paley-Wiener theorems
   - Bandlimited functions form closed subspace
   - **USE FOR:** Accessible modern reference for Paley-Wiener

### Harmonic Analysis & Periodic Decomposition

7. **Katznelson2004** - "An Introduction to Harmonic Analysis"
   - Fourier series for periodic functions
   - Commensurable periods → periodic composite (your T = lcm(T₀,...,Tₙ))
   - **USE FOR:** Connecting cyclostationarity to harmonic structure

8. **Benedetto1997** - "Modern Sampling Theory"
   - Multi-band signals and wavelets
   - Sampling per frequency band
   - **USE FOR:** Multi-band decomposition framework

### Symmetry Exploitation & Domain Reduction

9. **Muller2006** - "Elementary Functions: Algorithms and Implementation"
   - **DEFINITIVE** reference on argument reduction
   - Chapter 4: Range reduction techniques
   - Complexity analysis: when is τ(x) worth it?
   - **USE FOR:** Your recovery method τ(x), arccos example, complexity justification

10. **Meher2008** - "50 Years of CORDIC"
    - Comprehensive CORDIC review
    - Quarter-domain sin(x) reduction (your example!)
    - Symmetry-based computation
    - **USE FOR:** Classic example of domain reduction, FPGA context

11. **Detrey2007** - "Table-based polynomials for fast hardware function evaluation"
    - State-of-the-art FPGA LUT methods
    - Exploiting periodicity/symmetry
    - 4-8× memory reduction demonstrated
    - **USE FOR:** FPGA-specific LUT optimization, hardware synthesis

### Extended/Generalized Sampling Theory

12. **Landau1967** - "Sampling, data transmission, and the Nyquist rate"
    - Extension of Shannon sampling
    - Bandlimited signal spaces
    - **USE FOR:** Sampling rate reduction theoretical basis

13. **Higgins1996** - "Sampling Theory in Fourier and Signal Analysis"
    - Comprehensive sampling theory
    - Reconstruction and interpolation
    - **USE FOR:** General sampling reference

14. **Aldroubi1995** - "Sampling procedures in function spaces"
    - Generalization: harmonic structure → reduced sampling
    - Asymptotic equivalence with Shannon
    - **USE FOR:** Connecting harmonic structure to sampling requirements

### Quasi-Periodic & Non-Ideal Signals

15. **Janssen1988** - "The Zak transform and sampling theorems for wavelet subspaces"
    - Zak transform for quasi-periodic signals
    - Maps time-frequency to 2D fundamental domain
    - **USE FOR:** Extension to approximately periodic signals

16. **Butzer1983** - "Sampling theory for not necessarily band-limited functions"
    - Non-bandlimited signals
    - Error analysis for approximate methods
    - **USE FOR:** Handling non-ideal audio (drift, noise)

### FPGA Elementary Function Implementation

17. **DeDinechin2007** - "Assisted verification of elementary functions"
    - Domain reduction for verified implementations
    - Gappa tool for correctness
    - **USE FOR:** Verified/correct implementation of τ(x)

18. **Lee2006** - "A hardware Gaussian noise generator"
    - Domain reduction for transcendental functions on FPGAs
    - Box-Muller method error analysis
    - **USE FOR:** FPGA transcendental function techniques

### Interpolation & Reconstruction Algorithms

19. **Ferreira1994** - "Noniterative and fast iterative methods for interpolation"
    - Efficient bandlimited interpolation
    - Fast reconstruction from samples
    - **USE FOR:** Runtime sinc interpolation implementation

---

## Citation Strategy by Chapter Section

### Chapter 3, Section 4.4: Shannon Wavelet Basis

**Introduction to Shannon wavelets:**
- Cite: Daubechies1992, Mallat1989, Walter1992Shannon

**Bandlimited property (NEW subsection):**
- Cite: PaleyWiener1934, Rudin1987, Unser2000

**Periodic component compression (NEW subsection):**
- Cite: Katznelson2004 (periodicity theory)
- Cite: Muller2006 (domain reduction)
- Cite: Meher2008 (CORDIC example)
- Forward reference to Chapter 5 arccos example

**Multi-band optimization:**
- Cite: Benedetto1997 (multi-band signals)
- Cite: Aldroubi1995 (harmonic structure → sampling reduction)

### Chapter 4: Cyclostationary Analysis

**Connecting cyclostationarity to harmonic structure:**
- Cite: Katznelson2004 (commensurable periods → lcm period)
- Cite: Benedetto1997 (wavelet decomposition of cyclostationary)
- **Novel contribution:** explicit connection to compressibility!

**Quasi-periodic extension:**
- Cite: Janssen1988 (Zak transform)
- Cite: Butzer1983 (approximate sampling)

### Chapter 5: Architectural Implementation

**arccos example (existing):**
- Cite: Muller2006 (Chapter 4, argument reduction)
- Cite: DeDinechin2007 (verification)
- Cite: Lee2006 (FPGA implementation)

**General procedure (Section 5.1):**
- Cite: Unser2000 (sampling theory foundation)
- Cite: Walter1992Shannon (wavelet sampling)
- Cite: Ferreira1994 (efficient interpolation)
- Cite: Detrey2007 (FPGA table-based methods)

**Synthesis algorithm:**
- Cite: Mallat1989 (fast wavelet transform)
- Cite: Ferreira1994 (sinc interpolation)

---

## Strategic Use of Citations

### When to cite what:

**For theoretical foundations:**
→ PaleyWiener1934, Rudin1987, Katznelson2004

**For wavelet-specific theory:**
→ Daubechies1992, Mallat1989, Walter1992Shannon, Unser2000

**For FPGA implementation:**
→ Muller2006, Meher2008, Detrey2007, Lee2006

**For algorithm correctness:**
→ DeDinechin2007, Ferreira1994

**For extensions/robustness:**
→ Janssen1988, Butzer1983, Aldroubi1995

---

## Most Critical Citations (Top 5)

If you had to choose only 5 new citations for maximum impact:

1. **Unser2000** - Shannon wavelet sampling (comprehensive, IEEE, highly cited)
2. **Muller2006** - Elementary function domain reduction (definitive reference)
3. **Katznelson2004** - Harmonic analysis (connects cyclostationarity to periodicity)
4. **PaleyWiener1934** - Bandlimited reconstruction (foundational theorem)
5. **Detrey2007** - FPGA table-based methods (direct application domain)

These 5 provide:
- Theoretical foundation (Paley-Wiener, Katznelson)
- Wavelet framework (Unser)
- Implementation techniques (Muller, Detrey)
- FPGA context (Detrey)

---

## How to Integrate into Your Writing

### Template: Introducing Fundamental Domain Compression

```latex
The Paley-Wiener theorem \cite{PaleyWiener1934} establishes that
bandlimited functions are entire functions of exponential type,
implying that the complete function is determined by its values
on any bounded interval. For periodic bandlimited signals in a
Shannon wavelet subspace \cite{Walter1992Shannon,Unser2000}, this
property enables reconstruction from a fundamental domain.

Classical implementations exploit this for elementary functions
\cite{Muller2006,Meher2008}: for instance, $\sin(x)$ with period
$2\pi$ and even symmetry can be stored using only the quarter-domain
$[0, \pi/4]$, achieving $4\times$ memory reduction. Modern FPGA
implementations \cite{Detrey2007} demonstrate that the computational
cost of the recovery transformation $\tau(x)$ is typically negligible
compared to the memory savings.

We generalize this approach to arbitrary harmonic signals decomposed
via the Shannon wavelet basis. For a signal $f(t)$ with harmonic
components satisfying commensurability (periods related by rational
ratios, as shown in harmonic analysis \cite{Katznelson2004}), each
wavelet scale $j$ contributes a bandlimited periodic component.
These components can be compressed via fundamental domain storage,
with independent bit allocation per band (Section 4.1).
```

This gives you:
- Theoretical foundation (Paley-Wiener)
- Wavelet connection (Walter, Unser)
- Practical precedent (Muller, Meher, Detrey)
- Extension to your framework (Katznelson)
- Forward reference to your optimization

Perfect academic grounding!

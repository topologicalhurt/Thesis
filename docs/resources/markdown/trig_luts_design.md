# Designing trig lut's


$$

$$

## Optimising W.R.T frequency

$$
\frac{d}{d X} \frac{\sin{\left(X \right)}}{X}=\frac{\cos{\left(X \right)}}{X} - \frac{\sin{\left(X \right)}}{X^{2}}=\frac{\cos{\left(X \right)} - \mathop{\text{sinc}}{\left(X \right)}}{X}\newline

\implies X\mathcal{E}(X) = \cos{\left(X \right)} - \mathop{\text{sinc}}{\left(X \right)}\implies \cos(X) - X\mathcal{E}(X) = \mathop{\text{sinc}}{\left(X \right)}
$$

## Optimising W.R.T phase

$$
\newline

\mathcal{O}_{\theta}(X) = \frac{N i^{k} x^{k - 1}}{\Gamma\left(k + 1\right)}
$$

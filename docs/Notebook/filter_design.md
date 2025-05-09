# Designing the filter function
## Basic representation of transfer function (part I)

$$
 \newline Z =  i m_{1,i+1}^{T} m_{2,i+1} + m_{1,i}^{T} m_{2,i}  =  \left[\begin{matrix}m_{1,i}^{T} m_{2,i}\\m_{1,i+1}^{T} m_{2,i+1}\end{matrix}\right] \left[\begin{matrix}1\\1.0 i\end{matrix}\right] \newline \text{An original proposal was the following: } \mathcal{H_{old}}(Z) =  - \log{\left(\left|{\left(Z^{4} + 4\right) \mathop{\text{atanh}}{\left(Z^{2} \right)}}\right| \right)} \newline \mathcal{h}(Z) =  \mathop{\text{atanh}}{\left(\frac{Z^{4}}{\rho} \right)} \newline \mathcal{H}(Z) =  \frac{h{\left(Z,1 \right)} \mathop{\text{sgn}}{\left(Z \right)}}{Z^{4} + 1} \newline \mathcal{H_g}(Z, \rho) =  \lim_{\epsilon \to 0} \frac{\left(1 - e^{- \frac{\left(\left|{Z}\right| - 1\right)^{2}}{\epsilon^{2}}}\right) h{\left(Z,\rho \right)} \mathop{\text{sgn}}{\left(Z \right)}}{Z^{4} + 1} \text{Where the system becomes non-causal for any $\rho \geq 1$}
$$

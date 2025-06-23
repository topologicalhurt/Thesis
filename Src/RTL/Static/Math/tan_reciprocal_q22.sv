`include "Src/RTL/Static/Cores/sincos_poly_q22_dp.sv"

module tan_reciprocal_q22
(
    input  logic         clk2x,      // 2× clock, phase‑aligned
    input  logic [23:0]  theta_in,   // Q2.22
    output logic [23:0]  tan_out,    // Q1.23
);
    logic [23:0] num;
    logic [23:0] denom;

    sincos_poly_q22_dp sincosU (
        .clk2x (clk2x),
        .theta_in (theta_in),
        .sin_out (num),
        .cos_out (denom)
    );

    tan_out <= num / denom; // TODO: replace with xilinx ip divider
endmodule

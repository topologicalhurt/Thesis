// ------------------------------------------------------------------------
// Filename:       tan_reciprocal_q22.sv
//
// Project:        LLAC, intelligent hardware scheduler targeting common
// audio signal chains.
//
// For more information see the repository:
// https://github.com/topologicalhurt/Thesis
//
// Purpose:        N/A
//
// Author: topologicalhurt csin0659@uni.sydney.edu.au
//
// ------------------------------------------------------------------------
// Copyright (C) 2025, LLAC project LLC
//
// This file is a part of the RTL module
// It is intended to be used as part of the Math design where a README.md
// detailing the design should exist, conforming to the details provided
// under docs/CONTRIBUTING.md. The Math module is covered by the GPL 3.0
// License (see below.)
//
// The design is NOT COVERED UNDER ANY WARRANTY.
//
// LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
// As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html
//
// A copy of this license is included at the root directory. It should've
// been provided to you
// Otherwise please consult:
// https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
// ------------------------------------------------------------------------


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

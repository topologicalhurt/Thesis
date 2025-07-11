// ------------------------------------------------------------------------
// Filename:       sincos_poly_q22_dp.sv
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


`include "Src/RTL/Static/Cores/sin_poly_q22.sv"

module sincos_poly_q22_dp
#(parameter LAT = 8)                 // pipeline depth in clk2x cycles
(
    input  logic         clk2x,      // 2× clock, phase‑aligned
    input  logic [23:0]  theta_in,   // Q2.22
    output logic [23:0]  sin_out,    // Q1.23
    output logic [23:0]  cos_out     // Q1.23
);
    import math::angle_shift_q22;

    /* ---------- time‑multiplex driver + de‑interleave + latency align ------------------------- */
    logic [23:0] poly_in_fast; // Changes from theta to theta + pi/2 on clk2x
    logic toggle_fast = 1'b1;

    always_comb begin
        logic [23:0] theta_cos = angle_shift_q22(theta_in);
    end

    logic [LAT-1:0] tag_sr; // Shift‑register for “toggle”

    always_ff @(posedge clk2x) begin
        toggle_fast <= ~toggle_fast;
        poly_in_fast <= toggle_fast ? theta_cos : theta_in;
        tag_sr <= {tag_sr[LAT-2:0], toggle_fast};
    end

    /* ---------- single polynomial pipeline -------------------- */
    logic [23:0] poly_out_fast;

    sin_poly_q22 sinU (
        .theta_in (poly_in_fast),
        .sine_out (poly_out_fast)
    );

    // when tag_sr[0]==0 output belongs to sin. When 1 it is cosine
    always_ff @(posedge clk2x) begin
        if (tag_sr[0]==1'b0)
            sin_out <= poly_out_fast;
        else
            cos_out <= poly_out_fast;
    end

    // sin_out, cos_out now update on *clk2x*
endmodule

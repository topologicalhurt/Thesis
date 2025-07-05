// ------------------------------------------------------------------------
// Filename:       cos_poly_q22.sv
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


`include "Src/RTL/Static/Cores/consts.svh"


module cos_poly_q22 (
    input  logic [23:0] theta_in,  // 24-bit input angle, Q2.22 format (0 to 2π)
    output logic [23:0] cos_out    // 24-bit output cosine, Q1.23 format (signed)
);
    import math::angle_shift_q22;

    logic [24:0] add_tmp;      // 1 extra bit for carry
    logic [23:0] theta_shift;  // wrapped angle for sine core

    always_comb begin
        theta_shift = angle_shift_q22(theta);
    end

    sin_poly_q22 sin_core (
        .theta_in (theta_shift),
        .sine_out (cos_out)    // cos θ = sin(θ+π/2)
    );
endmodule

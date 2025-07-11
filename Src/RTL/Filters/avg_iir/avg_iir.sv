// ------------------------------------------------------------------------
// Filename:       avg_iir.sv
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
// It is intended to be used as part of the avg_iir design where a
// README.md detailing the design should exist, conforming to the details
// provided
// under docs/CONTRIBUTING.md. The avg_iir module is covered by the GPL 3.0
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

/* Useful readings:

    http://dx.doi.org/10.1063/1.1138645
    https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=7746188
    https://zipcpu.com/dsp/2017/08/19/simple-filter.html

*/


`include "avg_iir.svh"


module avg_iir #(
) (
    input wire i_clk
);

endmodule

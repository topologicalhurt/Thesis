// ------------------------------------------------------------------------
// Filename:       dsd.sv
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
// It is intended to be used as part of the In design where a README.md
// detailing the design should exist, conforming to the details provided
// under docs/CONTRIBUTING.md. The In module is covered by the GPL 3.0
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

/*  Whilst this design makes legal modification of, & avoids directly copying from:

    Dan Gisselquist, Ph.D
    Gisselquist Technology, LLC

    https://zipcpu.com/dsp/2020/07/28/down-sampler.html
    https://github.com/ZipCPU/dspfilters/blob/629474e69c68343ec04e93e4df69f4738c0971c8/rtl/subfildown.v

    It would still like to give direct credit to his work, without which the implementation
    of this design would've been significantly complicated.
*/


`include "dsd.svh"


module dsd #(
    parameter   AUDIO_WIDTH = 24,
    localparam	LGN_COEFFS=$clog2(NCOEFFS),

    parameter [0:0]	FIXED_COEFFS = 1'b0
) (
    input wire i_clk
);
	reg	[(COEFF_W-1):0]	    cmem	[0:((1<<LGN_COEFFS)-1)];
	reg	[(AUDIO_WIDTH-1):0]	dmem	[0:((1<<LGN_COEFFS)-1)];

    generate if (FIXED_COEFFS || INITIAL_COEFFS != 0)
    begin : LOAD_INITIAL_COEFFS

        initial $readmemh(INITIAL_COEFFS, cmem);

    end endgenerate

endmodule

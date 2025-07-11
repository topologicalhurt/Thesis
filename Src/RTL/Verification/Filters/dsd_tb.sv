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


module dsd_tb;

    parameter SYS_CLK_PERIOD = 10;      // I.e. 10 = 100 MHz system clock

    // Clock generation
    reg clk;

    // Instantiate the DUT (Device Under Test)
    dsd #(
        .IN_WIDTH(24),
        .FIXED_COEFFS(1'b0)
    ) dut (
        .i_clk(clk)
    );

    // System clock generation
    initial begin
        clk = 0;
        forever #(SYS_CLK_PERIOD/2) clk = ~clk;
    end

    // Test sequence
    initial begin
        $display("Starting DSD testbench");

        // Wait for a few clock cycles
        repeat (10) @(posedge clk);

        $display("DSD testbench completed successfully");
        $finish;
    end

endmodule

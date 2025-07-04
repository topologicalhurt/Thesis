// ------------------------------------------------------------------------
// Filename:       CIC_decimator.sv
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
// It is intended to be used as part of the downsampler design where a
// README.md detailing the design should exist, conforming to the details
// provided
// under docs/CONTRIBUTING.md. The downsampler module is covered by the GPL
// 3.0 License (see below.)
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

    https://tomverbeure.github.io/2020/09/30/Moving-Average-and-CIC-Filters.html
    https://www.dsprelated.com/showarticle/1337.php

*/

// TODO's:
// (1) Verify formally
// (2) Investigate https://ieeexplore.ieee.org/document/1163535 (Hogenauer) for choosing ideal delay lengths
// this will help reduce FF usage


`include "CIC_lp.svh"


module CIC_lp #(
    parameter integer N_STAGES = `N_STAGES,
    parameter integer DECIMATION_RATE = `DECIMATION_RATE,
    parameter integer COMB_DELAY = `COMB_DELAY,
    parameter integer IN_WIDTH = `AUDIO_IN,
    parameter integer BIT_GROWTH = `BIT_GROWTH,
    parameter integer INTEGRATOR_WIDTH = `INTEGRATOR_WIDTH
) (
    input wire i_clk,
    input wire rst_n,

    input wire signed [IN_WIDTH-1:0] data_in,
    output wire signed [IN_WIDTH-1:0] data_out,

    input wire in_valid,
    output wire out_valid
);

    // Integrator (interchangeable in order with comb)
    reg signed [INTEGRATOR_WIDTH-1:0] integrator_regs [N_STAGES-1:0];
    wire signed [INTEGRATOR_WIDTH-1:0] integrator_outputs [N_STAGES-1:0];
    genvar i;
    generate
        for (i = 0; i < N_STAGES; i = i + 1) begin : integrator_stage
            /*
            The integrator section consists of N_STAGES of cascaded accumulators.
            The first stage accumulates the input data:
              y1[n] = y1[n-1] + x[n]
            Each subsequent stage accumulates the output of the previous stage:
              yi[n] = yi[n-1] + y(i-1)[n]
            */
            if (i == 0) begin
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        integrator_regs[i] <= 0;
                    end else if (in_valid) begin
                        integrator_regs[i] <= integrator_regs[i] + data_in;
                    end
                end
                assign integrator_outputs[i] = integrator_regs[i];
            end else begin
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        integrator_regs[i] <= 0;
                    end else if (in_valid) begin
                        integrator_regs[i] <= integrator_regs[i] + integrator_outputs[i-1];
                    end
                end
                assign integrator_outputs[i] = integrator_regs[i];
            end
        end
    endgenerate

    /* The downsampler reduces the sample rate by a factor of DECIMATION_RATE.
    It generates a sample_enable signal that is asserted for one clock cycle
    every DECIMATION_RATE input samples. This signal is used to clock the
    comb section of the filter. */
    reg [$clog2(DECIMATION_RATE)-1:0] sample_count;
    wire sample_enable;
    always @(posedge i_clk) begin
        if (!rst_n) begin
            sample_count <= 0;
        end else if (in_valid) begin
            // every DECIMATION_RATE input samples. This signal is used to clock the comb section of the filter.
            if (sample_count == DECIMATION_RATE - 1) begin
                sample_count <= 0;
            end else begin
                sample_count <= sample_count + 1;
            end
        end
    end

    assign sample_enable = (sample_count == DECIMATION_RATE - 1) && in_valid;

    // Comb
    reg signed [INTEGRATOR_WIDTH-1:0] comb_inputs_d [N_STAGES-1:0];
    reg signed [INTEGRATOR_WIDTH-1:0] comb_outputs_d [N_STAGES-1:0];
    wire signed [INTEGRATOR_WIDTH-1:0] comb_outputs [N_STAGES-1:0];
    generate
        for (i = 0; i < N_STAGES; i = i + 1) begin : comb_stage
            /*
            The comb section consists of N_STAGES of cascaded differentiators.
            The first comb stage operates on the downsampled output of the final
            integrator stage. The equation for each comb stage is:
              yi[n] = y(i-1)[n] - y(i-1)[n-M]
            where M is the comb delay (usually 1 or 2).
            */
            if (i == 0) begin
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        comb_inputs_d[i] <= 0;
                    end else if (sample_enable) begin
                        comb_inputs_d[i] <= integrator_outputs[N_STAGES-1];
                    end
                end
                assign comb_outputs[i] = comb_inputs_d[i] - comb_outputs_d[i];
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        comb_outputs_d[i] <= 0;
                    end else if (sample_enable) begin
                        comb_outputs_d[i] <= comb_inputs_d[i];
                    end
                end
            end else begin
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        comb_inputs_d[i] <= 0;
                    end else if (sample_enable) begin
                        comb_inputs_d[i] <= comb_outputs[i-1];
                    end
                end
                assign comb_outputs[i] = comb_inputs_d[i] - comb_outputs_d[i];
                always @(posedge i_clk) begin
                    if (!rst_n) begin
                        comb_outputs_d[i] <= 0;
                    end else if (sample_enable) begin
                        comb_outputs_d[i] <= comb_inputs_d[i];
                    end
                end
            end
        end
    endgenerate

    // Output logic
    assign data_out = comb_outputs[N_STAGES-1] >>> BIT_GROWTH;
    assign out_valid = sample_enable;

endmodule

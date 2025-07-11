// ------------------------------------------------------------------------
// Filename:       sinc_euler_q22.sv
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

`include "Common/bit_growth.svh"
`include "consts.svh"
`include "sinc_euler_q22.svh"

/*
    Useful readings:

    https://www.sciencedirect.com/science/article/pii/S0096300315001046

    This module implements the formula:
    sinc(x) = (1/K) * sum_{n=1 to K} cos( ((n - 0.5) * x) / K )
    where K = 2^`N_STAGES.

    The design is free-running and heavily pipelined to maximize clock frequency.
    A new result is produced every K clock cycles.
*/

module sinc #(
    parameter integer K = 2**`N_STAGES,
    parameter integer IN_WIDTH = `AUDIO_WIDTH,

    parameter integer SUM_WIDTH = `ADD_GROWTH_N(IN_WIDTH, K)    // The accumulator must be wide enough to hold the sum of K cosine values without overflow.
) (
    input wire i_clk,
    input wire i_rst_n,
    input logic signed [IN_WIDTH-1:0] i_theta,  // Input angle x, in Q2.22 fixed-point format

    output logic signed [IN_WIDTH-1:0] o_sinc  // Final result, in Q2.22 fixed-point format
);

    // Formula Variables & Pipeline Registers
    logic [K_WIDTH-1:0] counter; // Tracks which `n` we are processing, from 1 to K.
    logic signed [`N_STAGES+1:0] x_coeff; // Represents (2n-1) to implement the (n-0.5) term.
    logic signed [SUM_WIDTH-1:0] cos_sum; // Accumulator for the summation.
    logic signed [IN_WIDTH-1:0] sinc_out_reg; // Registered output.

    // Pipeline stage 1 register: Holds the result of the multiplication.
    logic signed [`MULT_GROWTH_SIGNED(IN_WIDTH, $bits(x_coeff))-1:0] mult_out_s1_reg;

    // Pipeline stage 2 register: Holds the output of the cosine module.
    logic signed [IN_WIDTH-1:0] cos_out_s2_reg;

    /* Datapath Logic (Combinational)
    This logic calculates the argument for the cosine function.
    It is the first stage of the 2-stage pipeline.
    */
    logic signed [`MULT_GROWTH_SIGNED(IN_WIDTH, $bits(x_coeff))-1:0] mult_out_s1;
    /*
        alpha = (n - 0.5) * x / K
        (n - 0.5) is implemented as (2n-1)/2 = x_coeff/2.
        alpha = (x_coeff / 2) * (i_theta / K)
              = (x_coeff * i_theta) / (2 * K)

        Q-Format Math:
        - i_theta: Q2.22
        - x_coeff: Integer (signed)
        - Product (mult_out_s1): Q(2+$bits(x_coeff)-1).22. The binary point doesn't move.
    */
    assign mult_out_s1 = i_theta * x_coeff;

    // This is the second stage of the pipeline.
    logic signed [IN_WIDTH-1:0] cos_arg_s2;
    logic signed [IN_WIDTH-1:0] cos_out_s2;
    /*
        To get alpha, we scale the product by 1 / (2*K).
        K = 2^`N_STAGES, so 2*K = 2^(`N_STAGES`+1).
        This is a right shift by (`N_STAGES` + 1).

        Q-Format Math:
        - The shift scales the Q-format number, maintaining the Q2.22 format for the cosine module.
    */
    assign cos_arg_s2 = mult_out_s1_reg >>> (`N_STAGES` + 1);

    // Instantiate the cosine module.
    cos_poly_q22 cos_inst (
        .i_theta(cos_arg_s2),
        .o_cos(cos_out_s2)
    );

    // Control and Accumulation Logic (Sequential)
    always_ff @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            // Reset all state
            counter <= 0;
            x_coeff <= 1; // Start with coeff for n=1
            cos_sum <= 0;
            mult_out_s1_reg <= 0;
            cos_out_s2_reg <= 0;
            sinc_out_reg <= 0;
        end else begin
            // Pipeline Stage 1: Multiplication
            // Continuously calculate the product for the current `x_coeff`.
            mult_out_s1_reg <= mult_out_s1;

            // Pipeline Stage 2: Cosine Calculation
            // The cosine module's output is registered.
            cos_out_s2_reg <= cos_out_s2;

            // Stage 3: Accumulation and Control
            if (counter == K) begin
                // The final term (for n=K) has just been calculated in stage 2.
                // Add it to the sum and finalize the result.
                logic signed [SUM_WIDTH-1:0] final_sum = cos_sum + cos_out_s2_reg;

                // Final scaling: sum / K. A right shift by `N_STAGES`.
                sinc_out_reg <= final_sum >>> `N_STAGES;

                // Reset for the next calculation frame.
                counter <= 1;
                x_coeff <= 1;
                cos_sum <= 0;

            end else begin
                // For the first two cycles, the pipeline is filling, so we don't accumulate.
                if (counter > 0) begin
                    // Add the fully-pipelined cosine result to the sum.
                    cos_sum <= cos_sum + cos_out_s2_reg;
                end

                counter <= counter + 1;
                x_coeff <= x_coeff + 2; // Next odd number for (2n-1)
            end
        end
    end

    assign o_sinc = sinc_out_reg;

endmodule

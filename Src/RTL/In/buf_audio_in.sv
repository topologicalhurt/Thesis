// ------------------------------------------------------------------------
// Filename:       buf_audio_in.sv
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


`include "buf_audio_in.svh"
`include "Common/pos_edge_det.sv"

// TODO's:
// (1): build debug wrapper
// (2): ensure bram is accessed legally
// (3): make / ensure synthesizable
// (4): technically this is TDM not I2S so refactor / rename to reflect that


module buf_audio_in #(
    parameter I2S_WIDTH          = 24,
    parameter AUDIO_WIDTH        = 24,
    parameter NUM_AUDIO_CHANNELS = 8
) (
    input  wire                        sys_clk,          // System clock
    input  wire                        sys_rst,          // System reset (active high)

    // I2S Interface (codec is master)
    input  wire                        i2s_bclk,         // Bit clock
    input  wire                        i2s_lrclk,        // Word-select
    input  wire                        i2s_data,         // Serial data in

    // Consumer handshake
    input   wire                       adv_read_req,     // Request by consumer to advance read_ptr
    output  wire                       adv_read_enable,  // Advance read_ptr

    // Parallel audio outputs
    output logic [AUDIO_WIDTH-1:0]     audio_channel_out [(NUM_AUDIO_CHANNELS * STEREO_MULTIPLIER)-1:0],
    output wire                        sample_valid,     // One-cycle pulse when new samples accepted
    output logic                       buffer_ready,     // All channels hold at least one sample
    output logic                       buffer_full       // Any channel FIFO full
);
    //================================================================
    // I²S RECEIVE (i2s_bclk clock domain)
    //================================================================
    logic [I2S_WIDTH-1:0] shift_reg;
    logic [I2S_WIDTH-1:0] sample_latched_i2s;
    logic                 i2s_lrclk_d;
    logic                 sample_ready_i2s;
    logic                 captured_lrclk_i2s;

    always_ff @(posedge i2s_bclk or posedge sys_rst) begin
        if (sys_rst) begin
            shift_reg          <= '0;
            sample_latched_i2s <= '0;
            captured_lrclk_i2s <= 1'b0;
            i2s_lrclk_d        <= 1'b0;
            sample_ready_i2s   <= 1'b0;
        end else begin
            sample_ready_i2s   <= 1'b0;
            shift_reg <= {shift_reg[I2S_WIDTH-2:0], i2s_data};
            i2s_lrclk_d <= i2s_lrclk;

            // Check for word completion every I2S_WIDTH bits
            if (i2s_lrclk != i2s_lrclk_d) begin
                // $display("--> DUT @ %0t [I2S DOMAIN]: LRCLK edge detected. Pulsing sample_ready_i2s.", $time);
                sample_latched_i2s <= {shift_reg[I2S_WIDTH-2:0], i2s_data};        // Latch the completed word
                captured_lrclk_i2s <= i2s_lrclk_d;                                 // Latch current LRCLK for this word
                sample_ready_i2s   <= 1'b1;
            end
        end
    end

    //================================================================
    //  CDC & STAGING LOGIC (sys_clk domain)
    //================================================================
    // These registers hold flags that are pased with a 2-FF synchroniser
    logic                   sample_ready_sys_meta, sample_ready_sys;
    logic                   captured_lrclk_sys_meta, captured_lrclk_sys;

    // Synchronize the single-bit control signals from the i2s_bclk domain
    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            sample_ready_sys_meta   <= 1'b0;
            sample_ready_sys        <= 1'b0;
            captured_lrclk_sys_meta <= 1'b0;
            captured_lrclk_sys      <= 1'b0;
        end else begin
            sample_ready_sys_meta   <= sample_ready_i2s;
            sample_ready_sys        <= sample_ready_sys_meta;
            captured_lrclk_sys_meta <= captured_lrclk_i2s;
            captured_lrclk_sys      <= captured_lrclk_sys_meta;
        end
    end

    // Create a single-cycle 'valid' pulse from the synchronized 'ready' signal
    pos_edge_det sample_valid_detector (
        .sig(sample_ready_sys),
        .clk(sys_clk),
        .pe(sample_valid)
    );

    // Create a single-cycle 'read' pulse from the 'read' signal
    pos_edge_det read_detector (
        .sig(adv_read_req),
        .clk(sys_clk),
        .pe(adv_read_enable)
    );

    //================================================================
    // FIFO BUFFERS (sys_clk clock domain)
    //================================================================
    localparam PTR_W = $clog2(BUFFER_DEPTH); // Ptr width for FIFO depth
    localparam BUFFER_COUNT_WIDTH = PTR_W + 1;

    // Dimensions: [stereo_pair_index][L_or_R_index (0 or 1)][fifo_sample_index]
    logic [AUDIO_WIDTH-1:0] circ_buf     [NUM_AUDIO_CHANNELS-1:0][STEREO_MULTIPLIER-1:0][BUFFER_DEPTH-1:0];
    logic [PTR_W:0]         write_ptr    [NUM_AUDIO_CHANNELS-1:0][STEREO_MULTIPLIER-1:0];   // Extra MSB for full/empty
    logic [PTR_W:0]         read_ptr     [NUM_AUDIO_CHANNELS-1:0][STEREO_MULTIPLIER-1:0];   // Extra MSB
    logic [PTR_W:0]         buffer_count [NUM_AUDIO_CHANNELS-1:0][STEREO_MULTIPLIER-1:0];   // Count of samples in FIFO

    // Flags per MONO stream
    logic channel_full      [NUM_AUDIO_CHANNELS-1:0][STEREO_MULTIPLIER-1:0];

    genvar ch_pair_idx, lr_idx; // ch_pair_idx for stereo_pair, lr_idx for L/R
    generate
        for (ch_pair_idx = 0; ch_pair_idx < NUM_AUDIO_CHANNELS; ch_pair_idx++) begin : FIFO_PER_STEREO_PAIR

            logic stereo_pair_full;
            always_comb begin
                stereo_pair_full = 1'b0;
                for (int i = 0; i < STEREO_MULTIPLIER; i++) begin
                    stereo_pair_full |= (buffer_count[ch_pair_idx][i] >= BUFFER_COUNT_WIDTH'(BUFFER_DEPTH));
                end
            end

            for (lr_idx = 0; lr_idx < STEREO_MULTIPLIER; lr_idx++) begin : FIFO_PER_MONO_STREAM

                // This block defines behavior for one mono FIFO
                always_ff @(posedge sys_clk or posedge sys_rst) begin
                    if (sys_rst) begin
                        write_ptr[ch_pair_idx][lr_idx]    <= '0;
                        read_ptr[ch_pair_idx][lr_idx]     <= '0;
                        buffer_count[ch_pair_idx][lr_idx] <= '0;
                    end else begin

                        /* Write path:
                        A new sample arrives (sample_ready_sys is high for one cycle).
                        It belongs to the L/R channel indicated by captured_lrclk_sys.
                        This sample is written to ALL ch_pair_idx FIFOs for that specific L/R stream.
                        (This means the single I2S input is fanned out to NUM_AUDIO_CHANNELS stereo buffers).
                        */
                        if (sample_valid && (captured_lrclk_sys == lr_idx)) begin
                            // $display("--> DUT @ %0t [SYS DOMAIN]: sample_valid PULSE generated!", $time);
                            circ_buf[ch_pair_idx][lr_idx][write_ptr[ch_pair_idx][lr_idx][PTR_W-1:0]] <=
                            sample_latched_i2s[$bits(sample_latched_i2s)-1 -: AUDIO_WIDTH];

                            if (stereo_pair_full) begin
                                // Stereo pair overflow - advance read pointer first to drop oldest sample
                                read_ptr[ch_pair_idx][lr_idx] <= read_ptr[ch_pair_idx][lr_idx] + 1'b1;
                                write_ptr[ch_pair_idx][lr_idx] <= write_ptr[ch_pair_idx][lr_idx] + 1'b1;
                            end else begin
                                // Buffer not full - normal write
                                write_ptr[ch_pair_idx][lr_idx] <= write_ptr[ch_pair_idx][lr_idx] + 1'b1;
                                buffer_count[ch_pair_idx][lr_idx] <= buffer_count[ch_pair_idx][lr_idx] + 1'b1;
                            end
                        end

                        /* Read path:
                        If consumer wants to read (adv_read_enable) and FIFO is not empty
                        */
                        if (adv_read_enable && (buffer_count[ch_pair_idx][lr_idx] != '0)) begin
                            read_ptr[ch_pair_idx][lr_idx]     <= read_ptr[ch_pair_idx][lr_idx] + 1'b1;
                            buffer_count[ch_pair_idx][lr_idx] <= buffer_count[ch_pair_idx][lr_idx] - 1'b1;
                        end
                    end
                end
                // Combinational flags for this mono FIFO
                assign channel_full[ch_pair_idx][lr_idx] = stereo_pair_full;
            end
        end
    endgenerate

    // Continuous read-side data
    always_comb begin
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin     // i is ch_pair_idx
            for (int j = 0; j < STEREO_MULTIPLIER; j++) begin  // j is lr_idx (0 for L, 1 for R)
                // Output the sample at the current read pointer of the respective mono FIFO
                audio_channel_out[i * STEREO_MULTIPLIER + j] = circ_buf[i][j][read_ptr[i][j][PTR_W-1:0]];
            end
        end

        // buffer_ready: all mono channels have at least one sample
        buffer_ready = 1'b1; // Assume true, then AND with all non-empty flags
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            for (int j = 0; j < STEREO_MULTIPLIER; j++) begin
                buffer_ready &= (buffer_count[i][j] != '0);
            end
        end

        // buffer_full: any mono channel is full
        buffer_full = 1'b0; // Assume false, then OR with all full flags
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            for (int j = 0; j < STEREO_MULTIPLIER; j++) begin
                buffer_full |= channel_full[i][j];
            end
        end
    end

endmodule

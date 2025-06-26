// ------------------------------------------------------------------------
// Filename:       buf_audio_in_tb.sv
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


`include "buf_audio_in_tb.svh"
`include "buf_audio_in.svh"

module buf_audio_in_tb;
    // Clock periods
    localparam TB_SR         = 96;      // kHz sample rate
    parameter I2S_CLK_MULT   = 32;      // I2S clock multiplier
    parameter SYS_CLK_PERIOD = 10;      // I.e. 10 = 100 MHz system clock
    parameter I2S_CLK_PERIOD = $ceil(10**6 / (TB_SR * I2S_CLK_MULT));

    //================================================================
    // Driver variables
    //================================================================
    // DUT interface signals
    logic                adv_read_req;
    logic                adv_read_enable;
    logic                sys_clk;
    logic                sys_rst;
    logic                i2s_bclk;
    logic                i2s_lrclk; // 0 for Left, 1 for Right
    logic                i2s_data;

    // audio_channel_out size: TB_NUM_AUDIO_CHANNELS (stereo pairs) * STEREO_MULTIPLIER (2 for stereo)
    localparam TB_TOTAL_MONO_CHANNELS = TB_NUM_AUDIO_CHANNELS * STEREO_MULTIPLIER;
    logic [dut.AUDIO_WIDTH-1:0] audio_channel_out [TB_TOTAL_MONO_CHANNELS-1:0];

    logic                sample_valid;
    logic                buffer_ready;
    logic                buffer_full;

    //================================================================
    // Test variables
    //================================================================
    // Standard values to test receiver integrity (test 1)
    logic [dut.I2S_WIDTH-1:0] test_sample_left  = 24'h123456;
    logic [dut.I2S_WIDTH-1:0] test_sample_right = 24'hABCDEF;

    // Define the data patterns that will be used to fill the buffer (test 5)
    logic [dut.I2S_WIDTH-1:0] l_fill_val [BUFFER_DEPTH-1:0];
    logic [dut.I2S_WIDTH-1:0] r_fill_val [BUFFER_DEPTH-1:0];
    logic [dut.I2S_WIDTH-1:0] overflow_l  = 24'hBEEF01;
    logic [dut.I2S_WIDTH-1:0] overflow_r  = 24'hBEEF02;

    int sample_count;

    // NUM_AUDIO_CHANNELS parameter of DUT is number of stereo pairs
    buf_audio_in #(
        .NUM_AUDIO_CHANNELS(TB_NUM_AUDIO_CHANNELS)
    ) dut (
        .adv_read_req(adv_read_req),
        .adv_read_enable(adv_read_enable),
        .sys_clk(sys_clk),
        .sys_rst(sys_rst),
        .i2s_bclk(i2s_bclk),
        .i2s_lrclk(i2s_lrclk),
        .i2s_data(i2s_data),
        .audio_channel_out(audio_channel_out),
        .sample_valid(sample_valid),
        .buffer_ready(buffer_ready),
        .buffer_full(buffer_full)
    );

    // System clock generation
    initial begin
        sys_clk = 0;
        forever #(SYS_CLK_PERIOD/2) sys_clk = ~sys_clk;
    end

    // I2S bit clock generation
    initial begin
        i2s_bclk = 0;
        forever #(I2S_CLK_PERIOD/2) i2s_bclk = ~i2s_bclk;
    end

    /* I2S LR clock generation (word select)
    / LRCLK high for right channel, low for left channel. Each phase is I2S_WIDTH bclk cycles.
    / LRCLK period for I2S_WIDTH bits per channel (L/R), so I2S_WIDTH * 2 i2s_bclk cycles
    */
    initial begin
        logic [dut.I2S_WIDTH:0] tb_bclk_count = 0; // Counter for bclk cycles
        i2s_lrclk = 1'b0; // Start L
        @(posedge i2s_bclk);
        forever @(negedge i2s_bclk) begin
            tb_bclk_count++;
            if (tb_bclk_count == dut.I2S_WIDTH) begin
                i2s_lrclk = ~i2s_lrclk;
                tb_bclk_count = 0;
            end
        end
    end

    // Send a sample 'word' over I2S data line, MSB first
    task automatic send_word(input logic [dut.I2S_WIDTH-1:0] word);
        for (int b = dut.I2S_WIDTH-1; b >= 0; b--) begin
            // Data is sampled by receiver on rising edge of i2s_bclk
            @(negedge i2s_bclk); // Change data on falling edge
            i2s_data = word[b];
        end
    endtask

    // Send a stereo I2S sample (Left then Right)
    task automatic send_i2s_stereo_sample(input logic [dut.I2S_WIDTH-1:0] left_word, input logic [dut.I2S_WIDTH-1:0] right_word);

        // Wait for i2s_lrclk to be low (Left channel active)
        wait (i2s_lrclk == 1'b0); // Transition to Left channel phase

        $display("Time %0t: Sending Left sample 0x%h (i2s_lrclk=%b)", $time, left_word, i2s_lrclk);
        send_word(left_word);

        // Wait for i2s_lrclk to be high (Right channel active)
        wait (i2s_lrclk == 1'b1); // Transition to Right channel phase

        $display("Time %0t: Sending Right sample 0x%h (i2s_lrclk=%b)", $time, right_word, i2s_lrclk);
        send_word(right_word);

        @(negedge i2s_bclk)
        i2s_data = 1'b0; // Stop sending after the sample is complete

        @(posedge dut.sample_valid);

        $display("TB @ %0t: Detected 1st pulse. Waiting for 2nd 'sample_valid' pulse (for Right word)...", $time);
        @(posedge dut.sample_valid);

        sample_count += 2;

        $display("Time %0t: Sent I2S stereo sample: L=0x%h, R=0x%h", $time, left_word, right_word);
    endtask

    /* Task to check audio outputs for a specific mono channel
    base_pair_idx: index of the stereo pair (0 to TB_NUM_AUDIO_CHANNELS-1)
    lr_sel: 0 for Left, 1 for Right
    */
    task automatic check_and_pop_stereo_pair(
        input [dut.AUDIO_WIDTH-1:0] expected_left,
        input [dut.AUDIO_WIDTH-1:0] expected_right,
        input int base_pair_idx
    );

        typedef logic[$clog2(TB_TOTAL_MONO_CHANNELS)-1:0] index_t;
        logic [dut.AUDIO_WIDTH-1:0] actual_left, actual_right;
        index_t left_idx  = index_t'(base_pair_idx * STEREO_MULTIPLIER);
        index_t right_idx = index_t'(base_pair_idx * STEREO_MULTIPLIER + 1);

        @(posedge sys_clk);

        // Sample BOTH outputs before the pop command.
        actual_left = audio_channel_out[left_idx];
        actual_right = audio_channel_out[right_idx];

        `READ_ONCE

        $display("ACTUAL VALUES: %h, %h", actual_left, actual_right);

        // Now check the values that were sampled.
        if (actual_left !== expected_left) begin
            $error("Time %0t: LEFT channel mismatch! Pair %0d. Expected: 0x%h, Got: 0x%h",
                   $time, base_pair_idx, expected_left, actual_left);
        end else begin
            $display("Time %0t: LEFT channel output correct. Pair %0d: 0x%h",
                     $time, base_pair_idx, actual_left);
        end

        if (actual_right !== expected_right) begin
            $error("Time %0t: RIGHT channel mismatch! Pair %0d. Expected: 0x%h, Got: 0x%h",
                   $time, base_pair_idx, expected_right, actual_right);
        end else begin
            $display("Time %0t: RIGHT channel output correct. Pair %0d: 0x%h",
                     $time, base_pair_idx, actual_right);
        end

        // Pulse the global read enable to pop all FIFOs by one sample.
        `READ_ONCE
    endtask

    // Test 1: Send one full stereo sample
    task automatic test1_send_single_pair();
        $display("\n=== Test 1: Send One Stereo Sample ===");

        send_i2s_stereo_sample(test_sample_left, test_sample_right);

        /* Check outputs after enabling read
        We expect to read L then R for each stereo pair buffer
        */
        check_and_pop_stereo_pair(test_sample_left, test_sample_right, 0);
        $display("Test 1 completed successfully!");
    endtask

    // Test 2: test that the reset cycle works after sending a stereo sample
    // IMPORTANT: We do NOT check the value of audio_channel_out
    // (The physical RAM contents are indeterminate after a reset.)
    task automatic test2_reset_cycle();
        $display("\n=== Test 2: Reset During Operation ===");
        $display("Time %0t: Applying reset...", $time);
        `RESET_CYCLE

        // Verify all control logic has been cleared to 0.
        for (int p_idx = 0; p_idx < TB_NUM_AUDIO_CHANNELS; p_idx++) begin
            for (int lr_idx = 0; lr_idx < STEREO_MULTIPLIER; lr_idx++) begin
                if (dut.write_ptr[p_idx][lr_idx] !== '0) begin
                    $error("Time %0t: write_ptr[%0d][%0d] not cleared after reset. Got: %h",
                           $time, p_idx, lr_idx, dut.write_ptr[p_idx][lr_idx]);
                end
                if (dut.read_ptr[p_idx][lr_idx] !== '0) begin
                    $error("Time %0t: read_ptr[%0d][%0d] not cleared after reset. Got: %h",
                           $time, p_idx, lr_idx, dut.read_ptr[p_idx][lr_idx]);
                end
                if (dut.buffer_count[p_idx][lr_idx] !== '0) begin
                    $error("Time %0t: buffer_count[%0d][%0d] not cleared after reset. Got: %h",
                           $time, p_idx, lr_idx, dut.buffer_count[p_idx][lr_idx]);
                end
            end
        end

        // Check that top-level status flags are in their correct reset state.
        if (dut.buffer_ready !== 1'b0) begin
            $error("Time %0t: buffer_ready signal was not cleared by reset.", $time);
        end
        if (dut.buffer_full !== 1'b0) begin
            $error("Time %0t: buffer_full signal was not cleared by reset.", $time);
        end

        $display("Test 2 completed successfully!");
    endtask

    // Test 3: test the buffer ready flag is set
    task automatic test3_buffer_ready_flag_set();
        $display("\n=== Test 3: Buffer Ready Verification ===");

        if (buffer_ready) $error("Buffer should not be ready after reset");
        send_i2s_stereo_sample(test_sample_left, test_sample_right); // Send one stereo sample
        if (!buffer_ready) begin
             $error("Time %0t: Buffer ready signal not asserted after sending one stereo sample!", $time);
        end else begin
             $display("Time %0t: Buffer ready signal asserted as expected.", $time);
        end
        $display("Test 3 completed successfully!");
    endtask

    // Task for Test 4: Multiple stereo samples buffering test
    task automatic test4_multiple_stereo_samples();
        $display("\n=== Test 4: Multiple Stereo Samples for Buffer Test (fills one stereo pair) ===");

        for (int i = 0; i < BUFFER_DEPTH >> 1; i++) begin // Fill up one L/R FIFO set
            logic [dut.I2S_WIDTH-1:0] l_val = dut.I2S_WIDTH'(24'h100000 + i);
            logic [dut.I2S_WIDTH-1:0] r_val = dut.I2S_WIDTH'(24'h200000 + i);
            send_i2s_stereo_sample(l_val, r_val);
        end

        /* At this point, buffer for pair 0, L and R should be full.
        Other pairs (if TB_NUM_AUDIO_CHANNELS > 1) will also be full due to fanout.
        */
        if (!buffer_full) begin
            $error("Time %0t: Buffer should be full!", $time);
        end else begin
            $display("Time %0t: Buffer full detected as expected.", $time);
        end

        $display("\n --- Reading back buffered stereo samples for pair 0 ---");
        // The test verifies that we can read back BUFFER_DEPTH samples from each channel
        for (int i = 0; i < BUFFER_DEPTH >> 1; i++) begin
            check_and_pop_stereo_pair(24'h100000 + 24'(i), 24'h200000 + 24'(i), 0);
        end
        $display("Test 4 completed successfully!");
    endtask

    // Test 5: Verify that a buffer overflow is handled by dropping the oldest sample.
    task automatic test5_check_buffer_overflow();
        int offset = 1 + (BUFFER_DEPTH >> 1);

        $display("\n=== Test 5: Buffer Overflow Test ===");

        // I.e. values that will 'wrap around' the buffer
        for (int i = 0; i < BUFFER_DEPTH >> 1; i++) begin
            l_fill_val[i] = dut.I2S_WIDTH'(24'h100000 + 24'(i + offset));
            r_fill_val[i] = dut.I2S_WIDTH'(24'h200000 + 24'(i + offset));
        end

        // Fill the buffer x2 (there is buffer_depth // 2 per mono channel in a stereo pair)

        // Storage for stereo pair is now full
        for (int i = 0; i < BUFFER_DEPTH >> 1; i++) begin
            send_i2s_stereo_sample(24'h100000 + 24'(i), 24'h200000 + 24'(i));
        end
        if (!buffer_full) $error("Time %0t: Buffer should be full after filling!", $time);

        // Now the storage for the stereo pair should wrap back around to the beginning
        for (int i = BUFFER_DEPTH >> 1; i < BUFFER_DEPTH; i++) begin
            send_i2s_stereo_sample(24'h100000 + 24'(i), 24'h200000 + 24'(i));
        end

        // Send one more stereo pair to cause another overflow in the last slot
        $display("Time %0t: Sending overflow sample...", $time);
        send_i2s_stereo_sample(overflow_l, overflow_r);

        // Verify the contents of the buffer after the overflow.
        // The original sample 0 should have been dropped and replaced by the overflow sample at the end.
        // We expect to read samples 1 through (BUFFER_DEPTH-1), followed by the overflow sample.
        $display("Time %0t: Reading back buffer contents to verify overflow...", $time);

        // Check samples that were NOT overwritten (from index 1 upwards)
        for (int i = 0; i < (BUFFER_DEPTH >> 1) - 1; i++) begin
            $display("0x%h, 0x%h, %d", l_fill_val[i], r_fill_val[i], BUFFER_DEPTH);
            check_and_pop_stereo_pair(l_fill_val[i], r_fill_val[i], 0);
        end

        // Check that the final samples we read are the overflow samples
        check_and_pop_stereo_pair(overflow_l, overflow_r, 0);

        $display("Test 5 completed successfully!");
    endtask

    // Main test sequence
    initial begin
        $display("=== Stereo Audio Buf In Testbench Started (NUM_AUDIO_CHANNELS=%0d stereo pairs) ===", TB_NUM_AUDIO_CHANNELS);

        // Initialize signals
        i2s_data = 1'b0;
        sample_count = 0; // Counts mono samples
        adv_read_req = 1'b0;

        `RESET_CYCLE
        test1_send_single_pair();

        test2_reset_cycle();

        `RESET_CYCLE
        test3_buffer_ready_flag_set();

        `RESET_CYCLE

        test4_multiple_stereo_samples();
        `RESET_CYCLE

        test5_check_buffer_overflow();
        `RESET_CYCLE

        // Final verification
        $display("\n=== Test Summary ===");
        $display("Total MONO samples sent: %0d", sample_count);
        $display("Test completed successfully!");

        $finish;
    end

    // To avoid "Signal flopped as both synchronous and async"
    logic monitor_sample_valid;
    logic monitor_buffer_ready;
    logic monitor_i2s_lrclk;
    logic monitor_i2s_data;
    logic monitor_adv_read_enable;

    /* verilator lint_off UNUSED */
    always_ff @(posedge sys_clk) begin
        monitor_buffer_ready <= buffer_ready;
        monitor_i2s_lrclk <= i2s_lrclk;
        monitor_i2s_data <= i2s_data;
        monitor_adv_read_enable <= adv_read_enable;
        monitor_sample_valid <= sample_valid;
    end

    logic [dut.I2S_WIDTH-1:0] monitor_shift_reg;
    logic [4:0] monitor_bit_counter; // Avaliable in debug only wrapper
    always_ff @(posedge i2s_bclk) begin
        monitor_shift_reg <= dut.shift_reg;
        // monitor_bit_counter <= dut.bit_counter;
    end
    /* verilator lint_on UNUSED */

    // Monitor signals
    initial begin
        $monitor("###MISC###\n\tTime %0t: sys_clk=%b, sys_rst=%b, i2s_bclk=%b, i2s_lrclk=%b, i2s_data=%b, adv_read=%b | s_valid=%b, b_ready=%b, b_full=%b",
                $time, sys_clk, sys_rst, i2s_bclk, monitor_i2s_lrclk, monitor_i2s_data, monitor_adv_read_enable,
                monitor_sample_valid, monitor_buffer_ready, buffer_full,
                "\n###DATA OUT###\n\tshift_reg=0x%h, L0_out=0x%h, R0_out=0x%h",
                monitor_shift_reg,
                (TB_TOTAL_MONO_CHANNELS > 0) ? audio_channel_out[0] : 'x,
                (TB_TOTAL_MONO_CHANNELS > 1) ? audio_channel_out[1] : 'x);
    end

    initial begin
        $dumpfile("buf_audio_in_stereo_tb.vcd");
        $dumpvars(0, buf_audio_in_tb);
    end

endmodule

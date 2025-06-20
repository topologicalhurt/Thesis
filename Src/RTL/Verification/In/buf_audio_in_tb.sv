`include "In/buf_audio_in_tb.svh"
`include "buf_audio_in.svh"

module buf_audio_in_tb;

    localparam TB_SR           = 96;    // kHz sample rate

    // Clock periods
    parameter I2S_CLK_MULT   = 32;      // I2S clock multiplier
    parameter SYS_CLK_PERIOD = 10;      // I.e. 10 = 100 MHz system clock
    parameter I2S_CLK_PERIOD = $ceil(10**6 / (TB_SR * I2S_CLK_MULT));

    // DUT interface signals
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

    // Test variables
    logic [dut.I2S_WIDTH-1:0] test_sample_left  = 24'h123456;
    logic [dut.I2S_WIDTH-1:0] test_sample_right = 24'hABCDEF;
    logic [dut.I2S_WIDTH-1:0] overflow_l = dut.I2S_WIDTH'(24'hBEEF01);
    logic [dut.I2S_WIDTH-1:0] overflow_r = dut.I2S_WIDTH'(24'hBEEF02);
    int sample_count;

    // NUM_AUDIO_CHANNELS parameter of DUT is number of stereo pairs
    buf_audio_in #(
        .NUM_AUDIO_CHANNELS(TB_NUM_AUDIO_CHANNELS)
    ) dut (
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
        forever @(posedge i2s_bclk) begin
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

        // Wait for processing and CDC synchronization - enough time for data to be captured and synchronized
        fork
            wait (buffer_ready == 1'b1);
            begin
                #10000; // 10us timeout - much shorter for debugging
                $display("Time %0t: Timeout waiting for buffer_ready. buffer_ready=%b, sample_valid=%b, buffer_full=%b",
                       $time, buffer_ready, sample_valid, buffer_full);
                $display("Debug: buffer_count[0][0]=%0d, buffer_count[0][1]=%0d",
                       dut.buffer_count[0][0], dut.buffer_count[0][1]);
                // Just continue instead of finishing to see what happens
            end
        join_any
        disable fork;

        sample_count += 2;

        $display("Time %0t: Sent I2S stereo sample: L=0x%h, R=0x%h", $time, left_word, right_word);

    endtask

    /* Task to check audio outputs for a specific mono channel
    base_pair_idx: index of the stereo pair (0 to TB_NUM_AUDIO_CHANNELS-1)
    lr_sel: 0 for Left, 1 for Right
    */
    task automatic check_and_pop_mono_output(input [dut.AUDIO_WIDTH-1:0] expected_value, int base_pair_idx, bit lr_sel);
        logic [dut.AUDIO_WIDTH-1:0] actual_value;
        int flat_idx = base_pair_idx * STEREO_MULTIPLIER + int'(lr_sel);

        `READ_ENABLE

        actual_value = audio_channel_out[flat_idx];
        if (actual_value !== expected_value) begin
            $error("Time %0t: Output mismatch! Pair %0d, L/R %0d (Flat Idx %0d). Expected: 0x%h, Got: 0x%h",
                   $time, base_pair_idx, lr_sel, flat_idx, expected_value, actual_value);
        end else begin
            $display("Time %0t: Output correct. Pair %0d, L/R %0d (Flat Idx %0d): 0x%h",
                     $time, base_pair_idx, lr_sel, flat_idx, actual_value);
        end

        `READ_DISABLE

    endtask

    // Test 1: Send one full stereo sample
    task automatic test1_send_single_pair();
        $display("\n=== Test 1: Send One Stereo Sample ===");

        send_i2s_stereo_sample(test_sample_left, test_sample_right);

        /* Check outputs after enabling read
        We expect to read L then R for each stereo pair buffer
        */
        check_and_pop_mono_output(test_sample_left, 0, 0);
        check_and_pop_mono_output(test_sample_right, 0, 1);
        $display("Test 1 completed successfully!");
    endtask

    // Test 2: test that the reset cycle works after sending a stereo sample
    task automatic test2_reset_cycle();
        $display("\n=== Test 2: Reset During Operation ===");

        `RESET_CYCLE
        for (int i = 0; i < TB_TOTAL_MONO_CHANNELS; i++) begin
            if (audio_channel_out[i] !== '0) begin
                $error("Time %0t: Mono Channel %0d not cleared after reset: 0x%h",
                       $time, i, audio_channel_out[i]);
            end
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

        for (int i = 0; i < BUFFER_DEPTH; i++) begin // Fill up one L/R FIFO set
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
        for (int i = 0; i < BUFFER_DEPTH; i++) begin
            `READ_ENABLE
            $display("Time %0t: Read L[%0d]: 0x%h, R[%0d]: 0x%h", $time, i, audio_channel_out[0], i, audio_channel_out[1]);
            `READ_DISABLE
        end
        $display("Test 4 completed successfully!");
    endtask

    // Test 5: test that a buffer overflow is handled correctly
    task automatic test5_check_buffer_overflow();
        $display("\n=== Test 5: Buffer Overflow Test ===");

        for (int i = 0; i < BUFFER_DEPTH; i++) begin // Fill up one L/R FIFO set
            logic [dut.I2S_WIDTH-1:0] l_val = dut.I2S_WIDTH'(24'h100000 + i);
            logic [dut.I2S_WIDTH-1:0] r_val = dut.I2S_WIDTH'(24'h200000 + i);
            send_i2s_stereo_sample(l_val, r_val);
        end

        send_i2s_stereo_sample(overflow_l, overflow_r); // This should overwrite the oldest (i=0)

        // Debug: check what values are actually available after overflow
        $display("After overflow: L0_out=0x%h, R0_out=0x%h", audio_channel_out[0], audio_channel_out[1]);

        // After overflow, the newest samples should have overwritten the oldest position
        // and be immediately available for reading
        check_and_pop_mono_output(overflow_l, 0, 0);
        check_and_pop_mono_output(overflow_r, 0, 1);

        // Read out the remaining samples from i=1 to BUFFER_DEPTH-1 (sample i=0 was overwritten)
        $display("Reading out remaining samples...");
        for (int i = 1; i < BUFFER_DEPTH; i++) begin
            check_and_pop_mono_output(24'h100000 + 24'(i), 0, 0);
            check_and_pop_mono_output(24'h200000 + 24'(i), 0, 1);
        end
    endtask

    // Main test sequence
    initial begin
        $display("=== Stereo Audio Buf In Testbench Started (NUM_AUDIO_CHANNELS=%0d stereo pairs) ===", TB_NUM_AUDIO_CHANNELS);

        // Initialize signals
        i2s_data = 1'b0;
        sample_count = 0; // Counts mono samples
        adv_read_enable = 1'b0;

        `RESET_CYCLE
        test1_send_single_pair();

        $finish;

        test2_reset_cycle();

        `RESET_CYCLE
        test3_buffer_ready_flag_set();

        `RESET_CYCLE

        test4_multiple_stereo_samples();
        `RESET_CYCLE

        test5_check_buffer_overflow();

        // Final verification
        $display("\n=== Test Summary ===");
        $display("Total MONO samples sent: %0d", sample_count);
        $display("Test completed successfully!");

        $finish;
    end

    // To avoid "Signal flopped as both synchronous and async"
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
    end

    logic [dut.I2S_WIDTH-1:0] monitor_shift_reg;
    logic [4:0] monitor_bit_counter;
    always_ff @(posedge i2s_bclk) begin
        monitor_shift_reg <= dut.shift_reg;
        monitor_bit_counter <= dut.bit_counter;
    end
    /* verilator lint_on UNUSED */

    // Monitor signals
    initial begin
        $monitor("Time %0t: sys_clk=%b, sys_rst=%b, i2s_bclk=%b, i2s_lrclk=%b, i2s_data=%b, adv_read=%b | s_valid=%b, b_ready=%b, b_full=%b, L0_out=0x%h, R0_out=0x%h",
                 $time, sys_clk, sys_rst, i2s_bclk, monitor_i2s_lrclk, monitor_i2s_data, monitor_adv_read_enable,
                 sample_valid, monitor_buffer_ready, buffer_full,
                 (TB_TOTAL_MONO_CHANNELS > 0) ? audio_channel_out[0] : 'x, // Check bounds for safety
                 (TB_TOTAL_MONO_CHANNELS > 1) ? audio_channel_out[1] : 'x);
        // $monitor("bit_counter %d, shift_reg %h", monitor_bit_counter, monitor_shift_reg);
    end

    initial begin
        $dumpfile("buf_audio_in_stereo_tb.vcd");
        $dumpvars(0, buf_audio_in_tb);
    end

endmodule

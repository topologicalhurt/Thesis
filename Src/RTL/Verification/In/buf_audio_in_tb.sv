`timescale 1ns / 1ps

`include "In/buf_audio_in_tb.svh"

module buf_audio_in_tb;

    // Parameters
    parameter I2S_WIDTH = 24;
    parameter NUM_AUDIO_CHANNELS = 8;  // Reduced for testbench
    parameter AUDIO_WIDTH = 24;
    parameter BUFFER_DEPTH = 4;

    // Clock periods
    parameter SYS_CLK_PERIOD = 10;     // 100 MHz system clock
    parameter I2S_CLK_PERIOD = 40;     // 25 MHz I2S bit clock
    parameter LRCLK_PERIOD = I2S_CLK_PERIOD * I2S_WIDTH * 2; // Left + Right channels

    // DUT interface signals
    logic                adv_read_enable;
    logic                sys_clk;
    logic                sys_rst;
    logic                i2s_bclk;
    logic                i2s_lrclk;
    logic                i2s_data;
    logic [AUDIO_WIDTH-1:0] audio_channel_out [NUM_AUDIO_CHANNELS-1:0];
    logic                sample_valid;
    logic                buffer_ready;
    logic                buffer_full;

    // Test variables
    logic [I2S_WIDTH-1:0] test_sample_left = 24'h123456;
    logic [I2S_WIDTH-1:0] test_sample_right = 24'hABCDEF;
    logic [I2S_WIDTH-1:0] current_sample;
    int bit_index;
    int sample_count;
    // int channel_index;

    // Instantiate DUT
    buf_audio_in #(
        .I2S_WIDTH(I2S_WIDTH),
        .NUM_AUDIO_CHANNELS(NUM_AUDIO_CHANNELS),
        .AUDIO_WIDTH(AUDIO_WIDTH),
        .BUFFER_DEPTH(BUFFER_DEPTH)
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

    // I2S LR clock generation (word select)
    initial begin
        i2s_lrclk = 0;
        forever #(LRCLK_PERIOD/2) i2s_lrclk = ~i2s_lrclk;
    end

    // Task to send I2S sample
    task send_i2s_sample(input [I2S_WIDTH-1:0] sample_data);
        begin
            current_sample = sample_data;

            // Wait for LR clock edge (channel change)
            @(posedge i2s_lrclk or negedge i2s_lrclk);

            // TODO:
            // sending sample on pos edge of i2s_lrclk = left channel
            // sending sample on neg edge of i2s_lrclk = right channel

            // 2'b00 is undefined behaviour
            // case (r)
            //     2'b01: @(posedge i2s_lrclk);
            //     2'b10: @(negedge i2s_lrclk);
            //     2'b11: @(posedge i2s_lrclk or negedge i2s_lrclk);
            //     default: begin
            //         $fatal(1, "Illegal value for r (%b) – undefined behaviour.", r);
            //     end
            // endcase

            // Send MSB first, with one bit delay after WS change
            for (bit_index = I2S_WIDTH-1; bit_index >= 0; bit_index--) begin
                @(posedge i2s_bclk);
                i2s_data = current_sample[bit_index];
            end

            $display("Time %0t: Sent I2S sample: 0x%06h (LR=%b)", $time, sample_data, i2s_lrclk);
        end
    endtask

    // Task to check audio outputs
    task check_audio_outputs(input [AUDIO_WIDTH-1:0] expected_value);
        begin
            // Wait for sample_valid with timeout
            fork
                begin
                    @(posedge sample_valid);
                    $display("Time %0t: sample_valid detected", $time);
                end
                begin
                    #(SYS_CLK_PERIOD * 1000);
                    $display("Time %0t: Timeout waiting for sample_valid", $time);
                end
            join_any
            disable fork;

            @(posedge sys_clk);

            for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
                if (audio_channel_out[i] !== expected_value) begin
                    $display("Time %0t: Channel %0d output mismatch! Expected: 0x%06h, Got: 0x%06h",
                           $time, i, expected_value, audio_channel_out[i]);
                end else begin
                    $display("Time %0t: Channel %0d output correct: 0x%06h",
                             $time, i, audio_channel_out[i]);
                end

                assert(audio_channel_out[i] == expected_value)
                    else $fatal(1, "The audio channel out should match the sample value sent in");
            end

            `adv_read_enable
        end
    endtask

    // Main test sequence
    initial begin
        $display("=== Audio Buf In Testbench Started ===");

        // Initialize signals
        sys_rst = 1;
        i2s_data = 0;
        sample_count = 0;
        adv_read_enable = 1'b0;

        // Test 1: Reset during operation
        $display("\n=== Test 1: Reset During Operation ===");
        `RESET_CYCLE
        $display("Time %0t: Reset sequence completed", $time);

        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            if (audio_channel_out[i] !== 0) begin
                $error("Time %0t: Channel %0d not cleared after reset: 0x%06h",
                       $time, i, audio_channel_out[i]);
            end
        end

        // Test 2: Send left channel sample
        $display("\n=== Test 2: Left Channel Sample ===");
        // send_i2s_sample(test_sample_left, 2'b01);
        send_i2s_sample(test_sample_left);
        check_audio_outputs(test_sample_left);
        sample_count++;

        `RESET_CYCLE

        // Test 3: Send right channel sample
        $display("\n=== Test 3: Right Channel Sample ===");
        // send_i2s_sample(test_sample_right, 2'b10);
        send_i2s_sample(test_sample_right);
        check_audio_outputs(test_sample_right);
        sample_count++;

        `RESET_CYCLE

        // Test 4: Send multiple samples to test buffering
        $display("\n=== Test 4: Multiple Samples for Buffer Test ===");
        for (int i = 0; i <= BUFFER_DEPTH + 1; i++) begin
            logic [I2S_WIDTH-1:0] test_val = I2S_WIDTH'(24'h100000 + i);
            // send_i2s_sample(test_val, 2'b11);
            send_i2s_sample(test_val);
            sample_count++;
        end

        // Not sure if this makes sense, but the adv_read_enable has to be set high to check buffer overflow
        `adv_read_enable

        // Check for buffer full condition
        if (buffer_full) begin
            $display("Time %0t: Buffer full detected (correctly)", $time);
            $display("Shift register contains: %h", dut.shift_reg);
        end

        assert (buffer_full)
            else $fatal(1, "Buffer should not overflow. Buffer should report full.");

        `RESET_CYCLE

        // Test 5: Verify buffer ready signal
        $display("\n=== Test 5: Buffer Ready Verification ===");
        // Wait for buffer_ready with timeout
        fork
            begin
                wait(buffer_ready);
                $display("Time %0t: Buffer ready signal asserted", $time);
            end
            begin
                #(SYS_CLK_PERIOD * 1000);
                $display("Time %0t: Buffer ready timeout", $time);
                $fatal(1, "Never received a timeout signal");
            end
        join_any
        disable fork;

        `RESET_CYCLE

        // Test 6: Pattern test
        $display("\n=== Test 6: Pattern Test ===");
        for (int pattern = 0; pattern < 4; pattern++) begin
            logic [I2S_WIDTH-1:0] pattern_val = I2S_WIDTH'({8'hAA, 8'h55, 8'hAA} + pattern);
            // send_i2s_sample(pattern_val, 2'b11);
            send_i2s_sample(pattern_val);
            check_audio_outputs(pattern_val);
            sample_count++;
            `RESET_CYCLE
        end

        // Final verification
        $display("\n=== Test Summary ===");
        $display("Total samples sent: %0d", sample_count);
        $display("Test completed successfully!");

        $finish;
    end

    // logic monitor_buffer_ready;
    // always_ff @(posedge sys_clk) begin
    //     monitor_buffer_ready <= buffer_ready;
    // end

    // logic monitor_i2s_lrclk;
    // always_ff @(posedge sys_clk) begin
    //     monitor_i2s_lrclk <= i2s_lrclk;
    // end

    // initial begin
    //     $monitor("Time %0t: sample_valid=%b, buffer_ready=%b, buffer_full=%b, i2s_lrclk=%b",
    //              $time, sample_valid, monitor_buffer_ready, buffer_full, monitor_i2s_lrclk);
    // end

    // Debug: Monitor DUT internal signals
    initial begin
        forever begin
            @(posedge dut.i2s_bclk);
            $display("Time %0t: i2s_bclk edge - bit_counter=%0d, lrclk=%b, prev_lrclk=%b, data=%b, shift_reg=0x%06h",
                     $time, dut.bit_counter, dut.i2s_lrclk, dut.prev_lrclk, dut.i2s_data, dut.shift_reg);
            if (dut.sample_ready_i2s) begin
                $display("Time %0t: DUT sample_ready_i2s asserted!", $time);
            end
        end
    end

    // Monitor system clock domain
    initial begin
        forever begin
            @(posedge sys_clk);
            if (dut.sample_ready_sys && !dut.sample_ready_sys_prev) begin
                $display("Time %0t: DUT sample_ready_sys rising edge", $time);
            end
        end
    end

    initial begin
        $dumpfile("buf_audio_in_tb.vcd");
        $dumpvars(0, buf_audio_in_tb);
    end

endmodule

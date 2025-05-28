`timescale 1ns / 1ps

module buf_audio_in #(
    parameter I2S_WIDTH          = 24,
    parameter NUM_AUDIO_CHANNELS = 24,
    parameter AUDIO_WIDTH        = 24,
    parameter BUFFER_DEPTH       = 4
) (
    input  logic                       sys_clk,          // System clock
    input  logic                       sys_rst,          // System reset (active high)

    // I2S Interface (codec is master)
    input  logic                       i2s_bclk,         // Bit clock
    input  logic                       i2s_lrclk,        // Word-select
    input  logic                       i2s_data,         // Serial data in

    // Consumer handshake
    input  logic                       adv_read_enable,  // Advance read_ptr (active high)

    // Parallel audio outputs
    output logic [AUDIO_WIDTH-1:0]     audio_channel_out [NUM_AUDIO_CHANNELS-1:0],
    output logic                       sample_valid,     // One-cycle pulse when new samples accepted
    output logic                       buffer_ready,     // All channels hold at least one sample
    output logic                       buffer_full       // Any channel FIFO full
);

    //  I²S RECEIVE (codec clock domain)
    logic [I2S_WIDTH-1:0] shift_reg;
    logic [4:0]           bit_counter;
    logic                 prev_lrclk;

    logic                 sample_ready_i2s;
    logic [I2S_WIDTH-1:0] sample_latched_i2s;

    always_ff @(posedge i2s_bclk or posedge sys_rst) begin
        if (sys_rst) begin
            shift_reg        <= '0;
            bit_counter      <= '0;
            prev_lrclk       <= 1'b0;
            sample_ready_i2s <= 1'b0;
        end else begin
            shift_reg <= {shift_reg[I2S_WIDTH-2:0], i2s_data};

            if (prev_lrclk != i2s_lrclk) begin           // channel edge
                if (bit_counter == I2S_WIDTH-1) begin    // full word captured
                    sample_ready_i2s  <= 1'b1;
                    sample_latched_i2s <= shift_reg;
                end
                bit_counter <= '0;
            end else begin
                bit_counter      <= bit_counter + 5'd1;
                sample_ready_i2s <= 1'b0;
            end
            prev_lrclk <= i2s_lrclk;
        end
    end

    //  CDC: 2-FF synchroniser into sys_clk domain
    logic                 sample_ready_sys_meta, sample_ready_sys;
    logic [I2S_WIDTH-1:0] sample_latched_sys_meta, sample_latched_sys;

    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            sample_ready_sys_meta  <= 1'b0;
            sample_ready_sys       <= 1'b0;
            sample_latched_sys_meta <= '0;
            sample_latched_sys      <= '0;
        end else begin
            sample_ready_sys_meta   <= sample_ready_i2s;
            sample_ready_sys        <= sample_ready_sys_meta;
            sample_latched_sys_meta <= sample_latched_i2s;
            sample_latched_sys      <= sample_latched_sys_meta;
        end
    end

    // Channel independent FIFO's / Circular bufs
    localparam PTR_W = $clog2(BUFFER_DEPTH);

    logic [AUDIO_WIDTH-1:0] circ_buf [NUM_AUDIO_CHANNELS-1:0][BUFFER_DEPTH-1:0];
    logic [PTR_W:0]         write_ptr    [NUM_AUDIO_CHANNELS-1:0];   // extra MSB
    logic [PTR_W:0]         read_ptr     [NUM_AUDIO_CHANNELS-1:0];   // extra MSB
    logic [PTR_W:0]         buffer_count [NUM_AUDIO_CHANNELS-1:0];

    logic [NUM_AUDIO_CHANNELS-1:0] channel_full;
    logic [NUM_AUDIO_CHANNELS-1:0] channel_non_empty;
    logic [AUDIO_WIDTH-1:0] audio_out_buf [NUM_AUDIO_CHANNELS-1:0];  // Always_comb triggers on write to here

    genvar ch;
    generate
        for (ch = 0; ch < NUM_AUDIO_CHANNELS; ch++) begin : FIFO_PER_CH
            always_ff @(posedge sys_clk or posedge sys_rst) begin
                if (sys_rst) begin
                    write_ptr[ch]    <= '0;
                    read_ptr[ch]     <= '0;
                    buffer_count[ch] <= '0;
                    audio_out_buf[ch]<= '0;
                end else begin
                    logic [PTR_W:0] wp_next = write_ptr[ch] + 1'b1;
                    // logic fifo_full_next = (wp_next[PTR_W-1:0] == read_ptr[ch][PTR_W-1:0]) &&
                    //                     (wp_next[PTR_W]     != read_ptr[ch][PTR_W]);
                    logic fifo_cur_full  = (buffer_count[ch] == BUFFER_DEPTH);
                    logic fifo_cur_empty = (buffer_count[ch] == '0);

                    // Write path
                    if (sample_ready_sys) begin
                        circ_buf[ch][write_ptr[ch][PTR_W-1:0]] <= sample_latched_sys;
                        write_ptr[ch] <= wp_next;

                        // Handle buffer overflow
                        if (fifo_cur_full)
                            read_ptr[ch] <= read_ptr[ch] + 1'b1;    // Drop oldest
                        else
                            buffer_count[ch] <= buffer_count[ch] + 1'b1;

                        if (fifo_cur_empty)
                            audio_out_buf[ch] <= sample_latched_sys;    // Ready to write the sample immediately
                        end
                    end

                    // Read path
                    if (adv_read_enable && buffer_count[ch] != '0) begin
                        audio_out_buf[ch] <= circ_buf[ch][read_ptr[ch][PTR_W-1:0]];     // Read from the appropriate channel
                        read_ptr[ch]      <= read_ptr[ch] + 1'b1;
                        buffer_count[ch]  <= buffer_count[ch] - 1'b1;
                    end
                end

                // Combinational flags
                assign channel_full[ch]      = (buffer_count[ch] == BUFFER_DEPTH);
                assign channel_non_empty[ch] = (buffer_count[ch] != '0);
            end
    endgenerate

    logic sample_ready_sys_prev;
    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            sample_ready_sys_prev <= 1'b0;
            sample_valid          <= 1'b0;
        end else begin
            sample_valid          <=  sample_ready_sys & ~sample_ready_sys_prev;
            sample_ready_sys_prev <=  sample_ready_sys;
        end
    end

    // Continuous read-side data
    always_comb begin
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            audio_channel_out[i] = audio_out_buf[i];
        end
        buffer_ready = &channel_non_empty;   // every channel has ≥1 sample
        buffer_full  = |channel_full;        // any channel is full
    end

endmodule

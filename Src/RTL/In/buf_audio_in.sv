`include "buf_audio_in.svh"

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
    input  wire                        adv_read_enable,  // Advance read_ptr (active high)

    // Parallel audio outputs
    output logic [AUDIO_WIDTH-1:0]     audio_channel_out [(NUM_AUDIO_CHANNELS * STEREO_MULTIPLIER)-1:0],
    output logic                       sample_valid,     // One-cycle pulse when new samples accepted
    output logic                       buffer_ready,     // All channels hold at least one sample
    output logic                       buffer_full       // Any channel FIFO full
);
    //  I²S RECEIVE (codec clock domain)
    logic [I2S_WIDTH-1:0] shift_reg;
    logic [4:0]           bit_counter;
    logic                 captured_lrclk_i2s;            // To store lrclk at the time of sample latch

    logic                 sample_ready_i2s;
    logic [I2S_WIDTH-1:0] sample_latched_i2s;
    logic                 word_fully_shifted_flag_i2s;

    always_ff @(posedge i2s_bclk or posedge sys_rst) begin
        if (sys_rst) begin
            shift_reg          <= '0;
            bit_counter        <= '0;
            sample_ready_i2s   <= 1'b0;
            captured_lrclk_i2s <= 1'b0;
        end else begin
            word_fully_shifted_flag_i2s <= 1'b0;

            // Count bits continuously
            bit_counter <= bit_counter + 5'd1;

            // Check for word completion every I2S_WIDTH bits
            if (bit_counter == I2S_WIDTH) begin
                word_fully_shifted_flag_i2s <= 1'b1; // Signal that we have a complete word
                captured_lrclk_i2s <= i2s_lrclk;     // Latch current LRCLK for this word
                sample_latched_i2s <= {shift_reg[I2S_WIDTH-2:0], i2s_data}; // Latch the completed word (including current bit)
                bit_counter <= 5'd1;                 // Reset counter (current bit is bit 0 of next word)
            end

            // Always shift in new data AFTER checking for completion
            shift_reg <= {shift_reg[I2S_WIDTH-2:0], i2s_data};

            sample_ready_i2s <= word_fully_shifted_flag_i2s; // sample_ready is the flag from this cycle

        end
    end

    //  CDC: 2-FF synchroniser into sys_clk domain
    logic                 sample_ready_sys_meta, sample_ready_sys;
    logic [I2S_WIDTH-1:0] sample_latched_sys_meta, sample_latched_sys;
    logic                 captured_lrclk_sys_meta, captured_lrclk_sys; // Synchronized LRCLK

    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            sample_ready_sys_meta   <= 1'b0;
            sample_ready_sys        <= 1'b0;
            sample_latched_sys_meta <= '0;
            sample_latched_sys      <= '0;
            captured_lrclk_sys_meta <= 1'b0;
            captured_lrclk_sys      <= 1'b0;
        end else begin
            sample_ready_sys_meta   <= sample_ready_i2s;
            sample_ready_sys        <= sample_ready_sys_meta;
            sample_latched_sys_meta <= sample_latched_i2s;
            sample_latched_sys      <= sample_latched_sys_meta;
            captured_lrclk_sys_meta <= captured_lrclk_i2s;
            captured_lrclk_sys      <= captured_lrclk_sys_meta;
        end
    end

    // Channel independent FIFO's / Circular bufs for each MONO stream
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
            for (lr_idx = 0; lr_idx < STEREO_MULTIPLIER; lr_idx++) begin : FIFO_PER_MONO_STREAM

                // This block defines behavior for one mono FIFO
                always_ff @(posedge sys_clk or posedge sys_rst) begin
                    if (sys_rst) begin
                        write_ptr[ch_pair_idx][lr_idx]    <= '0;
                        read_ptr[ch_pair_idx][lr_idx]     <= '0;
                        buffer_count[ch_pair_idx][lr_idx] <= '0;
                        for (int k = 0; k < BUFFER_DEPTH; k++) begin
                            circ_buf[ch_pair_idx][lr_idx][k] <= '0;
                        end
                    end else begin
                        /* Write path:
                        A new sample arrives (sample_ready_sys is high for one cycle).
                        It belongs to the L/R channel indicated by captured_lrclk_sys.
                        This sample is written to ALL ch_pair_idx FIFOs for that specific L/R stream.
                        (This means the single I2S input is fanned out to NUM_AUDIO_CHANNELS stereo buffers).
                        */
                        if (sample_ready_sys && (captured_lrclk_sys != lr_idx)) begin
                            circ_buf[ch_pair_idx][lr_idx][write_ptr[ch_pair_idx][lr_idx][PTR_W-1:0]] <=
                            sample_latched_sys[$bits(sample_latched_sys)-1 -: AUDIO_WIDTH]; // Ensure correct width, MSB aligned

                            write_ptr[ch_pair_idx][lr_idx] <= write_ptr[ch_pair_idx][lr_idx] + 1'b1;

                            if (buffer_count[ch_pair_idx][lr_idx] == BUFFER_COUNT_WIDTH'(BUFFER_DEPTH)) begin // FIFO was full
                                read_ptr[ch_pair_idx][lr_idx] <= read_ptr[ch_pair_idx][lr_idx] + 1'b1;        // Overwrite: advance read_ptr (drop oldest)
                            end else begin
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
                assign channel_full[ch_pair_idx][lr_idx] = (buffer_count[ch_pair_idx][lr_idx] == BUFFER_COUNT_WIDTH'(BUFFER_DEPTH));
            end
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
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin     // i is ch_pair_idx
            for (int j = 0; j < STEREO_MULTIPLIER; j++) begin  // j is lr_idx (0 for L, 1 for R)
                // Output the sample at the current read pointer of the respective mono FIFO
                if (sys_rst) begin
                    audio_channel_out[i * STEREO_MULTIPLIER + j] = '0;
                end else begin
                    audio_channel_out[i * STEREO_MULTIPLIER + j] = circ_buf[i][j][read_ptr[i][j][PTR_W-1:0]];
                end
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

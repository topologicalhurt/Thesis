`timescale 1ns / 1ps

module buf_audio_in #(
    parameter I2S_WIDTH = 24,
    parameter NUM_AUDIO_CHANNELS = 24,
    parameter AUDIO_WIDTH = 24,
    parameter BUFFER_DEPTH = 4
) (
    input  logic                read_enable,

    input  logic                sys_clk,      // System clock
    input  logic                sys_rst,      // System reset (active high)

    // I2S Interface
    input  logic                i2s_bclk,     // Bit clock
    input  logic                i2s_lrclk,    // Left/Right clock (Word Select)
    input  logic                i2s_data,     // Serial data input

    // N parallel audio channel outputs
    output logic [AUDIO_WIDTH-1:0] audio_channel_out [NUM_AUDIO_CHANNELS-1:0],
    output logic                sample_valid,  // Pulses high for one sys_clk cycle when new samples are available
    output logic                buffer_ready,  // Indicates clean buffered data is available
    output logic                buffer_full    // Buffer overflow warning
);

    // I2S receiver signals
    logic [I2S_WIDTH-1:0]       shift_reg;
    logic [4:0]                 bit_counter;
    logic                       prev_lrclk;

    // Cross-domain synchronization
    logic                       sample_ready_i2s;         // In I2S clock domain
    logic                       sample_ready_sys_meta;    // Metastability protection
    logic                       sample_ready_sys;         // In system clock domain
    logic [I2S_WIDTH-1:0]       sample_latched_i2s;
    logic [I2S_WIDTH-1:0]       sample_latched_sys_meta;
    logic [I2S_WIDTH-1:0]       sample_latched_sys;

    // Clean audio buffering (circular buffer for each channel)
    logic [AUDIO_WIDTH-1:0]     audio_buffer [NUM_AUDIO_CHANNELS-1:0][BUFFER_DEPTH-1:0];
    logic [$clog2(BUFFER_DEPTH)-1:0] write_ptr [NUM_AUDIO_CHANNELS-1:0];
    logic [$clog2(BUFFER_DEPTH)-1:0] read_ptr [NUM_AUDIO_CHANNELS-1:0];
    logic [NUM_AUDIO_CHANNELS-1:0] channel_buffer_valid;
    logic [$clog2(BUFFER_DEPTH):0] buffer_count [NUM_AUDIO_CHANNELS-1:0];

    // I2S Receiver logic - Standard I2S: sample data on rising edge of bit clock
    always_ff @(posedge i2s_bclk or posedge sys_rst) begin
        if (sys_rst) begin
            shift_reg <= '0;
            bit_counter <= '0;
            prev_lrclk <= 1'b0;
            sample_ready_i2s <= 1'b0;
        end else begin
            // Normal bit clock - shift in data
            shift_reg <= {shift_reg[I2S_WIDTH-2:0], i2s_data};

            // Detect word select (LR clock) transition
            if (prev_lrclk != i2s_lrclk) begin
                // Check if we just completed a word (bit 23 captured on previous bclk)
                if (bit_counter == I2S_WIDTH - 1) begin
                    sample_ready_i2s <= 1'b1;
                    sample_latched_i2s <= shift_reg; // preserve sample before clearing
                end
                bit_counter <= '0;           // Reset bit counter at each channel change
            end else begin
                bit_counter <= bit_counter + 1'b1;
                sample_ready_i2s <= 1'b0;
            end

            prev_lrclk <= i2s_lrclk;
        end
    end

    // Clock domain crossing (from I2S clock to system clock)
    // Two-stage synchronizer to prevent metastability
    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            sample_ready_sys_meta <= 1'b0;
            sample_ready_sys <= 1'b0;
            sample_latched_sys_meta <= 0;
            sample_latched_sys      <= 0;
        end else begin
            sample_ready_sys_meta <= sample_ready_i2s;
            sample_ready_sys <= sample_ready_sys_meta;
            sample_latched_sys_meta <= sample_latched_i2s;
            sample_latched_sys      <= sample_latched_sys_meta;
        end
    end

    // Sample distribution in system clock domain
    logic sample_ready_sys_prev;

    // Initialize buffers and pointers
    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
                write_ptr[i] <= '0;
                read_ptr[i] <= '0;
                buffer_count[i] <= '0;
                channel_buffer_valid[i] <= 1'b0;
                for (int j = 0; j < BUFFER_DEPTH; j++) begin
                    audio_buffer[i][j] <= '0;
                end
            end
            sample_valid <= 1'b0;
            sample_ready_sys_prev <= 1'b0;
            buffer_ready <= 1'b0;
            buffer_full <= 1'b0;
        end else begin
            bit detected_overflow = 1'b0;

            // Detect rising edge of sample_ready_sys
            // And write new sample to all channel buffers
            if (sample_ready_sys && !sample_ready_sys_prev) begin
                for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
                    if (buffer_count[i] < BUFFER_DEPTH) begin
                        audio_buffer[i][write_ptr[i]] <= sample_latched_sys;
                        write_ptr[i] <= ($clog2(BUFFER_DEPTH))'((int'(write_ptr[i]) + 1) % BUFFER_DEPTH);
                        buffer_count[i] <= buffer_count[i] + 1;
                        channel_buffer_valid[i] <= 1'b1;
                    end else begin
                        detected_overflow = 1'b1;
                    end
                end
                sample_valid <= 1'b1;
            end else begin
                sample_valid <= 1'b0;
            end

            if (detected_overflow) begin
                buffer_full <= 1'b1;
            end

            sample_ready_sys_prev <= sample_ready_sys;
            buffer_ready <= &channel_buffer_valid;
        end
    end

    // Continuous assignment of buffered outputs
    always_comb begin
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            if (channel_buffer_valid[i] && buffer_count[i] > 0) begin
                audio_channel_out[i] = audio_buffer[i][read_ptr[i]];
            end else begin
                audio_channel_out[i] = 0;
            end
        end
    end

    // Buffer read logic (for when downstream consumes data)
    // I.e. controlled by external logic / read_enable
    always_ff @(posedge sys_clk) begin
        if (read_enable && buffer_full) begin
                // Clear only when every channel has at least one free slot
                bit clear_ok = 1'b1;
                for (int k = 0; k < NUM_AUDIO_CHANNELS; k++)
                    if (buffer_count[k] == BUFFER_DEPTH) clear_ok = 1'b0;
                buffer_full <= !clear_ok;
        end else if (read_enable) begin
                for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
                    if (buffer_count[i] > 0) begin
                        read_ptr[i] <= ($clog2(BUFFER_DEPTH))'((int'(read_ptr[i]) + 1) % BUFFER_DEPTH);
                        buffer_count[i] <= buffer_count[i] - 1;
                        if (buffer_count[i] == 1) begin
                            channel_buffer_valid[i] <= 1'b0;
                        end
                    end
                end
            end
        end

endmodule : buf_audio_in

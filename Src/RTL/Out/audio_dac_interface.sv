module audio_dac_interface #(
    parameter int AUDIO_DATA_WIDTH = 24
) (
    // Clock and reset
    input  logic                         clk_100mhz,     // 100MHz system clock from PYNQ-Z2
    input  logic                         resetn,         // Active low reset

    // Audio processing clock - typically 22.5792MHz (44.1kHz*512) or 24.576MHz (48kHz*512)
    input  logic                         audio_clk,      // Audio clock

    // Audio data input (from processing chain or memory)
    input  logic [AUDIO_DATA_WIDTH-1:0]  audio_left_in,  // Left channel input
    input  logic [AUDIO_DATA_WIDTH-1:0]  audio_right_in, // Right channel input
    input  logic                         audio_valid_in, // Data valid indicator
    output logic                         audio_ready_out,// Ready for data

    // I2S signals to ADAU1761 codec
    output logic                         i2s_bclk,       // Bit clock
    output logic                         i2s_lrclk,      // Left/Right clock (Word Select)
    output logic                         i2s_sdata,      // Serial data output to DAC

    // I2C control interface for codec configuration
    inout  wire                          i2c_scl,        // I2C clock
    inout  wire                          i2c_sda,        // I2C data

    // Optional debug/status signals
    output logic                         fifo_overflow,  // FIFO overflow indicator
    output logic                         fifo_underflow, // FIFO underflow indicator
    output logic [3:0]                   status          // General status
);
    // ADAU1761 needs to be configured via I2C before starting audio output

    // Clock generation parameters for common audio sample rates
    // For 44.1kHz: 22.5792MHz / 512 = 44.1kHz
    // For 48kHz: 24.576MHz / 512 = 48kHz
    localparam int BCLK_DIVIDER     = 4;    // ADAU1761 expects 64fs (i.e., 64*48k = 3.072MHz bit clock)
    localparam int LRCLK_DIVIDER    = 64;   // BCLK / 64 = sample rate clock

    // State definitions for I2S output
    typedef enum logic [1:0] {
        IDLE,
        RUNNING,
        ERROR,
        RESET
    } state_t;

    // Internal registers
    state_t                        state;
    logic [$clog2(BCLK_DIVIDER):0] bclk_counter;
    logic [$clog2(LRCLK_DIVIDER):0] lrclk_counter;
    logic                          bclk_internal;
    logic                          lrclk_internal;
    logic                          lrclk_prev;

    // Shift register for I2S data output
    logic [AUDIO_DATA_WIDTH-1:0]   shift_reg;
    logic [$clog2(AUDIO_DATA_WIDTH):0] bit_counter;

    // FIFO for clock domain crossing
    logic [AUDIO_DATA_WIDTH-1:0]   fifo_left[16];
    logic [AUDIO_DATA_WIDTH-1:0]   fifo_right[16];
    logic [3:0]                    fifo_write_ptr;
    logic [3:0]                    fifo_read_ptr;
    logic                          fifo_empty;
    logic                          fifo_full;

    // Current audio sample being processed
    logic [AUDIO_DATA_WIDTH-1:0]   current_left;
    logic [AUDIO_DATA_WIDTH-1:0]   current_right;
    logic                          load_next_sample;

    // FIFO control
    assign fifo_empty = (fifo_write_ptr == fifo_read_ptr);
    assign fifo_full = ((fifo_write_ptr + 1) & 4'hF) == fifo_read_ptr;

    // Signal when we can accept more audio data
    assign audio_ready_out = ~fifo_full;

    // I2C controller for codec configuration
    i2c_codec_config i2c_config (
        .clk(clk_100mhz),
        .resetn(resetn),
        .i2c_scl(i2c_scl),
        .i2c_sda(i2c_sda),
        .config_done(status[0]),
        .error(status[1])
    );

    // Handle data input into FIFO (system clock domain)
    always_ff @(posedge clk_100mhz or negedge resetn) begin
        if (!resetn) begin
            fifo_write_ptr <= 4'h0;
            fifo_overflow <= 1'b0;
        end else begin
            // Clear overflow flag when it's read
            if (status[3] == 1'b1) begin
                fifo_overflow <= 1'b0;
            end

            // Handle incoming audio data
            if (audio_valid_in && !fifo_full) begin
                fifo_left[fifo_write_ptr] <= audio_left_in;
                fifo_right[fifo_write_ptr] <= audio_right_in;
                fifo_write_ptr <= (fifo_write_ptr + 1) & 4'hF;
            end else if (audio_valid_in && fifo_full) begin
                fifo_overflow <= 1'b1;
                status[3] <= 1'b1;
            end
        end
    end

    // Generate bit clock and LR clock
    always_ff @(posedge audio_clk or negedge resetn) begin
        if (!resetn) begin
            bclk_counter <= '0;
            lrclk_counter <= '0;
            bclk_internal <= 1'b0;
            lrclk_internal <= 1'b0;
            i2s_bclk <= 1'b0;
            i2s_lrclk <= 1'b0;
        end else begin
            // Generate bit clock
            if (bclk_counter == BCLK_DIVIDER - 1) begin
                bclk_counter <= '0;
                bclk_internal <= ~bclk_internal;
            end else begin
                bclk_counter <= bclk_counter + 1;
            end

            // Generate LR clock
            if (lrclk_counter == LRCLK_DIVIDER - 1) begin
                lrclk_counter <= '0;
                lrclk_internal <= ~lrclk_internal;
            end else begin
                lrclk_counter <= lrclk_counter + 1;
            end

            // Output the clocks
            i2s_bclk <= bclk_internal;
            i2s_lrclk <= lrclk_internal;
        end
    end

    // I2S data output logic - data changes on falling edge of BCLK
    always_ff @(negedge bclk_internal or negedge resetn) begin
        if (!resetn) begin
            shift_reg <= '0;
            bit_counter <= '0;
            i2s_sdata <= 1'b0;
            lrclk_prev <= 1'b0;
            fifo_read_ptr <= 4'h0;
            current_left <= '0;
            current_right <= '0;
            load_next_sample <= 1'b1;
            fifo_underflow <= 1'b0;
            state <= RESET;
        end else begin
            // Detect LR clock transition
            if (lrclk_prev != lrclk_internal) begin
                bit_counter <= '0;

                // Left/Right channel selection
                if (lrclk_internal == 1'b0) begin
                    // Transition to left channel
                    shift_reg <= current_left;
                end else begin
                    // Transition to right channel
                    shift_reg <= current_right;

                    // After right channel is done, prepare to load next sample
                    load_next_sample <= 1'b1;
                end
            end else begin
                // Normal bit clock operation
                if (bit_counter < AUDIO_DATA_WIDTH) begin
                    // Output MSB first (I2S format)
                    i2s_sdata <= shift_reg[AUDIO_DATA_WIDTH-1];
                    shift_reg <= {shift_reg[AUDIO_DATA_WIDTH-2:0], 1'b0};
                    bit_counter <= bit_counter + 1;
                end
            end

            // Load next sample from FIFO if needed (at end of frame)
            if (load_next_sample && lrclk_internal == 1'b1 && lrclk_prev == 1'b1) begin
                load_next_sample <= 1'b0;

                if (!fifo_empty) begin
                    current_left <= fifo_left[fifo_read_ptr];
                    current_right <= fifo_right[fifo_read_ptr];
                    fifo_read_ptr <= (fifo_read_ptr + 1) & 4'hF;
                    state <= RUNNING;
                end else begin
                    // Underflow - no data available
                    fifo_underflow <= 1'b1;
                    status[2] <= 1'b1;

                    // Output zeros or hold last sample
                    current_left <= '0;
                    current_right <= '0;
                    state <= ERROR;
                end
            end

            lrclk_prev <= lrclk_internal;
        end
    end

    // Optional debug logic - monitor FIFO levels, etc.
    always_ff @(posedge clk_100mhz) begin
        if (!resetn) begin
            status[3:2] <= 2'b00;
        end else begin
            // Status bit 2: FIFO underflow occurred
            // Status bit 3: FIFO overflow occurred
            // Already handled in other blocks
        end
    end

endmodule : audio_dac_interface

// I2C Controller for ADAU1761 configuration
module i2c_codec_config (
    input  logic clk,
    input  logic resetn,
    inout  wire  i2c_scl,
    inout  wire  i2c_sda,
    output logic config_done,
    output logic error
);
    // I2C constants
    localparam ADAU1761_I2C_ADDR = 7'h3B; // I2C address for ADAU1761 (7-bit)
    localparam I2C_CLOCK_DIV = 248;       // For 100kHz I2C from 100MHz clock (DIV = Fclk/[4*Fi2c] - 1)

    // FSM states
    typedef enum logic [3:0] {
        IDLE,
        START,
        SEND_ADDR,
        SEND_REG_H,
        SEND_REG_L,
        SEND_DATA,
        STOP,
        WAIT,
        DONE,
        ERROR
    } i2c_state_t;

    // Internal state variables
    i2c_state_t state;
    logic [7:0] bit_counter;
    logic [7:0] byte_counter;
    logic [7:0] config_index;
    logic [7:0] i2c_clk_count;
    logic       i2c_clk_en;
    logic       scl_out;
    logic       sda_out;
    logic       i2c_busy;

    // Tristate control for I2C
    logic       scl_oe;  // Output enable for SCL (1 = drive, 0 = high-z)
    logic       sda_oe;  // Output enable for SDA (1 = drive, 0 = high-z)

    // Assign I2C signals
    assign i2c_scl = scl_oe ? scl_out : 1'bz;
    assign i2c_sda = sda_oe ? sda_out : 1'bz;

    // Configuration data for ADAU1761
    // Format: {register_address[15:0], data[7:0]}
    typedef struct packed {
        logic [15:0] reg_addr;
        logic [7:0]  value;
    } codec_config_t;

    // Configuration data
    codec_config_t codec_config[8];

    // Initialize configuration data
    initial begin
        // Reset the ADAU1761
        codec_config[0] = '{reg_addr: 16'h4000, value: 8'h01};  // Soft reset

        // PLL and Clock settings for 48kHz
        codec_config[1] = '{reg_addr: 16'h4002, value: 8'h01};  // Enable PLL
        codec_config[2] = '{reg_addr: 16'h4011, value: 8'h01};  // SerDac LRCLK = 48kHz
        codec_config[3] = '{reg_addr: 16'h4012, value: 8'h01};  // SerDac BCLK = 64fs

        // Audio Path Configuration
        codec_config[4] = '{reg_addr: 16'h4015, value: 8'h01};  // Enable I2S mode for DAC
        codec_config[5] = '{reg_addr: 16'h4019, value: 8'h03};  // Enable DAC to both left & right channels
        codec_config[6] = '{reg_addr: 16'h4023, value: 8'h30};  // Set DAC output volume (0dB)
        codec_config[7] = '{reg_addr: 16'h4025, value: 8'h30};  // Set DAC output volume (0dB)
    end

    // I2C clock generation
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            i2c_clk_count <= 8'h00;
            i2c_clk_en <= 1'b0;
        end else begin
            if (i2c_clk_count == I2C_CLOCK_DIV) begin
                i2c_clk_count <= 8'h00;
                i2c_clk_en <= 1'b1;
            end else begin
                i2c_clk_count <= i2c_clk_count + 8'h01;
                i2c_clk_en <= 1'b0;
            end
        end
    end

    // I2C state machine
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state <= IDLE;
            config_index <= 8'h00;
            byte_counter <= 8'h00;
            bit_counter <= 8'h00;
            scl_out <= 1'b1;
            sda_out <= 1'b1;
            scl_oe <= 1'b1;
            sda_oe <= 1'b1;
            config_done <= 1'b0;
            error <= 1'b0;
            i2c_busy <= 1'b0;
        end else if (i2c_clk_en) begin
            case (state)
                IDLE: begin
                    scl_out <= 1'b1;
                    sda_out <= 1'b1;
                    scl_oe <= 1'b1;
                    sda_oe <= 1'b1;

                    if (config_index < 8) begin
                        state <= START;
                        i2c_busy <= 1'b1;
                    end else begin
                        config_done <= 1'b1;
                        i2c_busy <= 1'b0;
                    end
                end

                START: begin
                    // I2C start condition: SDA goes low while SCL is high
                    sda_out <= 1'b0;
                    state <= SEND_ADDR;
                    bit_counter <= 8'h07; // 7-bit address + 1 bit R/W
                    byte_counter <= 8'h00;
                end

                SEND_ADDR: begin
                    // Send device address (7 bits) + Write bit (0)
                    if (bit_counter == 8'h00) begin
                        // After sending 8 bits, release SDA for ACK
                        scl_out <= 1'b0;
                        sda_oe <= 1'b0; // Release SDA for slave ACK
                        state <= SEND_REG_H;
                        bit_counter <= 8'h07;
                    end else begin
                        if (scl_out == 1'b0) begin
                            scl_out <= 1'b1;
                            // Don't change SDA when SCL is high
                        end else begin
                            scl_out <= 1'b0;
                            if (bit_counter == 8'h00) begin
                                // Last bit (R/W bit) - set to 0 for write
                                sda_out <= 1'b0;
                            end else begin
                                // Address bits
                                sda_out <= ADAU1761_I2C_ADDR[bit_counter - 1];
                            end
                            bit_counter <= bit_counter - 8'h01;
                        end
                        sda_oe <= 1'b1; // Drive SDA
                    end
                end

                SEND_REG_H: begin
                    // Send register address high byte
                    if (bit_counter == 8'h00) begin
                        // After sending 8 bits, release SDA for ACK
                        scl_out <= 1'b0;
                        sda_oe <= 1'b0; // Release SDA for slave ACK
                        state <= SEND_REG_L;
                        bit_counter <= 8'h07;
                    end else begin
                        if (scl_out == 1'b0) begin
                            scl_out <= 1'b1;
                            // Don't change SDA when SCL is high
                        end else begin
                            scl_out <= 1'b0;
                            sda_out <= codec_config[config_index].reg_addr[8 + bit_counter];
                            bit_counter <= bit_counter - 8'h01;
                        end
                        sda_oe <= 1'b1; // Drive SDA
                    end
                end

                SEND_REG_L: begin
                    // Send register address low byte
                    if (bit_counter == 8'h00) begin
                        // After sending 8 bits, release SDA for ACK
                        scl_out <= 1'b0;
                        sda_oe <= 1'b0; // Release SDA for slave ACK
                        state <= SEND_DATA;
                        bit_counter <= 8'h07;
                    end else begin
                        if (scl_out == 1'b0) begin
                            scl_out <= 1'b1;
                            // Don't change SDA when SCL is high
                        end else begin
                            scl_out <= 1'b0;
                            sda_out <= codec_config[config_index].reg_addr[bit_counter];
                            bit_counter <= bit_counter - 8'h01;
                        end
                        sda_oe <= 1'b1; // Drive SDA
                    end
                end

                SEND_DATA: begin
                    // Send data byte
                    if (bit_counter == 8'h00) begin
                        // After sending 8 bits, release SDA for ACK
                        scl_out <= 1'b0;
                        sda_oe <= 1'b0; // Release SDA for slave ACK
                        state <= STOP;
                    end else begin
                        if (scl_out == 1'b0) begin
                            scl_out <= 1'b1;
                            // Don't change SDA when SCL is high
                        end else begin
                            scl_out <= 1'b0;
                            sda_out <= codec_config[config_index].value[bit_counter];
                            bit_counter <= bit_counter - 8'h01;
                        end
                        sda_oe <= 1'b1; // Drive SDA
                    end
                end

                STOP: begin
                    // I2C stop condition: SDA goes high while SCL is high
                    if (scl_out == 1'b0) begin
                        scl_out <= 1'b1;
                        sda_out <= 1'b0;
                        sda_oe <= 1'b1; // Drive SDA
                    end else begin
                        sda_out <= 1'b1;
                        state <= WAIT;
                    end
                end

                WAIT: begin
                    // Wait a few cycles before moving to next config
                    byte_counter <= byte_counter + 8'h01;
                    if (byte_counter >= 8'h10) begin
                        config_index <= config_index + 8'h01;
                        state <= IDLE;
                    end
                end

                default: begin
                    state <= ERROR;
                    error <= 1'b1;
                end
            endcase
        end
    end

endmodule : i2c_codec_config

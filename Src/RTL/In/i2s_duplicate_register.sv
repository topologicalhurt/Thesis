module audio_processor (
input wire sys_clk,      // System clock
input wire sys_rst,      // System reset (active high)

// I2S Interface
input wire i2s_bclk,     // Bit clock
input wire i2s_lrclk,    // Left/Right clock (Word Select)
input wire i2s_data,     // Serial data input

output reg sample_valid  // Pulses high for one sys_clk cycle when new samples are available
);
GENERATE_I2S_CHANNEL_REGS();

// I2S receiver signals
reg [I2S_WIDTH-1:0] shift_reg;
reg [4:0] bit_counter;
reg prev_lrclk;

// Cross-domain synchronization
reg sample_ready_i2s;         // In I2S clock domain
reg sample_ready_sys_meta;    // Metastability protection
reg sample_ready_sys;         // In system clock domain

// I2S Receiver logic
// Standard I2S: sample data on rising edge of bit clock
always @(posedge i2s_bclk or posedge sys_rst) begin
    if (sys_rst) begin
        shift_reg <= 24'b0;
        bit_counter <= 5'b0;
        prev_lrclk <= 1'b0;

        // CLR_I2S_CHANNEL_REGS(NUM_AUDIO_CHANNELS);

        sample_ready_i2s <= 1'b0;
    end else begin
        // Detect word select (LR clock) transition
        if (prev_lrclk != i2s_lrclk) begin
            bit_counter <= 5'b0; // Reset bit counter at each channel change
            
            shift_reg <= 24'b0;  // Clear shift register for next channel
        end else begin
            // Normal bit clock - shift in data
            // I2S sends MSB first, one bit delay after WS changes
            if (bit_counter > 0) begin  // First bit after WS change is skipped
                shift_reg <= {shift_reg[22:0], i2s_data};
            end
            
            if (bit_counter < 24) begin
                bit_counter <= bit_counter + 1'b1;
            end
            
            // Clear the ready flag once we start receiving new data
            if (sample_ready_i2s && bit_counter > 2) begin
                sample_ready_i2s <= 1'b0;
            end
        end
        
        prev_lrclk <= i2s_lrclk;
    end
end

// Clock domain crossing (from I2S clock to system clock)
// Two-stage synchronizer to prevent metastability
always @(posedge sys_clk or posedge sys_rst) begin
    if (sys_rst) begin
        sample_ready_sys_meta <= 1'b0;
        sample_ready_sys <= 1'b0;
    end else begin
        sample_ready_sys_meta <= sample_ready_i2s;
        sample_ready_sys <= sample_ready_sys_meta;
    end
end

// Sample distribution in system clock domain
reg sample_ready_sys_prev;

always @(posedge sys_clk or posedge sys_rst) begin
    if (sys_rst) begin
        CLR_I2S_CHANNEL_REGS(NUM_AUDIO_CHANNELS);
        sample_valid <= 1'b0;
        sample_ready_sys_prev <= 1'b0;
    end else begin
        // Detect rising edge of sample_ready_sys
        if (sample_ready_sys && !sample_ready_sys_prev) begin

            // Distribute samples to all 4 parallel paths
            // SET_I2S_CHANNEL_REGS(NUM_AUDIO_CHANNELS);
            
            sample_valid <= 1'b1;
        end else begin
            sample_valid <= 1'b0;
        end
        
        sample_ready_sys_prev <= sample_ready_sys;
    end
end

endmodule

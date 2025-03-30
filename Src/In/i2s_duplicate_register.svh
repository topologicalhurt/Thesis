`ifndef AUDIO_DEFS_VH
    `define AUDIO_DEFS_VH

    `define STEREO 1
    `define NUM_AUDIO_CHANNELS 4
    `define AUDIO_WIDTH 24
    `define I2S_WIDTH 24

    // Generate I2S channel registers
    `define GENERATE_I2S_CHANNEL_REGS() \
        generate \
            genvar i; \
            for (i = 1; i <= `NUM_AUDIO_CHANNELS; i = i + 1) begin : audio_regs \
                `ifdef STEREO \
                    `if STEREO \
                        output reg [`AUDIO_WIDTH-1:0] audio_left_``i; \
                        output reg [`AUDIO_WIDTH-1:0] audio_right_``i; \
                    `else \
                        output reg [`AUDIO_WIDTH-1:0] audio_mono_``i; \
                    `endif \
                `endif \
            end \
        endgenerate \

`endif // AUDIO_DEFS_VH
    
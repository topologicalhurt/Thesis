#!/usr/bin/env python
"""
Generates an crossbar wrapper for i2s_duplicate_register.v &
i2s_duplicate_register.vh to allow for mono & stereo buffer registers.
Also allows for different bit-depths to be specified between i2s in &
the buffer register width.
"""


import argparse as ap
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Allocator.Interpreter.consts import LOGGER, MONO_STEREO_WRAPPER_PREFIX, I2S_DUPLICATE_REGISTER_HEADER_PATH,\
I2S_DUPLICATE_REGISTER_PATH
from Allocator.Interpreter.helpers import str2bool


def main() -> None:

    parser = ap.ArgumentParser(description=__doc__.strip())
    parser.add_argument('-s', type=str2bool, default=None,
                     help='Determines if FPGA uses stereo (True) or mono (False) buffer registers for I2S In')
    parser.add_argument('-n', type=int, default=None,
                    help='')
    parser.add_argument('-aw', type=int, default=None,
                     help='The audio bit depth for each channel (recommended / default: 24bit)')
    parser.add_argument('-i2sw', type=int, default=None,
                     help='The expected i2s bit depth (recommended / default: 24bit)')
    parser.add_argument('-f', type=bool, default=False,
                    help='Enable to allow for unsafe / unintended behaviour')
    args = vars(parser.parse_args())

    if args['i2sw'] != args['aw'] and not args['f']:
        LOGGER.warn(MONO_STEREO_WRAPPER_PREFIX.format(
            f'The bit depth for i2s input (I.e. {args["i2sw"]} is != the bit depth of the buffer register {args["aw"]})). '
            'This is highly likely to cause non-functional behaviour or artefacting. Please set the \'f\' '
            'option to true to resolve this conflict.\n'
            f'Assuming the bit-depth of i2s as a control'
        ))
        args['aw'] = args['i2sw']
    elif args['i2sw'] != args['aw']:
        LOGGER.warn(MONO_STEREO_WRAPPER_PREFIX.format(
            f'The bit depth for i2s input (I.e. {args["i2sw"]} is != the bit depth of the buffer register {args["aw"]}.\n'
            'Assuming the dev knows what they\'re doing!'
        ))

    header_args = {'s' : 'is_stereo', 'n' : 'n_audio_channels', 'aw' : 'audio_width', 'i2sw' : 'i2s_width'}
    header_template = generate_header_file(
        **{header_args[k] : v for k, v in args.items() if v is not None and k in header_args}
    )
    i2s_duplicate_register_template = generate_duplicate_register_file()

    _overwrite_fn(I2S_DUPLICATE_REGISTER_HEADER_PATH, header_template)
    _overwrite_fn(I2S_DUPLICATE_REGISTER_PATH, i2s_duplicate_register_template)


def generate_header_file(is_stereo : bool = True, n_audio_channels: int = 4,
                         audio_width : int = 24, i2s_width : int = 24) -> str:

    template = u"""`ifndef AUDIO_DEFS_VH
    `define AUDIO_DEFS_VH

    `define STEREO {is_stereo}
    `define NUM_AUDIO_CHANNELS {n_audio_channels}
    `define AUDIO_WIDTH {audio_width}
    `define I2S_WIDTH {i2s_width}

    // Generate I2S channel registers
    `define GENERATE_I2S_CHANNEL_REGS() \\
        generate \\
            genvar i; \\
            for (i = 1; i <= `NUM_AUDIO_CHANNELS; i = i + 1) begin : audio_regs \\
                `ifdef STEREO \\
                    `if STEREO \\
                        output reg [`AUDIO_WIDTH-1:0] audio_left_``i; \\
                        output reg [`AUDIO_WIDTH-1:0] audio_right_``i; \\
                    `else \\
                        output reg [`AUDIO_WIDTH-1:0] audio_mono_``i; \\
                    `endif \\
                `endif \\
            end \\
        endgenerate \\

`endif // AUDIO_DEFS_VH
    """.format(
        is_stereo=int(is_stereo),
        n_audio_channels=n_audio_channels,
        audio_width=audio_width,
        i2s_width=i2s_width
    )

    return template


def generate_duplicate_register_file() -> str:
    return u"""module audio_processor (
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
"""



def _overwrite_fn(fn : str, content: str) -> None:
    LOGGER.info(MONO_STEREO_WRAPPER_PREFIX.format(
        f'Writing to {fn}'
    ))

    with open(fn, 'w') as f:
        f.write(content)
        f.flush()

    LOGGER.info(MONO_STEREO_WRAPPER_PREFIX.format(
        f'Write to {fn} successful'
    ))


if __name__ == '__main__':
    main()

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

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from consts import MONO_STEREO_WRAPPER_PREFIX, I2S_DUPLICATE_REGISTER_HEADER_PATH,\
I2S_DUPLICATE_REGISTER_PATH
from Allocator.Interpreter.consts import LOGGER
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

    template = f"""`ifndef __AUDIO_DEFS_VH__
`define __AUDIO_DEFS_VH__

// Audio processing configuration parameters
localparam int DFX_REG_CTRL           = 0;
localparam int STEREO                 = {is_stereo};
localparam int AUDIO_WIDTH            = {audio_width};
localparam int BUFFER_DEPTH           = 4;

`endif // AUDIO_DEFS_VH
""".format(
        is_stereo=int(is_stereo),
        n_audio_channels=n_audio_channels,
        audio_width=audio_width,
        i2s_width=i2s_width
    )

    return template


def generate_duplicate_register_file() -> str:
    return """`timescale 1ns / 1ps

module buf_audio_in #(
    parameter I2S_WIDTH = 24,
    parameter NUM_AUDIO_CHANNELS = 24,
    parameter AUDIO_WIDTH = 24,
    parameter BUFFER_DEPTH = 4
) (
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
            // Detect word select (LR clock) transition
            if (prev_lrclk != i2s_lrclk) begin
                // Check if we just completed a word (at bit 23, which is the 24th bit)
                if (bit_counter == I2S_WIDTH - 1) begin
                    sample_ready_i2s <= 1'b1;
                end
                bit_counter <= '0;           // Reset bit counter at each channel change
                shift_reg <= '0;             // Clear shift register for next channel
            end else begin
                // Normal bit clock - shift in data
                // I2S sends MSB first, one bit delay after WS changes
                if (bit_counter > 0) begin   // First bit after WS change is skipped
                    shift_reg <= {shift_reg[I2S_WIDTH-2:0], i2s_data};
                end

                // Increment bit counter
                bit_counter <= bit_counter + 1'b1;

                // Clear ready flag during normal operation
                if (sample_ready_i2s && bit_counter > 2) begin
                    sample_ready_i2s <= 1'b0;
                end
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
        end else begin
            sample_ready_sys_meta <= sample_ready_i2s;
            sample_ready_sys <= sample_ready_sys_meta;
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
            // Detect rising edge of sample_ready_sys
            if (sample_ready_sys && !sample_ready_sys_prev) begin
                // Write new sample to all channel buffers
                for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
                    if (buffer_count[i] < BUFFER_DEPTH) begin
                        audio_buffer[i][write_ptr[i]] <= shift_reg[AUDIO_WIDTH-1:0];
                        write_ptr[i] <= ($clog2(BUFFER_DEPTH))'((int'(write_ptr[i]) + 1) % BUFFER_DEPTH);
                        buffer_count[i] <= buffer_count[i] + 1;
                        channel_buffer_valid[i] <= 1'b1;
                    end else begin
                        buffer_full <= 1'b1;  // Buffer overflow warning
                    end
                end
                sample_valid <= 1'b1;
            end else begin
                sample_valid <= 1'b0;
                buffer_full <= 1'b0;
            end

            sample_ready_sys_prev <= sample_ready_sys;

            // Check if all channels have valid buffered data
            buffer_ready <= &channel_buffer_valid;
        end
    end

    // Continuous assignment of buffered outputs
    always_comb begin
        for (int i = 0; i < NUM_AUDIO_CHANNELS; i++) begin
            if (channel_buffer_valid[i] && buffer_count[i] > 0) begin
                audio_channel_out[i] = audio_buffer[i][read_ptr[i]];
            end else begin
                audio_channel_out[i] = '0;
            end
        end
    end

    // Buffer read logic (when downstream consumes data)
    // This would typically be controlled by external logic
    // For now, we auto-advance read pointers when buffer is not empty
    always_ff @(posedge sys_clk or posedge sys_rst) begin
        if (sys_rst) begin
            // Reset handled above
        end else if (buffer_ready) begin
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

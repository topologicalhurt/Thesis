`ifndef __AUDIO_DEFS_VH__
`define __AUDIO_DEFS_VH__

// Audio buffer configuration parameters

/* verilator lint_off UNUSED */
localparam int DFX_REG_CTRL           = 0;
localparam bit STEREO                 = 1'b1;
/* verilator lint_on UNUSED */

localparam int STEREO_MULTIPLIER      = int'(STEREO) + 1;
localparam int BUFFER_DEPTH           = 4 * STEREO_MULTIPLIER;

`endif // AUDIO_DEFS_VH

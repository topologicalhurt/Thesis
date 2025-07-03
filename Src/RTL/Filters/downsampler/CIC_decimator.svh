`ifndef __CIC_DEC_DEFS_VH__
`define __CIC_DEC_DEFS_VH__

`define N_STAGES 5 // Number of integrator/comb stages
`define DECIMATION_RATE 2;
`define COMB_DELAY 1
`define AUDIO_IN 24
`define BIT_GROWTH `N_STAGES * $clog2(`DECIMATION_RATE * `COMB_DELAY) // Bit growth N*log2(R*M)
`define INTEGRATOR_WIDTH `IN_WIDTH + `BIT_GROWTH

`endif // __CIC_DEC_DEFS_VH__

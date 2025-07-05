`ifndef __BIT_GROWTH_DEFS_VH__
`define __BIT_GROWTH_DEFS_VH__

// Calculate bit growth for unsigned multiplication
`define MULT_GROWTH_UNSIGNED(A_WIDTH, B_WIDTH) (A_WIDTH + B_WIDTH)

// Calculate bit growth for signed multiplication
`define MULT_GROWTH_SIGNED(A_WIDTH, B_WIDTH) (A_WIDTH + B_WIDTH)

// Calculate bit growth for adding two numbers.
// Equivalent to $max(A_WIDTH, B_WIDTH) + 1
`define ADD_GROWTH(A_WIDTH, B_WIDTH) (((A_WIDTH) > (B_WIDTH)) ? ((A_WIDTH) + 1) : ((B_WIDTH) + 1))

// Calculate bit growth for adding N numbers of A_WIDTH
`define ADD_GROWTH_N(A_WIDTH, N) ((A_WIDTH) + $clog2(N))

`endif // __BIT_GROWTH_DEFS_VH__

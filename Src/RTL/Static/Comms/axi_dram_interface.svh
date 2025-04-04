`ifndef AXI_DEFS_SVH
`define AXI_DEFS_SVH

// AXI4 Parameters for Pynq-Z2
`define AXI_ID_WIDTH 6
`define AXI_ADDR_WIDTH 32
`define AXI_DATA_WIDTH 64
`define AXI_STRB_WIDTH (`AXI_DATA_WIDTH/8)
`define AXI_USER_WIDTH 1

// AXI Response Codes
`define AXI_RESP_OKAY   2'b00
`define AXI_RESP_EXOKAY 2'b01
`define AXI_RESP_SLVERR 2'b10
`define AXI_RESP_DECERR 2'b11

// AXI Burst Types
`define AXI_BURST_FIXED 2'b00
`define AXI_BURST_INCR  2'b01
`define AXI_BURST_WRAP  2'b10

// AXI Memory Types (AxCACHE)
`define AXI_CACHE_NORMAL_NON_CACHEABLE_NON_BUFFERABLE 4'b0000
`define AXI_CACHE_NORMAL_NON_CACHEABLE_BUFFERABLE     4'b0001
`define AXI_CACHE_NORMAL_CACHEABLE_NON_BUFFERABLE     4'b0010
`define AXI_CACHE_NORMAL_CACHEABLE_BUFFERABLE         4'b0011
`define AXI_CACHE_DEVICE_NON_BUFFERABLE              4'b0100
`define AXI_CACHE_DEVICE_BUFFERABLE                  4'b0101

// AXI Protection Types (AxPROT)
`define AXI_PROT_UNPRIVILEGED_ACCESS 3'b000
`define AXI_PROT_PRIVILEGED_ACCESS   3'b001
`define AXI_PROT_SECURE_ACCESS       3'b000
`define AXI_PROT_NON_SECURE_ACCESS   3'b010
`define AXI_PROT_DATA_ACCESS         3'b000
`define AXI_PROT_INSTRUCTION_ACCESS  3'b100

// Commonly used combinations
`define AXI_PROT_DEFAULT 3'b000

// Memory sizes based on Pynq-Z2 (512MB DDR3 RAM)
`define DDR_SIZE       32'h20000000  // 512MB
`define DDR_BASE_ADDR  32'h00000000

// DRAM Access Macros
`define DRAM_SINGLE_READ(addr)  \
    user_req <= 1'b1;           \
    user_rnw <= 1'b1;           \
    user_addr <= addr;          \
    @(posedge user_ready);      \
    user_req <= 1'b0;           \

`define DRAM_SINGLE_WRITE(addr, data, strb) \
    user_req <= 1'b1;                       \
    user_rnw <= 1'b0;                       \
    user_addr <= addr;                       \
    user_wdata <= data;                     \
    user_wstrb <= strb;                     \
    @(posedge user_ready);                  \
    user_req <= 1'b0;

`endif // AXI_DEFS_SVH

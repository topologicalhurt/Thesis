// DFX Controller Interface definitions
`ifndef __DFX_CONTROLLER_SVH__
`define __DFX_CONTROLLER_SVH__

// DFX Controller constants
typedef enum logic [3:0] {
    DFX_STATE_IDLE,             // Idle state, ready for new command
    DFX_STATE_INIT,             // Initialization state
    DFX_STATE_SHUTDOWN,         // Shutting down current configuration
    DFX_STATE_CHECK_BITSTREAM,  // Validate bitstream before loading
    DFX_STATE_LOAD_PREP,        // Prepare region for reconfiguration
    DFX_STATE_LOADING,          // Active reconfiguration
    DFX_STATE_VERIFY,           // Verify reconfiguration success
    DFX_STATE_STARTUP,          // Start up the new configuration
    DFX_STATE_DONE,             // Reconfiguration complete
    DFX_STATE_ERROR             // Error state
} dfx_state_t;

// DFX Controller commands
typedef enum logic [3:0] {
    DFX_CMD_NOOP        = 4'h0, // No operation
    DFX_CMD_LOAD        = 4'h1, // Load a new bitstream to a partition
    DFX_CMD_RESET       = 4'h2, // Reset a reconfigurable partition
    DFX_CMD_STATUS      = 4'h3, // Get status information
    DFX_CMD_ABORT       = 4'h4, // Abort current reconfiguration
    DFX_CMD_CLEAR_ERR   = 4'h5, // Clear error flags
    DFX_CMD_DEBUG       = 4'h6, // Enter debug mode
    DFX_CMD_RESERVE     = 4'h7  // Reserve a region for future ops
} dfx_cmd_t;

// DFX Error codes
typedef enum logic [3:0] {
    DFX_ERR_NONE        = 4'h0, // No error
    DFX_ERR_INVALID_CMD = 4'h1, // Invalid command
    DFX_ERR_INVALID_RP  = 4'h2, // Invalid reconfigurable partition
    DFX_ERR_INVALID_BS  = 4'h3, // Invalid bitstream
    DFX_ERR_BUSY        = 4'h4, // Controller busy
    DFX_ERR_TIMEOUT     = 4'h5, // Operation timeout
    DFX_ERR_ACCESS      = 4'h6, // Access error (ICAP/PCAP)
    DFX_ERR_CRC         = 4'h7, // CRC error
    DFX_ERR_SEU         = 4'h8, // Single event upset detected
    DFX_ERR_MEM_ACCESS  = 4'h9, // Memory access error
    DFX_ERR_SYSTEM      = 4'hF  // System error
} dfx_error_t;

// Register map for DFX Controller
// (Assuming AXI-Lite interface with 32-bit registers)
localparam int DFX_REG_CTRL           = 0;  // Control register (W/R)
localparam int DFX_REG_STATUS         = 1;  // Status register (R)
localparam int DFX_REG_ERROR          = 2;  // Error register (R)
localparam int DFX_REG_RP_SELECT      = 3;  // RP selection register (W/R)
localparam int DFX_REG_BS_ADDR_LOW    = 4;  // Bitstream address low 32 bits (W/R)
localparam int DFX_REG_BS_ADDR_HIGH   = 5;  // Bitstream address high 32 bits (W/R)
localparam int DFX_REG_BS_SIZE        = 6;  // Bitstream size in bytes (W/R)
localparam int DFX_REG_BS_ID          = 7;  // Bitstream ID (W/R)
localparam int DFX_REG_TIMEOUT        = 8;  // Timeout value (W/R)
localparam int DFX_REG_VERSION        = 9;  // Version register (R)
localparam int DFX_REG_DEBUG          = 10; // Debug register (W/R)
localparam int DFX_REG_CONFIG_ID      = 11; // Current configuration ID (R)
localparam int DFX_REG_PROGRESS       = 12; // Progress indicator (R)
localparam int DFX_REG_INT_ENABLE     = 13; // Interrupt enable (W/R)
localparam int DFX_REG_INT_STATUS     = 14; // Interrupt status (R/W1C)
localparam int DFX_REG_RP_STATUS      = 15; // RP Status register (R)

// Bit definitions for DFX_REG_CTRL
localparam int DFX_CTRL_START_BIT     = 0;  // Start operation (self-clearing)
localparam int DFX_CTRL_ABORT_BIT     = 1;  // Abort operation (self-clearing)
localparam int DFX_CTRL_CLR_ERR_BIT   = 2;  // Clear error flags (self-clearing)
localparam int DFX_CTRL_CMD_SHIFT     = 4;  // Command field shift
localparam int DFX_CTRL_CMD_MASK      = 4'hF; // Command field mask
localparam int DFX_CTRL_SECURE_BIT    = 8;  // Enable secure mode
localparam int DFX_CTRL_SELF_TEST_BIT = 9;  // Run self-test (self-clearing)
localparam int DFX_CTRL_SW_RESET_BIT  = 31; // Software reset (self-clearing)

// Bit definitions for DFX_REG_STATUS
localparam int DFX_STATUS_BUSY_BIT    = 0;  // Controller busy
localparam int DFX_STATUS_DONE_BIT    = 1;  // Operation complete
localparam int DFX_STATUS_ERROR_BIT   = 2;  // Error occurred
localparam int DFX_STATUS_STATE_SHIFT = 4;  // State field shift
localparam int DFX_STATUS_STATE_MASK  = 4'hF; // State field mask

// Bit definitions for DFX_REG_INT_STATUS/DFX_REG_INT_ENABLE
localparam int DFX_INT_DONE_BIT       = 0;  // Operation complete
localparam int DFX_INT_ERROR_BIT      = 1;  // Error occurred
localparam int DFX_INT_TIMEOUT_BIT    = 2;  // Timeout occurred
localparam int DFX_INT_PROGRESS_BIT   = 3;  // Progress update

// Bitstream header structure (32 bytes total)
typedef struct packed {
    logic [31:0] magic;            // Magic number (0x44465800 = "DFX\0")
    logic [31:0] version;          // Header version
    logic [31:0] bitstream_length; // Length of bitstream in bytes
    logic [31:0] target_rp_id;     // Target reconfigurable partition ID
    logic [31:0] bitstream_id;     // Bitstream identifier
    logic [31:0] timestamp;        // Creation timestamp
    logic [31:0] checksum;         // Checksum of bitstream
    logic [31:0] reserved;         // Reserved for future use
} dfx_bitstream_header_t;

// Interface for communication with ICAP controller
interface dfx_icap_if;
    logic        clk;      // ICAP clock
    logic        ce_n;     // Chip enable (active low)
    logic        write_n;  // Write enable (active low)
    logic [31:0] din;      // Data input
    logic [31:0] dout;     // Data output
    logic        busy;     // ICAP busy flag

    modport controller (
        output clk, ce_n, write_n, din,
        input  dout, busy
    );

    modport icap (
        input  clk, ce_n, write_n, din,
        output dout, busy
    );
endinterface

// User interface for DFX controller
interface dfx_user_if #(parameter int NUM_RPS = 4);
    logic                      request;     // Request reconfiguration
    logic                      grant;       // Grant reconfiguration request
    logic [$clog2(NUM_RPS)-1:0] rp_id;     // Reconfigurable partition ID
    logic [31:0]               bs_id;       // Bitstream ID to load
    logic [63:0]               bs_addr;     // Bitstream address in memory
    logic [31:0]               bs_size;     // Bitstream size in bytes
    logic                      busy;        // Controller busy
    logic                      done;        // Operation complete
    logic [3:0]                error;       // Error code

    modport requester (
        output request, rp_id, bs_id, bs_addr, bs_size,
        input  grant, busy, done, error
    );

    modport controller (
        input  request, rp_id, bs_id, bs_addr, bs_size,
        output grant, busy, done, error
    );
endinterface

`endif // __DFX_CONTROLLER_SVH__

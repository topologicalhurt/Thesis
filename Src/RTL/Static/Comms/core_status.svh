`ifndef CORE_STATUS_SVH
`define CORE_STATUS_SVH

// Core status types
typedef enum logic [1:0] {
    IDLE      = 2'b00,   // Core is idle, ready for new tasks
    BUSY      = 2'b01,   // Core is currently processing
    ERROR     = 2'b10,   // Core encountered an error
    COMPLETE  = 2'b11    // Core has completed its task
} core_status_t;

`endif // CORE_STATUS_SVH

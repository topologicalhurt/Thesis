`ifndef AXI_INTERRUPT_DEFS_SVH
`define AXI_INTERRUPT_DEFS_SVH

`include "Src/RTL/Static/Comms/core_status.svh"

// Interrupt types
typedef enum int {
    INT_CORE_DONE        = 0,  // Audio core processing completed
    INT_CORE_ERROR       = 1,  // Audio core encountered an error
    INT_BUS_ERROR        = 2,  // Communication bus error
    INT_BUFFER_OVERFLOW  = 3,  // Audio buffer overflow
    INT_BUFFER_UNDERFLOW = 4,  // Audio buffer underflow
    INT_SYNC_LOST        = 5,  // Audio synchronization lost
    INT_TEMP_WARNING     = 6,  // Temperature warning
    INT_SOFT_INT         = 7   // Software-triggered interrupt
} interrupt_type_t;

// Register offsets (byte addresses for AXI4-Lite)
localparam int INTR_REG_CTRL          = 32'h00;  // Control register
localparam int INTR_REG_STATUS        = 32'h04;  // Status register
localparam int INTR_REG_CORE_CTRL     = 32'h08;  // Core control register
localparam int INTR_REG_CORE_STATUS   = 32'h0C;  // Core status register
localparam int INTR_REG_INT_ENABLE    = 32'h10;  // Interrupt enable register
localparam int INTR_REG_INT_STATUS    = 32'h14;  // Interrupt status register
localparam int INTR_REG_INT_CLEAR     = 32'h18;  // Interrupt clear register
localparam int INTR_REG_CORE_SELECT   = 32'h1C;  // Core selection for individual control

// Bit positions within control register
localparam int CTRL_GLOBAL_PAUSE      = 0;  // Pause all cores
localparam int CTRL_GLOBAL_STOP       = 1;  // Stop all cores
localparam int CTRL_GLOBAL_RESUME     = 2;  // Resume all cores
localparam int CTRL_INT_ENABLE        = 3;  // Global interrupt enable
localparam int CTRL_SOFT_RESET        = 4;  // Soft reset for all cores

// Bit positions within core control register
localparam int CORE_CTRL_PAUSE        = 0;  // Pause selected core
localparam int CORE_CTRL_STOP         = 1;  // Stop selected core
localparam int CORE_CTRL_RESUME       = 2;  // Resume selected core

// Helper macros for software control

// Enable an interrupt type
`define ENABLE_INTERRUPT(type) \
    write_reg(INTR_REG_INT_ENABLE, read_reg(INTR_REG_INT_ENABLE) | (1 << type))

// Disable an interrupt type
`define DISABLE_INTERRUPT(type) \
    write_reg(INTR_REG_INT_ENABLE, read_reg(INTR_REG_INT_ENABLE) & ~(1 << type))

// Clear a pending interrupt
`define CLEAR_INTERRUPT(type) \
    write_reg(INTR_REG_INT_CLEAR, (1 << type))

// Pause a specific core
`define PAUSE_CORE(core_id) \
    write_reg(INTR_REG_CORE_SELECT, core_id); \
    write_reg(INTR_REG_CORE_CTRL, (1 << CORE_CTRL_PAUSE))

// Stop a specific core
`define STOP_CORE(core_id) \
    write_reg(INTR_REG_CORE_SELECT, core_id); \
    write_reg(INTR_REG_CORE_CTRL, (1 << CORE_CTRL_STOP))

// Resume a specific core
`define RESUME_CORE(core_id) \
    write_reg(INTR_REG_CORE_SELECT, core_id); \
    write_reg(INTR_REG_CORE_CTRL, (1 << CORE_CTRL_RESUME))

// Pause all cores
`define PAUSE_ALL_CORES() \
    write_reg(INTR_REG_CTRL, (1 << CTRL_GLOBAL_PAUSE))

// Stop all cores
`define STOP_ALL_CORES() \
    write_reg(INTR_REG_CTRL, (1 << CTRL_GLOBAL_STOP))

// Resume all cores
`define RESUME_ALL_CORES() \
    write_reg(INTR_REG_CTRL, (1 << CTRL_GLOBAL_RESUME))

// Check if a specific core is busy
`define IS_CORE_BUSY(core_id) \
    ((read_reg(INTR_REG_CORE_STATUS) >> core_id) & 0x1)

// Check if a specific interrupt is pending
`define IS_INTERRUPT_PENDING(type) \
    ((read_reg(INTR_REG_INT_STATUS) >> type) & 0x1)

`endif // AXI_INTERRUPT_DEFS_SVH

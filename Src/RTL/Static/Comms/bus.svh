`ifndef BUS_DEFS_SVH
`define BUS_DEFS_SVH

`include "Src/RTL/Static/Comms/core_status.svh"

// Instruction types for audio ensemble cores communication
typedef enum logic [1:0] {
    HALT_PAUSE = 2'b00,  // Temporarily pause processing
    STOP      = 2'b01,   // Stop processing completely
    CONTINUE  = 2'b10,   // Resume processing after pause
    DONE      = 2'b11    // Processing completed
} bus_instruction_t;

// Function to extract destination ID for a specific core
function automatic logic [CORE_ID_WIDTH-1:0] get_dst_id(
    input logic [NUM_CORES*CORE_ID_WIDTH-1:0] dst_ids,
    input int core_idx,
    input int NUM_CORES,
    input int CORE_ID_WIDTH
);
    return dst_ids[core_idx*CORE_ID_WIDTH +: CORE_ID_WIDTH];
endfunction

// Function to extract instruction for a specific core
function automatic logic [INSTR_WIDTH-1:0] get_instruction(
    input logic [NUM_CORES*INSTR_WIDTH-1:0] instructions,
    input int core_idx,
    input int NUM_CORES,
    input int INSTR_WIDTH
);
    return instructions[core_idx*INSTR_WIDTH +: INSTR_WIDTH];
endfunction

// Interface definitions
interface bus_if #(
    parameter int NUM_CORES = 4,
    parameter int INSTR_WIDTH = 2
);
    localparam int CORE_ID_WIDTH = $clog2(NUM_CORES);

    // From core to bus
    logic [NUM_CORES-1:0] send_req;
    logic [NUM_CORES-1:0] broadcast_mode;
    logic [NUM_CORES*CORE_ID_WIDTH-1:0] dst_ids;
    logic [NUM_CORES*INSTR_WIDTH-1:0] instructions;
    logic [NUM_CORES-1:0] send_grant;

    // From bus to core
    logic [NUM_CORES-1:0] recv_valid;
    logic [CORE_ID_WIDTH-1:0] src_id;
    logic [INSTR_WIDTH-1:0] instruction;

    // Modport for cores (clients)
    modport core (
        output send_req, broadcast_mode, dst_ids, instructions,
        input send_grant, recv_valid, src_id, instruction
    );

    // Modport for bus (server)
    modport server (
        input send_req, broadcast_mode, dst_ids, instructions,
        output send_grant, recv_valid, src_id, instruction
    );

endinterface : bus_if

`endif // BUS_DEFS_SVH

// ------------------------------------------------------------------------
// Filename:       bus.sv
//
// Project:        LLAC, intelligent hardware scheduler targeting common
// audio signal chains.
//
// For more information see the repository:
// https://github.com/topologicalhurt/Thesis
//
// Purpose:        N/A
//
// Author: topologicalhurt csin0659@uni.sydney.edu.au
//
// ------------------------------------------------------------------------
// Copyright (C) 2025, LLAC project LLC
//
// This file is a part of the RTL module
// It is intended to be used as part of the Comms design where a README.md
// detailing the design should exist, conforming to the details provided
// under docs/CONTRIBUTING.md. The Comms module is covered by the GPL 3.0
// License (see below.)
//
// The design is NOT COVERED UNDER ANY WARRANTY.
//
// LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
// As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html
//
// A copy of this license is included at the root directory. It should've
// been provided to you
// Otherwise please consult:
// https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
// ------------------------------------------------------------------------


module bus #(
    parameter int NUM_CORES = 4,
    parameter int INSTR_WIDTH = 2
) (
    input  logic                   clk,
    input  logic                   reset,

    // From cores (sending interface)
    input  logic [NUM_CORES-1:0]   send_req,
    input  logic [NUM_CORES-1:0]   broadcast_mode, // 1 = broadcast to all cores
    input  logic [NUM_CORES*CORE_ID_WIDTH-1:0] dst_ids,
    input  logic [NUM_CORES*INSTR_WIDTH-1:0]  instructions,
    output logic [NUM_CORES-1:0]   send_grant,

    // To cores (receiving interface)
    output logic [NUM_CORES-1:0]   recv_valid,
    output logic [CORE_ID_WIDTH-1:0] src_id,
    output logic [INSTR_WIDTH-1:0] instruction
);
    localparam int CORE_ID_WIDTH = $clog2(NUM_CORES);

    typedef enum logic [1:0] {
        HALT_PAUSE = 2'b00,
        STOP      = 2'b01,
        CONTINUE  = 2'b10,
        DONE      = 2'b11
    } instruction_t;

    // Arbitration logic - priority encoder to select one sender
    logic [CORE_ID_WIDTH-1:0] selected_core;
    logic [CORE_ID_WIDTH-1:0] priority_ptr;
    logic [NUM_CORES-1:0]     priority_masked_req;
    logic [NUM_CORES-1:0]     priority_unmasked_req;

    // Rotate the priority based on the current pointer
    assign priority_masked_req = send_req & ((~'0) << priority_ptr);
    assign priority_unmasked_req = send_req;

    // Find the highest priority requesting core
    always_comb begin
        selected_core = '0;

        // First check masked requests (higher priority)
        for (int i = NUM_CORES-1; i >= 0; i--) begin
            if (priority_masked_req[i]) selected_core = i;
        end

        // If no masked requests, check unmasked
        if (priority_masked_req == '0) begin
            for (int i = NUM_CORES-1; i >= 0; i--) begin
                if (priority_unmasked_req[i]) selected_core = i;
            end
        end
    end

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            priority_ptr <= '0;
            send_grant <= '0;
            recv_valid <= '0;
            src_id <= '0;
            instruction <= '0;
        end else begin
            send_grant <= '0;
            recv_valid <= '0;

            if (|send_req) begin
                // Grant to the selected core
                send_grant[selected_core] <= 1'b1;
                src_id <= selected_core;
                instruction <= instructions[selected_core*INSTR_WIDTH +: INSTR_WIDTH];

                // Determine who receives this message
                if (broadcast_mode[selected_core]) begin
                    // Send to all cores except sender
                    recv_valid <= ~(1 << selected_core);
                end else begin
                    // Point-to-point - send only to destination
                    recv_valid[dst_ids[selected_core*CORE_ID_WIDTH +: CORE_ID_WIDTH]] <= 1'b1;
                end

                // Update priority for next cycle
                priority_ptr <= (selected_core + 1) % NUM_CORES;
            end
        end
    end

endmodule : bus

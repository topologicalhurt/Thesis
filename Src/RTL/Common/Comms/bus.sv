module bus #(
    parameter NUM_CORES = 4,
    parameter INSTR_WIDTH = 2
) (
    input wire clk,
    input wire reset,
    
    // From cores (sending interface)
    input wire [NUM_CORES-1:0] send_req,
    input wire [NUM_CORES-1:0] broadcast_mode, // 1 = broadcast to all cores
    input wire [NUM_CORES*CORE_ID_WIDTH-1:0] dst_ids,
    input wire [NUM_CORES*INSTR_WIDTH-1:0] instructions,
    output reg [NUM_CORES-1:0] send_grant,
    
    // To cores (receiving interface)
    output reg [NUM_CORES-1:0] recv_valid,
    output reg [CORE_ID_WIDTH-1:0] src_id,
    output reg [INSTR_WIDTH-1:0] instruction
);
    localparam CORE_ID_WIDTH = $clog2(NUM_CORES);

    localparam HALT_PAUSE = 2'b00;
    localparam STOP = 2'b01;
    localparam CONTINUE = 2'b10;
    localparam DONE = 2'b11;
    
    // Arbitration logic - priority encoder to select one sender
    reg [CORE_ID_WIDTH-1:0] selected_core;
    reg [CORE_ID_WIDTH-1:0]  priority_ptr;
    wire [NUM_CORES-1:0] priority_masked_req;
    wire [NUM_CORES-1:0] priority_unmasked_req;
    
    // Rotate the priority based on the current pointer
    assign priority_masked_req = send_req & ((~0) < priority_ptr);
    assign priority_unmasked_req = send_req;
    
    // Find the highest priority requesting core
    always @(*) begin
        integer i;
        selected_core = 0;
        
        // First check masked requests (higher priority)
        for (i = NUM_CORES-1; i >= 0; i = i - 1) begin
            if (priority_masked_req[i]) selected_core = i;
        end
        
        // If no masked requests, check unmasked
        if (priority_masked_req == 0) begin
            for (i = NUM_CORES-1; i >= 0; i = i - 1) begin
                if (priority_unmasked_req[i]) selected_core = i;
            end
        end
    end
    
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            priority_ptr <= 0;
            send_grant <= 0;
            recv_valid <= 0;
            src_id <= 0;
            instruction <= 0;
        end else begin
            send_grant <= 0;
            recv_valid <= 0;
            
            if (|send_req) begin
                // Grant to the selected core
                send_grant[selected_core] <= 1;
                src_id <= selected_core;
                instruction <= instructions[selected_core*INSTR_WIDTH +: INSTR_WIDTH];
                
                // Determine who receives this message
                if (broadcast_mode[selected_core]) begin
                    // Send to all cores except sender
                    recv_valid <= ~(1 << selected_core);
                end else begin
                    // Point-to-point - send only to destination
                    recv_valid[dst_ids[selected_core*CORE_ID_WIDTH +: CORE_ID_WIDTH]] <= 1;
                end
                
            // Update priority for next cycle
            priority_ptr <= (selected_core + 1) % NUM_CORES;
            end
        end
    end
    
endmodule

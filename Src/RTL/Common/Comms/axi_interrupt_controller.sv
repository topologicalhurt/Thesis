module axi_interrupt_controller #(
    parameter int NUM_CORES = 4,
    parameter int NUM_INTERRUPTS = 8,
    parameter int AXI_ADDR_WIDTH = 32,
    parameter int AXI_DATA_WIDTH = 32
) (
    input  logic                       clk,
    input  logic                       resetn,

    // AXI4-Lite Slave Interface
    input  logic [AXI_ADDR_WIDTH-1:0]  s_axil_awaddr,
    input  logic                       s_axil_awvalid,
    output logic                       s_axil_awready,

    input  logic [AXI_DATA_WIDTH-1:0]  s_axil_wdata,
    input  logic [AXI_DATA_WIDTH/8-1:0] s_axil_wstrb,
    input  logic                       s_axil_wvalid,
    output logic                       s_axil_wready,

    output logic [1:0]                 s_axil_bresp,
    output logic                       s_axil_bvalid,
    input  logic                       s_axil_bready,

    input  logic [AXI_ADDR_WIDTH-1:0]  s_axil_araddr,
    input  logic                       s_axil_arvalid,
    output logic                       s_axil_arready,

    output logic [AXI_DATA_WIDTH-1:0]  s_axil_rdata,
    output logic [1:0]                 s_axil_rresp,
    output logic                       s_axil_rvalid,
    input  logic                       s_axil_rready,

    // Interrupt from cores to host
    input  logic [NUM_CORES-1:0]       core_interrupt,
    input  logic [NUM_CORES-1:0]       core_status,
    output logic                       irq_out,

    // Control to cores
    output logic [NUM_CORES-1:0]       core_pause,
    output logic [NUM_CORES-1:0]       core_stop,
    output logic [NUM_CORES-1:0]       core_resume,

    // Interface to bus module
    output logic [NUM_CORES-1:0]       send_req,
    output logic [NUM_CORES-1:0]       broadcast_mode,
    output logic [NUM_CORES*$clog2(NUM_CORES)-1:0] dst_ids,
    output logic [NUM_CORES*2-1:0]     instructions,
    input  logic [NUM_CORES-1:0]       send_grant
);
    localparam int CORE_ID_WIDTH = $clog2(NUM_CORES);

    // Register map
    localparam int REG_CTRL             = 0;  // Control register
    localparam int REG_STATUS           = 1;  // Status register
    localparam int REG_CORE_CTRL        = 2;  // Core control register
    localparam int REG_CORE_STATUS      = 3;  // Core status register
    localparam int REG_INT_ENABLE       = 4;  // Interrupt enable register
    localparam int REG_INT_STATUS       = 5;  // Interrupt status register
    localparam int REG_INT_CLEAR        = 6;  // Interrupt clear register
    localparam int REG_CORE_SELECT      = 7;  // Core selection for individual control

    // Number of 32-bit registers
    localparam int NUM_REGS = 8;

    // Register definitions
    logic [AXI_DATA_WIDTH-1:0] regs[NUM_REGS];
    logic [AXI_DATA_WIDTH-1:0] reg_next[NUM_REGS];

    // Interrupt status and enable registers
    logic [NUM_INTERRUPTS-1:0] int_status;
    logic [NUM_INTERRUPTS-1:0] int_enable;
    logic [NUM_INTERRUPTS-1:0] int_clear;

    // Core control and status
    logic [NUM_CORES-1:0] core_status_reg;
    logic [NUM_CORES-1:0] core_int_pending;

    // Selected core for individual control
    logic [CORE_ID_WIDTH-1:0] selected_core;

    // Bit positions within control register
    localparam int CTRL_GLOBAL_PAUSE_POS    = 0;
    localparam int CTRL_GLOBAL_STOP_POS     = 1;
    localparam int CTRL_GLOBAL_RESUME_POS   = 2;
    localparam int CTRL_INT_ENABLE_POS      = 3;
    localparam int CTRL_SOFT_RESET_POS      = 4;

    // Bit positions within core control register
    localparam int CORE_CTRL_PAUSE_POS      = 0;
    localparam int CORE_CTRL_STOP_POS       = 1;
    localparam int CORE_CTRL_RESUME_POS     = 2;

    // Map interrupt types
    localparam int INT_CORE_DONE            = 0;
    localparam int INT_CORE_ERROR           = 1;
    localparam int INT_BUS_ERROR            = 2;
    localparam int INT_BUFFER_OVERFLOW      = 3;
    localparam int INT_BUFFER_UNDERFLOW     = 4;
    localparam int INT_SYNC_LOST            = 5;
    localparam int INT_TEMP_WARNING         = 6;
    localparam int INT_SOFT_INT             = 7;

    // Map different instructions from bus.svh
    typedef enum logic [1:0] {
        HALT_PAUSE = 2'b00,
        STOP       = 2'b01,
        CONTINUE   = 2'b10,
        DONE       = 2'b11
    } bus_instruction_t;

    // AXI4-Lite write logic
    logic write_en;
    logic [3:0] waddr;

    always_comb begin
        write_en = s_axil_awvalid && s_axil_wvalid && s_axil_awready && s_axil_wready;
        waddr = s_axil_awaddr[5:2]; // Word-aligned addressing
    end

    // AXI4-Lite read logic
    logic read_en;
    logic [3:0] raddr;

    always_comb begin
        read_en = s_axil_arvalid && s_axil_arready;
        raddr = s_axil_araddr[5:2]; // Word-aligned addressing
    end

    // Register update logic
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            for (int i = 0; i < NUM_REGS; i++) begin
                regs[i] <= '0;
            end
            int_status <= '0;
            int_enable <= '0;
            selected_core <= '0;

            s_axil_awready <= 1'b0;
            s_axil_wready <= 1'b0;
            s_axil_bvalid <= 1'b0;
            s_axil_bresp <= 2'b00;
            s_axil_arready <= 1'b0;
            s_axil_rvalid <= 1'b0;
            s_axil_rdata <= '0;
            s_axil_rresp <= 2'b00;

            core_pause <= '0;
            core_stop <= '0;
            core_resume <= '0;
        end else begin
            // Default values
            s_axil_awready <= 1'b1;
            s_axil_wready <= 1'b1;

            if (write_en) begin
                if (waddr < NUM_REGS) begin
                    for (int i = 0; i < AXI_DATA_WIDTH/8; i++) begin
                        if (s_axil_wstrb[i]) begin
                            regs[waddr][i*8 +: 8] <= s_axil_wdata[i*8 +: 8];
                        end
                    end

                    // Handle special registers
                    if (waddr == REG_INT_CLEAR) begin
                        int_status <= int_status & ~s_axil_wdata[NUM_INTERRUPTS-1:0];
                    end
                    else if (waddr == REG_INT_ENABLE) begin
                        int_enable <= s_axil_wdata[NUM_INTERRUPTS-1:0];
                    end
                    else if (waddr == REG_CORE_SELECT) begin
                        selected_core <= s_axil_wdata[CORE_ID_WIDTH-1:0];
                    end
                end

                // Generate write response
                s_axil_bvalid <= 1'b1;
                s_axil_bresp <= 2'b00; // OKAY
            end else if (s_axil_bvalid && s_axil_bready) begin
                s_axil_bvalid <= 1'b0;
            end

            // Handle read transactions
            s_axil_arready <= 1'b1;

            if (read_en) begin
                s_axil_rvalid <= 1'b1;
                s_axil_rresp <= 2'b00; // OKAY

                if (raddr < NUM_REGS) begin
                    s_axil_rdata <= regs[raddr];

                    // Handle special register reads
                    if (raddr == REG_STATUS) begin
                        s_axil_rdata <= {24'b0, core_status_reg};
                    end
                    else if (raddr == REG_INT_STATUS) begin
                        s_axil_rdata <= {24'b0, int_status};
                    end
                    else if (raddr == REG_CORE_STATUS) begin
                        s_axil_rdata <= {24'b0, core_status};
                    end
                end else begin
                    s_axil_rdata <= '0;
                    s_axil_rresp <= 2'b10; // SLVERR
                end
            end else if (s_axil_rvalid && s_axil_rready) begin
                s_axil_rvalid <= 1'b0;
            end

            // Process control register commands
            if (regs[REG_CTRL][CTRL_GLOBAL_PAUSE_POS]) begin
                core_pause <= {NUM_CORES{1'b1}};
                regs[REG_CTRL][CTRL_GLOBAL_PAUSE_POS] <= 1'b0; // Auto-clear
            end else begin
                core_pause <= '0;
            end

            if (regs[REG_CTRL][CTRL_GLOBAL_STOP_POS]) begin
                core_stop <= {NUM_CORES{1'b1}};
                regs[REG_CTRL][CTRL_GLOBAL_STOP_POS] <= 1'b0; // Auto-clear
            end else begin
                core_stop <= '0;
            end

            if (regs[REG_CTRL][CTRL_GLOBAL_RESUME_POS]) begin
                core_resume <= {NUM_CORES{1'b1}};
                regs[REG_CTRL][CTRL_GLOBAL_RESUME_POS] <= 1'b0; // Auto-clear
            end else begin
                core_resume <= '0;
            end

            // Process core-specific control register
            if (regs[REG_CORE_CTRL][CORE_CTRL_PAUSE_POS]) begin
                core_pause[selected_core] <= 1'b1;
                regs[REG_CORE_CTRL][CORE_CTRL_PAUSE_POS] <= 1'b0; // Auto-clear
            end

            if (regs[REG_CORE_CTRL][CORE_CTRL_STOP_POS]) begin
                core_stop[selected_core] <= 1'b1;
                regs[REG_CORE_CTRL][CORE_CTRL_STOP_POS] <= 1'b0; // Auto-clear
            end

            if (regs[REG_CORE_CTRL][CORE_CTRL_RESUME_POS]) begin
                core_resume[selected_core] <= 1'b1;
                regs[REG_CORE_CTRL][CORE_CTRL_RESUME_POS] <= 1'b0; // Auto-clear
            end

            // Update interrupt status based on core interrupts
            for (int i = 0; i < NUM_CORES; i++) begin
                if (core_interrupt[i]) begin
                    int_status[INT_CORE_DONE] <= 1'b1;
                    core_int_pending[i] <= 1'b1;
                end
            end

            // Update status register
            core_status_reg <= core_status;

            // Generate interrupts based on bus commands
            send_req <= '0;

            // Convert control signals to bus commands
            for (int i = 0; i < NUM_CORES; i++) begin
                if (core_pause[i]) begin
                    send_req[i] <= 1'b1;
                    broadcast_mode[i] <= 1'b0;
                    dst_ids[i*CORE_ID_WIDTH +: CORE_ID_WIDTH] <= i;
                    instructions[i*2 +: 2] <= HALT_PAUSE;
                end
                else if (core_stop[i]) begin
                    send_req[i] <= 1'b1;
                    broadcast_mode[i] <= 1'b0;
                    dst_ids[i*CORE_ID_WIDTH +: CORE_ID_WIDTH] <= i;
                    instructions[i*2 +: 2] <= STOP;
                end
                else if (core_resume[i]) begin
                    send_req[i] <= 1'b1;
                    broadcast_mode[i] <= 1'b0;
                    dst_ids[i*CORE_ID_WIDTH +: CORE_ID_WIDTH] <= i;
                    instructions[i*2 +: 2] <= CONTINUE;
                end
            end
        end
    end

    // Generate IRQ output to host
    always_comb begin
        irq_out = |(int_status & int_enable) && regs[REG_CTRL][CTRL_INT_ENABLE_POS];
    end

endmodule : axi_interrupt_controller

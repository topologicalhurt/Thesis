// ------------------------------------------------------------------------
// Filename:       llac_top_interface.sv
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


module llac_top_interface #(
    parameter int NUM_CORES = 4,
    parameter int NUM_INTERRUPTS = 8,
    parameter int AXI_ID_WIDTH = 6,
    parameter int AXI_ADDR_WIDTH = 32,
    parameter int AXI_DATA_WIDTH = 64,
    parameter int AXI_STRB_WIDTH = AXI_DATA_WIDTH/8
) (
    input  logic                           clk,
    input  logic                           resetn,

    // AXI4 Memory Interface for DRAM
    // Write Address Channel
    output logic [AXI_ID_WIDTH-1:0]        m_axi_awid,
    output logic [AXI_ADDR_WIDTH-1:0]      m_axi_awaddr,
    output logic [7:0]                     m_axi_awlen,
    output logic [2:0]                     m_axi_awsize,
    output logic [1:0]                     m_axi_awburst,
    output logic                           m_axi_awlock,
    output logic [3:0]                     m_axi_awcache,
    output logic [2:0]                     m_axi_awprot,
    output logic [3:0]                     m_axi_awqos,
    output logic                           m_axi_awvalid,
    input  logic                           m_axi_awready,

    // Write Data Channel
    output logic [AXI_DATA_WIDTH-1:0]      m_axi_wdata,
    output logic [AXI_STRB_WIDTH-1:0]      m_axi_wstrb,
    output logic                           m_axi_wlast,
    output logic                           m_axi_wvalid,
    input  logic                           m_axi_wready,

    // Write Response Channel
    input  logic [AXI_ID_WIDTH-1:0]        m_axi_bid,
    input  logic [1:0]                     m_axi_bresp,
    input  logic                           m_axi_bvalid,
    output logic                           m_axi_bready,

    // Read Address Channel
    output logic [AXI_ID_WIDTH-1:0]        m_axi_arid,
    output logic [AXI_ADDR_WIDTH-1:0]      m_axi_araddr,
    output logic [7:0]                     m_axi_arlen,
    output logic [2:0]                     m_axi_arsize,
    output logic [1:0]                     m_axi_arburst,
    output logic                           m_axi_arlock,
    output logic [3:0]                     m_axi_arcache,
    output logic [2:0]                     m_axi_arprot,
    output logic [3:0]                     m_axi_arqos,
    output logic                           m_axi_arvalid,
    input  logic                           m_axi_arready,

    // Read Data Channel
    input  logic [AXI_ID_WIDTH-1:0]        m_axi_rid,
    input  logic [AXI_DATA_WIDTH-1:0]      m_axi_rdata,
    input  logic [1:0]                     m_axi_rresp,
    input  logic                           m_axi_rlast,
    input  logic                           m_axi_rvalid,
    output logic                           m_axi_rready,

    // AXI4-Lite Slave Interface for Control
    input  logic [AXI_ADDR_WIDTH-1:0]      s_axil_awaddr,
    input  logic                           s_axil_awvalid,
    output logic                           s_axil_awready,

    input  logic [31:0]                    s_axil_wdata,
    input  logic [3:0]                     s_axil_wstrb,
    input  logic                           s_axil_wvalid,
    output logic                           s_axil_wready,

    output logic [1:0]                     s_axil_bresp,
    output logic                           s_axil_bvalid,
    input  logic                           s_axil_bready,

    input  logic [AXI_ADDR_WIDTH-1:0]      s_axil_araddr,
    input  logic                           s_axil_arvalid,
    output logic                           s_axil_arready,

    output logic [31:0]                    s_axil_rdata,
    output logic [1:0]                     s_axil_rresp,
    output logic                           s_axil_rvalid,
    input  logic                           s_axil_rready,

    // Interrupt output to host
    output logic                           irq_out,

    // Audio interface signals
    input  logic                           audio_clk,
    input  logic                           audio_rst,

    // I2S interface signals (assumed to be connected to external I2S module)
    output logic [NUM_CORES-1:0]           core_pause,
    output logic [NUM_CORES-1:0]           core_stop,
    output logic [NUM_CORES-1:0]           core_resume,
    input  logic [NUM_CORES-1:0]           core_status,
    input  logic [NUM_CORES-1:0]           core_interrupt
);
    localparam int CORE_ID_WIDTH = $clog2(NUM_CORES);

    // User interface to AXI DRAM
    logic                      user_req;
    logic                      user_rnw;
    logic [AXI_ADDR_WIDTH-1:0] user_addr;
    logic [AXI_DATA_WIDTH-1:0] user_wdata;
    logic [AXI_STRB_WIDTH-1:0] user_wstrb;
    logic [AXI_DATA_WIDTH-1:0] user_rdata;
    logic                      user_ready;

    // Bus interface signals
    logic [NUM_CORES-1:0]      send_req;
    logic [NUM_CORES-1:0]      broadcast_mode;
    logic [NUM_CORES*CORE_ID_WIDTH-1:0] dst_ids;
    logic [NUM_CORES*2-1:0]    instructions;
    logic [NUM_CORES-1:0]      send_grant;
    logic [NUM_CORES-1:0]      recv_valid;
    logic [CORE_ID_WIDTH-1:0]  src_id;
    logic [1:0]                instruction;

    // Address mapping between AXI-Lite and internal modules
    // 0x0000-0x00FF: Interrupt Controller
    // 0x0100-0x01FF: DRAM Control Interface
    // 0x0200-0x02FF: Audio Control Interface

    logic                      int_ctrl_sel;
    logic                      dram_ctrl_sel;
    logic                      audio_ctrl_sel;

    // Address decoding
    always_comb begin
        int_ctrl_sel = (s_axil_awaddr[15:8] == 8'h00) || (s_axil_araddr[15:8] == 8'h00);
        dram_ctrl_sel = (s_axil_awaddr[15:8] == 8'h01) || (s_axil_araddr[15:8] == 8'h01);
        audio_ctrl_sel = (s_axil_awaddr[15:8] == 8'h02) || (s_axil_araddr[15:8] == 8'h02);
    end

    // AXI memory interface for DRAM
    axi_dram_interface #(
        .AXI_ID_WIDTH(AXI_ID_WIDTH),
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
        .AXI_STRB_WIDTH(AXI_STRB_WIDTH),
        .AXI_BURST_LEN(16)
    ) axi_dram_if (
        .clk(clk),
        .resetn(resetn),

        // User Interface
        .user_req(user_req),
        .user_rnw(user_rnw),
        .user_addr(user_addr),
        .user_wdata(user_wdata),
        .user_wstrb(user_wstrb),
        .user_rdata(user_rdata),
        .user_ready(user_ready),

        // AXI Write Address Channel
        .axi_awid(m_axi_awid),
        .axi_awaddr(m_axi_awaddr),
        .axi_awlen(m_axi_awlen),
        .axi_awsize(m_axi_awsize),
        .axi_awburst(m_axi_awburst),
        .axi_awlock(m_axi_awlock),
        .axi_awcache(m_axi_awcache),
        .axi_awprot(m_axi_awprot),
        .axi_awqos(m_axi_awqos),
        .axi_awvalid(m_axi_awvalid),
        .axi_awready(m_axi_awready),

        // AXI Write Data Channel
        .axi_wdata(m_axi_wdata),
        .axi_wstrb(m_axi_wstrb),
        .axi_wlast(m_axi_wlast),
        .axi_wvalid(m_axi_wvalid),
        .axi_wready(m_axi_wready),

        // AXI Write Response Channel
        .axi_bid(m_axi_bid),
        .axi_bresp(m_axi_bresp),
        .axi_bvalid(m_axi_bvalid),
        .axi_bready(m_axi_bready),

        // AXI Read Address Channel
        .axi_arid(m_axi_arid),
        .axi_araddr(m_axi_araddr),
        .axi_arlen(m_axi_arlen),
        .axi_arsize(m_axi_arsize),
        .axi_arburst(m_axi_arburst),
        .axi_arlock(m_axi_arlock),
        .axi_arcache(m_axi_arcache),
        .axi_arprot(m_axi_arprot),
        .axi_arqos(m_axi_arqos),
        .axi_arvalid(m_axi_arvalid),
        .axi_arready(m_axi_arready),

        // AXI Read Data Channel
        .axi_rid(m_axi_rid),
        .axi_rdata(m_axi_rdata),
        .axi_rresp(m_axi_rresp),
        .axi_rlast(m_axi_rlast),
        .axi_rvalid(m_axi_rvalid),
        .axi_rready(m_axi_rready)
    );

    // Interrupt controller
    axi_interrupt_controller #(
        .NUM_CORES(NUM_CORES),
        .NUM_INTERRUPTS(NUM_INTERRUPTS),
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(32)
    ) interrupt_ctrl (
        .clk(clk),
        .resetn(resetn),

        // AXI4-Lite Slave Interface - We only connect this when selected
        .s_axil_awaddr(int_ctrl_sel ? s_axil_awaddr : '0),
        .s_axil_awvalid(int_ctrl_sel ? s_axil_awvalid : 1'b0),
        .s_axil_awready(),  // We'll handle this at the top level

        .s_axil_wdata(int_ctrl_sel ? s_axil_wdata : '0),
        .s_axil_wstrb(int_ctrl_sel ? s_axil_wstrb : '0),
        .s_axil_wvalid(int_ctrl_sel ? s_axil_wvalid : 1'b0),
        .s_axil_wready(),  // We'll handle this at the top level

        .s_axil_bresp(),   // We'll handle this at the top level
        .s_axil_bvalid(),  // We'll handle this at the top level
        .s_axil_bready(int_ctrl_sel ? s_axil_bready : 1'b0),

        .s_axil_araddr(int_ctrl_sel ? s_axil_araddr : '0),
        .s_axil_arvalid(int_ctrl_sel ? s_axil_arvalid : 1'b0),
        .s_axil_arready(),  // We'll handle this at the top level

        .s_axil_rdata(),    // We'll handle this at the top level
        .s_axil_rresp(),    // We'll handle this at the top level
        .s_axil_rvalid(),   // We'll handle this at the top level
        .s_axil_rready(int_ctrl_sel ? s_axil_rready : 1'b0),

        // Interrupt signals
        .core_interrupt(core_interrupt),
        .core_status(core_status),
        .irq_out(irq_out),

        // Control to cores
        .core_pause(core_pause),
        .core_stop(core_stop),
        .core_resume(core_resume),

        // Interface to bus module
        .send_req(send_req),
        .broadcast_mode(broadcast_mode),
        .dst_ids(dst_ids),
        .instructions(instructions),
        .send_grant(send_grant)
    );

    // Bus module for communication between cores
    bus #(
        .NUM_CORES(NUM_CORES),
        .INSTR_WIDTH(2)
    ) bus_module (
        .clk(clk),
        .reset(~resetn),

        // From cores (sending interface)
        .send_req(send_req),
        .broadcast_mode(broadcast_mode),
        .dst_ids(dst_ids),
        .instructions(instructions),
        .send_grant(send_grant),

        // To cores (receiving interface)
        .recv_valid(recv_valid),
        .src_id(src_id),
        .instruction(instruction)
    );

    // Simple AXI-Lite mux for read data and responses
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            s_axil_awready <= 1'b0;
            s_axil_wready <= 1'b0;
            s_axil_bresp <= 2'b00;
            s_axil_bvalid <= 1'b0;
            s_axil_arready <= 1'b0;
            s_axil_rdata <= '0;
            s_axil_rresp <= 2'b00;
            s_axil_rvalid <= 1'b0;
        end else begin
            // Default: acknowledge all requests
            s_axil_awready <= 1'b1;
            s_axil_wready <= 1'b1;
            s_axil_arready <= 1'b1;

            // Handle write responses
            if (s_axil_awvalid && s_axil_wvalid && s_axil_awready && s_axil_wready) begin
                s_axil_bvalid <= 1'b1;
                s_axil_bresp <= 2'b00; // OKAY
            end else if (s_axil_bready && s_axil_bvalid) begin
                s_axil_bvalid <= 1'b0;
            end

            // Handle read responses
            if (s_axil_arvalid && s_axil_arready) begin
                s_axil_rvalid <= 1'b1;

                if (int_ctrl_sel) begin
                    // Forward data from interrupt controller
                    s_axil_rresp <= 2'b00; // OKAY
                end else if (dram_ctrl_sel) begin
                    // Simple DRAM control (status/metrics)
                    s_axil_rresp <= 2'b00; // OKAY
                end else if (audio_ctrl_sel) begin
                    // Audio control interface
                    s_axil_rresp <= 2'b00; // OKAY
                end else begin
                    // Invalid address
                    s_axil_rdata <= 32'h00000000;
                    s_axil_rresp <= 2'b10; // SLVERR
                end
            end else if (s_axil_rready && s_axil_rvalid) begin
                s_axil_rvalid <= 1'b0;
            end
        end
    end

endmodule : llac_top_interface

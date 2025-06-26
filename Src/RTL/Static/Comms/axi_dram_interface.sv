// ------------------------------------------------------------------------
// Filename:       axi_dram_interface.sv
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


module axi_dram_interface #(
    parameter AXI_ID_WIDTH = 6,
    parameter AXI_ADDR_WIDTH = 32,
    parameter AXI_DATA_WIDTH = 64,
    parameter AXI_STRB_WIDTH = AXI_DATA_WIDTH/8,
    parameter AXI_BURST_LEN = 16
) (
    // Clock and Reset
    input  wire                          clk,
    input  wire                          resetn,

    // User Interface
    input  wire                          user_req,
    input  wire                          user_rnw,
    input  wire [AXI_ADDR_WIDTH-1:0]     user_addr,
    input  wire [AXI_DATA_WIDTH-1:0]     user_wdata,
    input  wire [AXI_STRB_WIDTH-1:0]     user_wstrb,
    output reg  [AXI_DATA_WIDTH-1:0]     user_rdata,
    output reg                           user_ready,

    // AXI Write Address Channel
    output reg  [AXI_ID_WIDTH-1:0]       axi_awid,
    output reg  [AXI_ADDR_WIDTH-1:0]     axi_awaddr,
    output reg  [7:0]                    axi_awlen,
    output reg  [2:0]                    axi_awsize,
    output reg  [1:0]                    axi_awburst,
    output reg                           axi_awlock,
    output reg  [3:0]                    axi_awcache,
    output reg  [2:0]                    axi_awprot,
    output reg  [3:0]                    axi_awqos,
    output reg                           axi_awvalid,
    input  wire                          axi_awready,

    // AXI Write Data Channel
    output reg  [AXI_DATA_WIDTH-1:0]     axi_wdata,
    output reg  [AXI_STRB_WIDTH-1:0]     axi_wstrb,
    output reg                           axi_wlast,
    output reg                           axi_wvalid,
    input  wire                          axi_wready,

    // AXI Write Response Channel
    input  wire [AXI_ID_WIDTH-1:0]       axi_bid,
    input  wire [1:0]                    axi_bresp,
    input  wire                          axi_bvalid,
    output reg                           axi_bready,

    // AXI Read Address Channel
    output reg  [AXI_ID_WIDTH-1:0]       axi_arid,
    output reg  [AXI_ADDR_WIDTH-1:0]     axi_araddr,
    output reg  [7:0]                    axi_arlen,
    output reg  [2:0]                    axi_arsize,
    output reg  [1:0]                    axi_arburst,
    output reg                           axi_arlock,
    output reg  [3:0]                    axi_arcache,
    output reg  [2:0]                    axi_arprot,
    output reg  [3:0]                    axi_arqos,
    output reg                           axi_arvalid,
    input  wire                          axi_arready,

    // AXI Read Data Channel
    input  wire [AXI_ID_WIDTH-1:0]       axi_rid,
    input  wire [AXI_DATA_WIDTH-1:0]     axi_rdata,
    input  wire [1:0]                    axi_rresp,
    input  wire                          axi_rlast,
    input  wire                          axi_rvalid,
    output reg                           axi_rready
);

    typedef enum logic [2:0] {
        IDLE,
        WRITE_ADDR,
        WRITE_DATA,
        WRITE_RESP,
        READ_ADDR,
        READ_DATA
    } state_t;

    state_t state, next_state;

    // State machine
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn)
            state <= IDLE;
        else
            state <= next_state;
    end

    // Next state logic
    always_comb begin
        next_state = state;

        case (state)
            IDLE: begin
                if (user_req) begin
                    if (user_rnw)
                        next_state = READ_ADDR;
                    else
                        next_state = WRITE_ADDR;
                end
            end

            WRITE_ADDR: begin
                if (axi_awready && axi_awvalid)
                    next_state = WRITE_DATA;
            end

            WRITE_DATA: begin
                if (axi_wready && axi_wvalid && axi_wlast)
                    next_state = WRITE_RESP;
            end

            WRITE_RESP: begin
                if (axi_bvalid && axi_bready)
                    next_state = IDLE;
            end

            READ_ADDR: begin
                if (axi_arready && axi_arvalid)
                    next_state = READ_DATA;
            end

            READ_DATA: begin
                if (axi_rvalid && axi_rready && axi_rlast)
                    next_state = IDLE;
            end

            default: next_state = IDLE;
        endcase
    end

    // Output logic
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            user_ready <= 1'b0;
            user_rdata <= {AXI_DATA_WIDTH{1'b0}};

            axi_awid <= {AXI_ID_WIDTH{1'b0}};
            axi_awaddr <= {AXI_ADDR_WIDTH{1'b0}};
            axi_awlen <= 8'b0;
            axi_awsize <= 3'b0;
            axi_awburst <= 2'b0;
            axi_awlock <= 1'b0;
            axi_awcache <= 4'b0;
            axi_awprot <= 3'b0;
            axi_awqos <= 4'b0;
            axi_awvalid <= 1'b0;

            axi_wdata <= {AXI_DATA_WIDTH{1'b0}};
            axi_wstrb <= {AXI_STRB_WIDTH{1'b0}};
            axi_wlast <= 1'b0;
            axi_wvalid <= 1'b0;

            axi_bready <= 1'b0;

            axi_arid <= {AXI_ID_WIDTH{1'b0}};
            axi_araddr <= {AXI_ADDR_WIDTH{1'b0}};
            axi_arlen <= 8'b0;
            axi_arsize <= 3'b0;
            axi_arburst <= 2'b0;
            axi_arlock <= 1'b0;
            axi_arcache <= 4'b0;
            axi_arprot <= 3'b0;
            axi_arqos <= 4'b0;
            axi_arvalid <= 1'b0;

            axi_rready <= 1'b0;
        end else begin
            user_ready <= 1'b0;

            axi_awvalid <= 1'b0;
            axi_wvalid <= 1'b0;
            axi_bready <= 1'b0;
            axi_arvalid <= 1'b0;
            axi_rready <= 1'b0;

            case (state)
                IDLE: begin
                    if (user_req) begin
                        if (user_rnw) begin
                            axi_arid <= {AXI_ID_WIDTH{1'b0}};
                            axi_araddr <= user_addr;
                            axi_arlen <= 8'd0;
                            axi_arsize <= $clog2(AXI_STRB_WIDTH);
                            axi_arburst <= 2'b01;
                            axi_arlock <= 1'b0;
                            axi_arcache <= 4'b0011;
                            axi_arprot <= 3'b000;
                            axi_arqos <= 4'b0000;
                            axi_arvalid <= 1'b1;
                        end else begin
                            axi_awid <= {AXI_ID_WIDTH{1'b0}};
                            axi_awaddr <= user_addr;
                            axi_awlen <= 8'd0;
                            axi_awsize <= $clog2(AXI_STRB_WIDTH);
                            axi_awburst <= 2'b01;
                            axi_awlock <= 1'b0;
                            axi_awcache <= 4'b0011;
                            axi_awprot <= 3'b000;
                            axi_awqos <= 4'b0000;
                            axi_awvalid <= 1'b1;

                            axi_wdata <= user_wdata;
                            axi_wstrb <= user_wstrb;
                            axi_wlast <= 1'b1;
                        end
                    end
                end

                WRITE_ADDR: begin
                    axi_awvalid <= 1'b1;
                    if (axi_awready && axi_awvalid) begin
                        axi_wvalid <= 1'b1;
                    end
                end

                WRITE_DATA: begin
                    axi_wvalid <= 1'b1;
                    if (axi_wready && axi_wvalid)
                        axi_bready <= 1'b1;
                end

                WRITE_RESP: begin
                    axi_bready <= 1'b1;
                    if (axi_bvalid && axi_bready) begin
                        user_ready <= 1'b1;
                    end
                end

                READ_ADDR: begin
                    axi_arvalid <= 1'b1;
                    if (axi_arready && axi_arvalid) begin
                        axi_rready <= 1'b1;
                    end
                end

                READ_DATA: begin
                    axi_rready <= 1'b1;
                    if (axi_rvalid && axi_rready) begin
                        user_rdata <= axi_rdata;
                        if (axi_rlast) begin
                            user_ready <= 1'b1;
                        end
                    end
                end
            endcase
        end
    end

endmodule

interface axi_interface #(
    parameter AXI_ID_WIDTH = 6,
    parameter AXI_ADDR_WIDTH = 32,
    parameter AXI_DATA_WIDTH = 64,
    parameter AXI_STRB_WIDTH = AXI_DATA_WIDTH/8
);
    logic [AXI_ID_WIDTH-1:0]    awid;
    logic [AXI_ADDR_WIDTH-1:0]  awaddr;
    logic [7:0]                 awlen;
    logic [2:0]                 awsize;
    logic [1:0]                 awburst;
    logic                       awlock;
    logic [3:0]                 awcache;
    logic [2:0]                 awprot;
    logic [3:0]                 awqos;
    logic                       awvalid;
    logic                       awready;

    logic [AXI_DATA_WIDTH-1:0]  wdata;
    logic [AXI_STRB_WIDTH-1:0]  wstrb;
    logic                       wlast;
    logic                       wvalid;
    logic                       wready;

    logic [AXI_ID_WIDTH-1:0]    bid;
    logic [1:0]                 bresp;
    logic                       bvalid;
    logic                       bready;

    logic [AXI_ID_WIDTH-1:0]    arid;
    logic [AXI_ADDR_WIDTH-1:0]  araddr;
    logic [7:0]                 arlen;
    logic [2:0]                 arsize;
    logic [1:0]                 arburst;
    logic                       arlock;
    logic [3:0]                 arcache;
    logic [2:0]                 arprot;
    logic [3:0]                 arqos;
    logic                       arvalid;
    logic                       arready;

    logic [AXI_ID_WIDTH-1:0]    rid;
    logic [AXI_DATA_WIDTH-1:0]  rdata;
    logic [1:0]                 rresp;
    logic                       rlast;
    logic                       rvalid;
    logic                       rready;

    modport master (
        output awid, awaddr, awlen, awsize, awburst, awlock, awcache, awprot, awqos, awvalid,
        input  awready,
        output wdata, wstrb, wlast, wvalid,
        input  wready,
        input  bid, bresp, bvalid,
        output bready,
        output arid, araddr, arlen, arsize, arburst, arlock, arcache, arprot, arqos, arvalid,
        input  arready,
        input  rid, rdata, rresp, rlast, rvalid,
        output rready
    );

    modport slave (
        input  awid, awaddr, awlen, awsize, awburst, awlock, awcache, awprot, awqos, awvalid,
        output awready,
        input  wdata, wstrb, wlast, wvalid,
        output wready,
        output bid, bresp, bvalid,
        input  bready,
        input  arid, araddr, arlen, arsize, arburst, arlock, arcache, arprot, arqos, arvalid,
        output arready,
        output rid, rdata, rresp, rlast, rvalid,
        input  rready
    );

endinterface

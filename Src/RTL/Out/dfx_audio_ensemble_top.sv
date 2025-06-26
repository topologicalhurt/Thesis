// ------------------------------------------------------------------------
// Filename:       dfx_audio_ensemble_top.sv
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
// It is intended to be used as part of the Out design where a README.md
// detailing the design should exist, conforming to the details provided
// under docs/CONTRIBUTING.md. The Out module is covered by the GPL 3.0
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


`include "Src/RTL/Static/Comms/dfx_controller.svh"

module dfx_audio_ensemble_top #(
    parameter int NUM_CORES = 4,
    parameter int AUDIO_WIDTH = 24,
    parameter int AXI_ADDR_WIDTH = 32,
    parameter int AXI_DATA_WIDTH = 64,
    parameter int AXI_ID_WIDTH = 6,
    parameter bit USE_ICAP = 1      // 1 = Use ICAP, 0 = Use PCAP (Processor Configuration Access Port)
) (
    // Clocks and reset
    input  logic        clk_100mhz,   // 100MHz system clock from PYNQ-Z2
    input  logic        clk_audio,    // Audio clock (typically 24.576MHz for 48kHz)
    input  logic        resetn,       // Active low reset

    // Audio core bus signals
    input logic [NUM_CORES-1:0]       core_pause,
    input logic [NUM_CORES-1:0]       core_stop,
    input logic [NUM_CORES-1:0]       core_resume,
    input logic [NUM_CORES-1:0]       core_status,
    input logic [NUM_CORES-1:0]       core_interrupt,

    // AXI4 memory interface for DRAM
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
    output logic [AXI_DATA_WIDTH/8-1:0]    m_axi_wstrb,
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

    // AXI4-Lite slave interface for control
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

    // Interrupt
    output logic                           irq_out,

    // I2S interface signals
    output logic                           i2s_mclk,      // Master clock (optional)
    output logic                           i2s_bclk,      // Bit clock
    output logic                           i2s_lrclk,     // Left/Right clock (Word Select)
    input  logic                           i2s_sdata_in,  // Serial data input from ADC
    output logic                           i2s_sdata_out, // Serial data output to DAC

    // I2C control interface for codec configuration
    inout  wire                            i2c_scl,
    inout  wire                            i2c_sda,

    // ICAP interface (if USE_ICAP=1)
    output logic                           icap_clk,
    output logic                           icap_ce_n,
    output logic                           icap_write_n,
    output logic [31:0]                    icap_din,
    input  logic [31:0]                    icap_dout,
    input  logic                           icap_busy,

    // PCAP interface signals (if USE_ICAP=0)
    output logic                           pcap_clk,
    output logic                           pcap_csib,
    output logic                           pcap_rdwrb,
    output logic [31:0]                    pcap_din,
    input  logic [31:0]                    pcap_dout,
    input  logic                           pcap_done,

    // Debug/Status LEDs
    output logic [3:0]                     leds
);
    // Local parameters
    localparam int CORE_ID_WIDTH = $clog2(NUM_CORES);

    // Base addresses for AXI-Lite slaves
    localparam int AUDIO_SYS_BASE = 32'h43C0_0000;
    localparam int DFX_CTRL_BASE  = 32'h43C1_0000;

    // DFX controller specific signals
    logic [NUM_CORES-1:0]       rp_decouple;
    logic [NUM_CORES-1:0]       rp_status;
    logic                       dfx_done;
    logic                       dfx_error;
    logic                       dfx_irq;

    // AXI-Lite demultiplexing
    logic                       axil_audio_sel;
    logic                       axil_dfx_sel;

    // Audio system AXI-Lite
    logic [AXI_ADDR_WIDTH-1:0]  audio_axil_awaddr;
    logic                       audio_axil_awvalid;
    logic                       audio_axil_awready;
    logic [31:0]                audio_axil_wdata;
    logic [3:0]                 audio_axil_wstrb;
    logic                       audio_axil_wvalid;
    logic                       audio_axil_wready;
    logic [1:0]                 audio_axil_bresp;
    logic                       audio_axil_bvalid;
    logic                       audio_axil_bready;
    logic [AXI_ADDR_WIDTH-1:0]  audio_axil_araddr;
    logic                       audio_axil_arvalid;
    logic                       audio_axil_arready;
    logic [31:0]                audio_axil_rdata;
    logic [1:0]                 audio_axil_rresp;
    logic                       audio_axil_rvalid;
    logic                       audio_axil_rready;

    // DFX controller AXI-Lite
    logic [AXI_ADDR_WIDTH-1:0]  dfx_axil_awaddr;
    logic                       dfx_axil_awvalid;
    logic                       dfx_axil_awready;
    logic [31:0]                dfx_axil_wdata;
    logic [3:0]                 dfx_axil_wstrb;
    logic                       dfx_axil_wvalid;
    logic                       dfx_axil_wready;
    logic [1:0]                 dfx_axil_bresp;
    logic                       dfx_axil_bvalid;
    logic                       dfx_axil_bready;
    logic [AXI_ADDR_WIDTH-1:0]  dfx_axil_araddr;
    logic                       dfx_axil_arvalid;
    logic                       dfx_axil_arready;
    logic [31:0]                dfx_axil_rdata;
    logic [1:0]                 dfx_axil_rresp;
    logic                       dfx_axil_rvalid;
    logic                       dfx_axil_rready;

    // DFX controller AXI master for memory access
    logic [AXI_ID_WIDTH-1:0]    dfx_axi_awid;
    logic [AXI_ADDR_WIDTH-1:0]  dfx_axi_awaddr;
    logic [7:0]                 dfx_axi_awlen;
    logic [2:0]                 dfx_axi_awsize;
    logic [1:0]                 dfx_axi_awburst;
    logic                       dfx_axi_awlock;
    logic [3:0]                 dfx_axi_awcache;
    logic [2:0]                 dfx_axi_awprot;
    logic [3:0]                 dfx_axi_awqos;
    logic                       dfx_axi_awvalid;
    logic                       dfx_axi_awready;
    logic [AXI_DATA_WIDTH-1:0]  dfx_axi_wdata;
    logic [AXI_DATA_WIDTH/8-1:0] dfx_axi_wstrb;
    logic                       dfx_axi_wlast;
    logic                       dfx_axi_wvalid;
    logic                       dfx_axi_wready;
    logic [AXI_ID_WIDTH-1:0]    dfx_axi_bid;
    logic [1:0]                 dfx_axi_bresp;
    logic                       dfx_axi_bvalid;
    logic                       dfx_axi_bready;
    logic [AXI_ID_WIDTH-1:0]    dfx_axi_arid;
    logic [AXI_ADDR_WIDTH-1:0]  dfx_axi_araddr;
    logic [7:0]                 dfx_axi_arlen;
    logic [2:0]                 dfx_axi_arsize;
    logic [1:0]                 dfx_axi_arburst;
    logic                       dfx_axi_arlock;
    logic [3:0]                 dfx_axi_arcache;
    logic [2:0]                 dfx_axi_arprot;
    logic [3:0]                 dfx_axi_arqos;
    logic                       dfx_axi_arvalid;
    logic                       dfx_axi_arready;
    logic [AXI_ID_WIDTH-1:0]    dfx_axi_rid;
    logic [AXI_DATA_WIDTH-1:0]  dfx_axi_rdata;
    logic [1:0]                 dfx_axi_rresp;
    logic                       dfx_axi_rlast;
    logic                       dfx_axi_rvalid;
    logic                       dfx_axi_rready;

    // Audio system AXI master for memory access
    logic [AXI_ID_WIDTH-1:0]    audio_axi_awid;
    logic [AXI_ADDR_WIDTH-1:0]  audio_axi_awaddr;
    logic [7:0]                 audio_axi_awlen;
    logic [2:0]                 audio_axi_awsize;
    logic [1:0]                 audio_axi_awburst;
    logic                       audio_axi_awlock;
    logic [3:0]                 audio_axi_awcache;
    logic [2:0]                 audio_axi_awprot;
    logic [3:0]                 audio_axi_awqos;
    logic                       audio_axi_awvalid;
    logic                       audio_axi_awready;
    logic [AXI_DATA_WIDTH-1:0]  audio_axi_wdata;
    logic [AXI_DATA_WIDTH/8-1:0] audio_axi_wstrb;
    logic                       audio_axi_wlast;
    logic                       audio_axi_wvalid;
    logic                       audio_axi_wready;
    logic [AXI_ID_WIDTH-1:0]    audio_axi_bid;
    logic [1:0]                 audio_axi_bresp;
    logic                       audio_axi_bvalid;
    logic                       audio_axi_bready;
    logic [AXI_ID_WIDTH-1:0]    audio_axi_arid;
    logic [AXI_ADDR_WIDTH-1:0]  audio_axi_araddr;
    logic [7:0]                 audio_axi_arlen;
    logic [2:0]                 audio_axi_arsize;
    logic [1:0]                 audio_axi_arburst;
    logic                       audio_axi_arlock;
    logic [3:0]                 audio_axi_arcache;
    logic [2:0]                 audio_axi_arprot;
    logic [3:0]                 audio_axi_arqos;
    logic                       audio_axi_arvalid;
    logic                       audio_axi_arready;
    logic [AXI_ID_WIDTH-1:0]    audio_axi_rid;
    logic [AXI_DATA_WIDTH-1:0]  audio_axi_rdata;
    logic [1:0]                 audio_axi_rresp;
    logic                       audio_axi_rlast;
    logic                       audio_axi_rvalid;
    logic                       audio_axi_rready;

    // Audio interrupt
    logic                       audio_irq;

    // LED status indicators
    assign leds = {dfx_error, dfx_done, core_status[1:0]};

    // Address decoding
    always_comb begin
        // Extract base address from AXI-Lite address
        if ((s_axil_awaddr[31:16] == DFX_CTRL_BASE[31:16]) ||
            (s_axil_araddr[31:16] == DFX_CTRL_BASE[31:16])) begin
            axil_dfx_sel = 1'b1;
            axil_audio_sel = 1'b0;
        end else begin
            axil_dfx_sel = 1'b0;
            axil_audio_sel = 1'b1;
        end

        // Connect AXI-Lite signals to appropriate module
        // Audio system AXI-Lite
        audio_axil_awaddr = s_axil_awaddr;
        audio_axil_awvalid = axil_audio_sel ? s_axil_awvalid : 1'b0;
        audio_axil_wdata = s_axil_wdata;
        audio_axil_wstrb = s_axil_wstrb;
        audio_axil_wvalid = axil_audio_sel ? s_axil_wvalid : 1'b0;
        audio_axil_bready = axil_audio_sel ? s_axil_bready : 1'b0;
        audio_axil_araddr = s_axil_araddr;
        audio_axil_arvalid = axil_audio_sel ? s_axil_arvalid : 1'b0;
        audio_axil_rready = axil_audio_sel ? s_axil_rready : 1'b0;

        // DFX controller AXI-Lite
        dfx_axil_awaddr = s_axil_awaddr;
        dfx_axil_awvalid = axil_dfx_sel ? s_axil_awvalid : 1'b0;
        dfx_axil_wdata = s_axil_wdata;
        dfx_axil_wstrb = s_axil_wstrb;
        dfx_axil_wvalid = axil_dfx_sel ? s_axil_wvalid : 1'b0;
        dfx_axil_bready = axil_dfx_sel ? s_axil_bready : 1'b0;
        dfx_axil_araddr = s_axil_araddr;
        dfx_axil_arvalid = axil_dfx_sel ? s_axil_arvalid : 1'b0;
        dfx_axil_rready = axil_dfx_sel ? s_axil_rready : 1'b0;
    end

    // AXI-Lite response mux
    always_comb begin
        if (axil_audio_sel) begin
            s_axil_awready = audio_axil_awready;
            s_axil_wready = audio_axil_wready;
            s_axil_bresp = audio_axil_bresp;
            s_axil_bvalid = audio_axil_bvalid;
            s_axil_arready = audio_axil_arready;
            s_axil_rdata = audio_axil_rdata;
            s_axil_rresp = audio_axil_rresp;
            s_axil_rvalid = audio_axil_rvalid;
        end else begin
            s_axil_awready = dfx_axil_awready;
            s_axil_wready = dfx_axil_wready;
            s_axil_bresp = dfx_axil_bresp;
            s_axil_bvalid = dfx_axil_bvalid;
            s_axil_arready = dfx_axil_arready;
            s_axil_rdata = dfx_axil_rdata;
            s_axil_rresp = dfx_axil_rresp;
            s_axil_rvalid = dfx_axil_rvalid;
        end
    end

    // AXI master arbitration (simple priority-based)
    // DFX controller has higher priority
    always_comb begin
        // Default assignments
        // Connect DFX controller to AXI by default
        m_axi_awid = dfx_axi_awid;
        m_axi_awaddr = dfx_axi_awaddr;
        m_axi_awlen = dfx_axi_awlen;
        m_axi_awsize = dfx_axi_awsize;
        m_axi_awburst = dfx_axi_awburst;
        m_axi_awlock = dfx_axi_awlock;
        m_axi_awcache = dfx_axi_awcache;
        m_axi_awprot = dfx_axi_awprot;
        m_axi_awqos = dfx_axi_awqos;
        m_axi_awvalid = dfx_axi_awvalid;
        dfx_axi_awready = m_axi_awready;
        audio_axi_awready = 1'b0;

        m_axi_wdata = dfx_axi_wdata;
        m_axi_wstrb = dfx_axi_wstrb;
        m_axi_wlast = dfx_axi_wlast;
        m_axi_wvalid = dfx_axi_wvalid;
        dfx_axi_wready = m_axi_wready;
        audio_axi_wready = 1'b0;

        dfx_axi_bid = m_axi_bid;
        dfx_axi_bresp = m_axi_bresp;
        dfx_axi_bvalid = m_axi_bvalid;
        audio_axi_bvalid = 1'b0;
        audio_axi_bid = '0;
        audio_axi_bresp = 2'b00;
        m_axi_bready = dfx_axi_bready;

        m_axi_arid = dfx_axi_arid;
        m_axi_araddr = dfx_axi_araddr;
        m_axi_arlen = dfx_axi_arlen;
        m_axi_arsize = dfx_axi_arsize;
        m_axi_arburst = dfx_axi_arburst;
        m_axi_arlock = dfx_axi_arlock;
        m_axi_arcache = dfx_axi_arcache;
        m_axi_arprot = dfx_axi_arprot;
        m_axi_arqos = dfx_axi_arqos;
        m_axi_arvalid = dfx_axi_arvalid;
        dfx_axi_arready = m_axi_arready;
        audio_axi_arready = 1'b0;

        dfx_axi_rid = m_axi_rid;
        dfx_axi_rdata = m_axi_rdata;
        dfx_axi_rresp = m_axi_rresp;
        dfx_axi_rlast = m_axi_rlast;
        dfx_axi_rvalid = m_axi_rvalid;
        audio_axi_rvalid = 1'b0;
        audio_axi_rid = '0;
        audio_axi_rdata = '0;
        audio_axi_rresp = 2'b00;
        audio_axi_rlast = 1'b0;
        m_axi_rready = dfx_axi_rready;

        // If DFX controller isn't using AXI, give access to audio system
        if (!dfx_axi_awvalid && !dfx_axi_arvalid) begin
            // Only switch if DFX isn't in the middle of a transaction
            if (!m_axi_awvalid && !m_axi_arvalid) begin
                m_axi_awid = audio_axi_awid;
                m_axi_awaddr = audio_axi_awaddr;
                m_axi_awlen = audio_axi_awlen;
                m_axi_awsize = audio_axi_awsize;
                m_axi_awburst = audio_axi_awburst;
                m_axi_awlock = audio_axi_awlock;
                m_axi_awcache = audio_axi_awcache;
                m_axi_awprot = audio_axi_awprot;
                m_axi_awqos = audio_axi_awqos;
                m_axi_awvalid = audio_axi_awvalid;
                audio_axi_awready = m_axi_awready;
                dfx_axi_awready = 1'b0;

                m_axi_wdata = audio_axi_wdata;
                m_axi_wstrb = audio_axi_wstrb;
                m_axi_wlast = audio_axi_wlast;
                m_axi_wvalid = audio_axi_wvalid;
                audio_axi_wready = m_axi_wready;
                dfx_axi_wready = 1'b0;

                audio_axi_bid = m_axi_bid;
                audio_axi_bresp = m_axi_bresp;
                audio_axi_bvalid = m_axi_bvalid;
                dfx_axi_bvalid = 1'b0;
                dfx_axi_bid = '0;
                dfx_axi_bresp = 2'b00;
                m_axi_bready = audio_axi_bready;

                m_axi_arid = audio_axi_arid;
                m_axi_araddr = audio_axi_araddr;
                m_axi_arlen = audio_axi_arlen;
                m_axi_arsize = audio_axi_arsize;
                m_axi_arburst = audio_axi_arburst;
                m_axi_arlock = audio_axi_arlock;
                m_axi_arcache = audio_axi_arcache;
                m_axi_arprot = audio_axi_arprot;
                m_axi_arqos = audio_axi_arqos;
                m_axi_arvalid = audio_axi_arvalid;
                audio_axi_arready = m_axi_arready;
                dfx_axi_arready = 1'b0;

                audio_axi_rid = m_axi_rid;
                audio_axi_rdata = m_axi_rdata;
                audio_axi_rresp = m_axi_rresp;
                audio_axi_rlast = m_axi_rlast;
                audio_axi_rvalid = m_axi_rvalid;
                dfx_axi_rvalid = 1'b0;
                dfx_axi_rid = '0;
                dfx_axi_rdata = '0;
                dfx_axi_rresp = 2'b00;
                dfx_axi_rlast = 1'b0;
                m_axi_rready = audio_axi_rready;
            end
        end
    end

    // Interrupt combination
    assign irq_out = audio_irq | dfx_irq;

    // Instantiate the audio system
    llac_audio_system_top #(
        .NUM_CORES(NUM_CORES),
        .AUDIO_WIDTH(AUDIO_WIDTH),
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
        .AXI_ID_WIDTH(AXI_ID_WIDTH)
    ) audio_system (
        // Clocks and reset
        .clk_100mhz(clk_100mhz),
        .clk_audio(clk_audio),
        .resetn(resetn),

        // AXI4 memory interface
        .m_axi_awid(audio_axi_awid),
        .m_axi_awaddr(audio_axi_awaddr),
        .m_axi_awlen(audio_axi_awlen),
        .m_axi_awsize(audio_axi_awsize),
        .m_axi_awburst(audio_axi_awburst),
        .m_axi_awlock(audio_axi_awlock),
        .m_axi_awcache(audio_axi_awcache),
        .m_axi_awprot(audio_axi_awprot),
        .m_axi_awqos(audio_axi_awqos),
        .m_axi_awvalid(audio_axi_awvalid),
        .m_axi_awready(audio_axi_awready),

        .m_axi_wdata(audio_axi_wdata),
        .m_axi_wstrb(audio_axi_wstrb),
        .m_axi_wlast(audio_axi_wlast),
        .m_axi_wvalid(audio_axi_wvalid),
        .m_axi_wready(audio_axi_wready),

        .m_axi_bid(audio_axi_bid),
        .m_axi_bresp(audio_axi_bresp),
        .m_axi_bvalid(audio_axi_bvalid),
        .m_axi_bready(audio_axi_bready),

        .m_axi_arid(audio_axi_arid),
        .m_axi_araddr(audio_axi_araddr),
        .m_axi_arlen(audio_axi_arlen),
        .m_axi_arsize(audio_axi_arsize),
        .m_axi_arburst(audio_axi_arburst),
        .m_axi_arlock(audio_axi_arlock),
        .m_axi_arcache(audio_axi_arcache),
        .m_axi_arprot(audio_axi_arprot),
        .m_axi_arqos(audio_axi_arqos),
        .m_axi_arvalid(audio_axi_arvalid),
        .m_axi_arready(audio_axi_arready),

        .m_axi_rid(audio_axi_rid),
        .m_axi_rdata(audio_axi_rdata),
        .m_axi_rresp(audio_axi_rresp),
        .m_axi_rlast(audio_axi_rlast),
        .m_axi_rvalid(audio_axi_rvalid),
        .m_axi_rready(audio_axi_rready),

        // AXI4-Lite slave interface
        .s_axil_awaddr(audio_axil_awaddr),
        .s_axil_awvalid(audio_axil_awvalid),
        .s_axil_awready(audio_axil_awready),

        .s_axil_wdata(audio_axil_wdata),
        .s_axil_wstrb(audio_axil_wstrb),
        .s_axil_wvalid(audio_axil_wvalid),
        .s_axil_wready(audio_axil_wready),

        .s_axil_bresp(audio_axil_bresp),
        .s_axil_bvalid(audio_axil_bvalid),
        .s_axil_bready(audio_axil_bready),

        .s_axil_araddr(audio_axil_araddr),
        .s_axil_arvalid(audio_axil_arvalid),
        .s_axil_arready(audio_axil_arready),

        .s_axil_rdata(audio_axil_rdata),
        .s_axil_rresp(audio_axil_rresp),
        .s_axil_rvalid(audio_axil_rvalid),
        .s_axil_rready(audio_axil_rready),

        // Interrupt
        .irq_out(audio_irq),

        // I2S interface signals
        .i2s_mclk(i2s_mclk),
        .i2s_bclk(i2s_bclk),
        .i2s_lrclk(i2s_lrclk),
        .i2s_sdata_in(i2s_sdata_in),
        .i2s_sdata_out(i2s_sdata_out),

        // I2C control interface
        .i2c_scl(i2c_scl),
        .i2c_sda(i2c_sda),

        // Core control signals - connect to DFX controller
        .core_pause(core_pause),
        .core_stop(core_stop),
        .core_resume(core_resume),
        .core_status(core_status),
        .core_interrupt(core_interrupt),

        // Debug LEDs handled at top level
        .leds()
    );

    // Instantiate the DFX controller
    dfx_controller #(
        .NUM_RPS(NUM_CORES),
        .AXI_ADDR_WIDTH(AXI_ADDR_WIDTH),
        .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
        .AXI_ID_WIDTH(AXI_ID_WIDTH),
        .MAX_BITSTREAM_SIZE(1024*1024), // 1MB
        .USE_ICAP(USE_ICAP),
        .SECURE_LOAD(0),
        .TIMEOUT_CYCLES(1000000)
    ) dfx_ctrl (
        // Clock and reset
        .clk(clk_100mhz),
        .resetn(resetn),

        // AXI4-Lite slave interface
        .s_axil_awaddr(dfx_axil_awaddr),
        .s_axil_awvalid(dfx_axil_awvalid),
        .s_axil_awready(dfx_axil_awready),

        .s_axil_wdata(dfx_axil_wdata),
        .s_axil_wstrb(dfx_axil_wstrb),
        .s_axil_wvalid(dfx_axil_wvalid),
        .s_axil_wready(dfx_axil_wready),

        .s_axil_bresp(dfx_axil_bresp),
        .s_axil_bvalid(dfx_axil_bvalid),
        .s_axil_bready(dfx_axil_bready),

        .s_axil_araddr(dfx_axil_araddr),
        .s_axil_arvalid(dfx_axil_arvalid),
        .s_axil_arready(dfx_axil_arready),

        .s_axil_rdata(dfx_axil_rdata),
        .s_axil_rresp(dfx_axil_rresp),
        .s_axil_rvalid(dfx_axil_rvalid),
        .s_axil_rready(dfx_axil_rready),

        // AXI4 master interface for memory access
        .m_axi_awid(dfx_axi_awid),
        .m_axi_awaddr(dfx_axi_awaddr),
        .m_axi_awlen(dfx_axi_awlen),
        .m_axi_awsize(dfx_axi_awsize),
        .m_axi_awburst(dfx_axi_awburst),
        .m_axi_awlock(dfx_axi_awlock),
        .m_axi_awcache(dfx_axi_awcache),
        .m_axi_awprot(dfx_axi_awprot),
        .m_axi_awqos(dfx_axi_awqos),
        .m_axi_awvalid(dfx_axi_awvalid),
        .m_axi_awready(dfx_axi_awready),

        .m_axi_wdata(dfx_axi_wdata),
        .m_axi_wstrb(dfx_axi_wstrb),
        .m_axi_wlast(dfx_axi_wlast),
        .m_axi_wvalid(dfx_axi_wvalid),
        .m_axi_wready(dfx_axi_wready),

        .m_axi_bid(dfx_axi_bid),
        .m_axi_bresp(dfx_axi_bresp),
        .m_axi_bvalid(dfx_axi_bvalid),
        .m_axi_bready(dfx_axi_bready),

        .m_axi_arid(dfx_axi_arid),
        .m_axi_araddr(dfx_axi_araddr),
        .m_axi_arlen(dfx_axi_arlen),
        .m_axi_arsize(dfx_axi_arsize),
        .m_axi_arburst(dfx_axi_arburst),
        .m_axi_arlock(dfx_axi_arlock),
        .m_axi_arcache(dfx_axi_arcache),
        .m_axi_arprot(dfx_axi_arprot),
        .m_axi_arqos(dfx_axi_arqos),
        .m_axi_arvalid(dfx_axi_arvalid),
        .m_axi_arready(dfx_axi_arready),

        .m_axi_rid(dfx_axi_rid),
        .m_axi_rdata(dfx_axi_rdata),
        .m_axi_rresp(dfx_axi_rresp),
        .m_axi_rlast(dfx_axi_rlast),
        .m_axi_rvalid(dfx_axi_rvalid),
        .m_axi_rready(dfx_axi_rready),

        // Core control interface
        .core_status(core_status),
        .core_pause(core_pause),
        .core_stop(core_stop),
        .core_resume(core_resume),
        .core_interrupt(core_interrupt),

        // ICAP interface
        .icap_clk(icap_clk),
        .icap_ce_n(icap_ce_n),
        .icap_write_n(icap_write_n),
        .icap_din(icap_din),
        .icap_dout(icap_dout),
        .icap_busy(icap_busy),

        // PCAP interface
        .pcap_clk(pcap_clk),
        .pcap_csib(pcap_csib),
        .pcap_rdwrb(pcap_rdwrb),
        .pcap_din(pcap_din),
        .pcap_dout(pcap_dout),
        .pcap_done(pcap_done),

        // Decouple signals for each RP
        .rp_decouple(rp_decouple),

        // Status and interrupts
        .rp_status(rp_status),
        .dfx_done(dfx_done),
        .dfx_error(dfx_error),
        .irq_out(dfx_irq)
    );

endmodule

// ------------------------------------------------------------------------
// Filename:       dfx_controller.sv
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


`include "Src/RTL/Static/Comms/dfx_controller.svh"

module dfx_controller #(
    parameter int NUM_RPS = 4,                // Number of reconfigurable partitions
    parameter int AXI_ADDR_WIDTH = 32,        // AXI address width
    parameter int AXI_DATA_WIDTH = 32,        // AXI data width
    parameter int AXI_ID_WIDTH = 6,           // AXI ID width
    parameter int MAX_BITSTREAM_SIZE = 1024*1024, // Max bitstream size in bytes
    parameter bit USE_ICAP = 1,               // 1 = Use ICAP, 0 = Use PCAP
    parameter bit SECURE_LOAD = 0,            // Enable additional security features
    parameter int TIMEOUT_CYCLES = 1000000    // Default timeout cycles
) (
    // Clock and reset
    input  logic                          clk,
    input  logic                          resetn,

    // AXI4-Lite slave interface for control
    input  logic [AXI_ADDR_WIDTH-1:0]     s_axil_awaddr,
    input  logic                          s_axil_awvalid,
    output logic                          s_axil_awready,

    input  logic [AXI_DATA_WIDTH-1:0]     s_axil_wdata,
    input  logic [AXI_DATA_WIDTH/8-1:0]   s_axil_wstrb,
    input  logic                          s_axil_wvalid,
    output logic                          s_axil_wready,

    output logic [1:0]                    s_axil_bresp,
    output logic                          s_axil_bvalid,
    input  logic                          s_axil_bready,

    input  logic [AXI_ADDR_WIDTH-1:0]     s_axil_araddr,
    input  logic                          s_axil_arvalid,
    output logic                          s_axil_arready,

    output logic [AXI_DATA_WIDTH-1:0]     s_axil_rdata,
    output logic [1:0]                    s_axil_rresp,
    output logic                          s_axil_rvalid,
    input  logic                          s_axil_rready,

    // AXI4 master interface for memory access
    // Write Address Channel
    output logic [AXI_ID_WIDTH-1:0]       m_axi_awid,
    output logic [AXI_ADDR_WIDTH-1:0]     m_axi_awaddr,
    output logic [7:0]                    m_axi_awlen,
    output logic [2:0]                    m_axi_awsize,
    output logic [1:0]                    m_axi_awburst,
    output logic                          m_axi_awlock,
    output logic [3:0]                    m_axi_awcache,
    output logic [2:0]                    m_axi_awprot,
    output logic [3:0]                    m_axi_awqos,
    output logic                          m_axi_awvalid,
    input  logic                          m_axi_awready,

    // Write Data Channel
    output logic [AXI_DATA_WIDTH-1:0]     m_axi_wdata,
    output logic [AXI_DATA_WIDTH/8-1:0]   m_axi_wstrb,
    output logic                          m_axi_wlast,
    output logic                          m_axi_wvalid,
    input  logic                          m_axi_wready,

    // Write Response Channel
    input  logic [AXI_ID_WIDTH-1:0]       m_axi_bid,
    input  logic [1:0]                    m_axi_bresp,
    input  logic                          m_axi_bvalid,
    output logic                          m_axi_bready,

    // Read Address Channel
    output logic [AXI_ID_WIDTH-1:0]       m_axi_arid,
    output logic [AXI_ADDR_WIDTH-1:0]     m_axi_araddr,
    output logic [7:0]                    m_axi_arlen,
    output logic [2:0]                    m_axi_arsize,
    output logic [1:0]                    m_axi_arburst,
    output logic                          m_axi_arlock,
    output logic [3:0]                    m_axi_arcache,
    output logic [2:0]                    m_axi_arprot,
    output logic [3:0]                    m_axi_arqos,
    output logic                          m_axi_arvalid,
    input  logic                          m_axi_arready,

    // Read Data Channel
    input  logic [AXI_ID_WIDTH-1:0]       m_axi_rid,
    input  logic [AXI_DATA_WIDTH-1:0]     m_axi_rdata,
    input  logic [1:0]                    m_axi_rresp,
    input  logic                          m_axi_rlast,
    input  logic                          m_axi_rvalid,
    output logic                          m_axi_rready,

    // Core control interface
    input  logic [NUM_RPS-1:0]            core_status,        // Status of cores
    output logic [NUM_RPS-1:0]            core_pause,         // Signal to pause cores
    output logic [NUM_RPS-1:0]            core_stop,          // Signal to stop cores
    output logic [NUM_RPS-1:0]            core_resume,        // Signal to resume cores
    input  logic [NUM_RPS-1:0]            core_interrupt,     // Interrupts from cores

    // ICAP interface (if USE_ICAP=1)
    output logic                          icap_clk,
    output logic                          icap_ce_n,
    output logic                          icap_write_n,
    output logic [31:0]                   icap_din,
    input  logic [31:0]                   icap_dout,
    input  logic                          icap_busy,

    // PCAP interface signals (if USE_ICAP=0)
    output logic                          pcap_clk,
    output logic                          pcap_csib,
    output logic                          pcap_rdwrb,
    output logic [31:0]                   pcap_din,
    input  logic [31:0]                   pcap_dout,
    input  logic                          pcap_done,

    // Decouple signals (one per reconfigurable partition)
    output logic [NUM_RPS-1:0]            rp_decouple,        // Signal to decouple RP

    // Status and interrupts
    output logic [NUM_RPS-1:0]            rp_status,          // Status of RPs
    output logic                          dfx_done,           // DFX operation complete
    output logic                          dfx_error,          // DFX error occurred
    output logic                          irq_out             // Interrupt to host
);

    // Local parameter definitions
    localparam int RP_ID_WIDTH = $clog2(NUM_RPS);
    localparam int NUM_REGS = 16;  // Number of control registers

    // Register definitions
    logic [AXI_DATA_WIDTH-1:0] regs[NUM_REGS];
    logic [AXI_DATA_WIDTH-1:0] reg_next[NUM_REGS];

    // DFX controller state
    dfx_state_t dfx_state, dfx_next_state;
    dfx_error_t dfx_err_code;

    // RP selection and configuration
    logic [RP_ID_WIDTH-1:0]    selected_rp;
    logic [31:0]               current_bs_id;
    logic [63:0]               bs_addr;
    logic [31:0]               bs_size;
    logic [31:0]               timeout_counter;
    logic [31:0]               progress_counter;
    logic [31:0]               configured_bitstreams[NUM_RPS];

    // Interrupt tracking
    logic                     int_done_status;
    logic                     int_error_status;
    logic                     int_timeout_status;
    logic                     int_progress_status;
    logic                     int_done_enable;
    logic                     int_error_enable;
    logic                     int_timeout_enable;
    logic                     int_progress_enable;

    // Memory access state machine
    typedef enum logic [2:0] {
        MEM_IDLE,
        MEM_ADDR,
        MEM_DATA,
        MEM_RESP,
        MEM_DONE
    } mem_state_t;
    mem_state_t mem_state, mem_next_state;

    // Configuration access state machine
    typedef enum logic [2:0] {
        CFG_IDLE,
        CFG_INIT,
        CFG_SYNC,
        CFG_WRITE,
        CFG_DESYNC,
        CFG_DONE
    } cfg_state_t;
    cfg_state_t cfg_state, cfg_next_state;

    // Buffer for bitstream data
    logic [31:0]              bitstream_buffer[32];  // Small buffer for streaming
    logic [5:0]               buf_read_ptr;
    logic [5:0]               buf_write_ptr;
    logic                     buf_empty;
    logic                     buf_full;

    // AXI4-Lite interface logic
    logic                     write_en;
    logic [3:0]               waddr;
    logic                     read_en;
    logic [3:0]               raddr;

    // Command processing
    logic                     cmd_start;
    logic                     cmd_abort;
    dfx_cmd_t                 cmd_type;

    // ICAP/PCAP control
    logic                     cfg_active;
    logic [31:0]              cfg_word_counter;
    logic [31:0]              cfg_data;
    logic                     cfg_write_en;
    logic                     cfg_port_ready;

    // Address decoding
    always_comb begin
        write_en = s_axil_awvalid && s_axil_wvalid && s_axil_awready && s_axil_wready;
        waddr = s_axil_awaddr[5:2]; // Word-aligned addressing

        read_en = s_axil_arvalid && s_axil_arready;
        raddr = s_axil_araddr[5:2]; // Word-aligned addressing
    end

    // State control and main state machine
    always_ff @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            dfx_state <= DFX_STATE_IDLE;
            mem_state <= MEM_IDLE;
            cfg_state <= CFG_IDLE;

            // Reset all registers
            for (int i = 0; i < NUM_REGS; i++) begin
                regs[i] <= '0;
            end

            selected_rp <= '0;
            current_bs_id <= '0;
            bs_addr <= '0;
            bs_size <= '0;
            timeout_counter <= TIMEOUT_CYCLES;
            progress_counter <= '0;

            // Reset interrupt status
            int_done_status <= 1'b0;
            int_error_status <= 1'b0;
            int_timeout_status <= 1'b0;
            int_progress_status <= 1'b0;
            int_done_enable <= 1'b0;
            int_error_enable <= 1'b0;
            int_timeout_enable <= 1'b0;
            int_progress_enable <= 1'b0;

            // Reset buffer pointers
            buf_read_ptr <= '0;
            buf_write_ptr <= '0;

            // Reset AXI-Lite interface
            s_axil_awready <= 1'b0;
            s_axil_wready <= 1'b0;
            s_axil_bresp <= 2'b00;
            s_axil_bvalid <= 1'b0;
            s_axil_arready <= 1'b0;
            s_axil_rdata <= '0;
            s_axil_rresp <= 2'b00;
            s_axil_rvalid <= 1'b0;

            // Reset AXI master interface
            m_axi_awid <= '0;
            m_axi_awaddr <= '0;
            m_axi_awlen <= '0;
            m_axi_awsize <= '0;
            m_axi_awburst <= '0;
            m_axi_awlock <= '0;
            m_axi_awcache <= '0;
            m_axi_awprot <= '0;
            m_axi_awqos <= '0;
            m_axi_awvalid <= 1'b0;
            m_axi_wdata <= '0;
            m_axi_wstrb <= '0;
            m_axi_wlast <= 1'b0;
            m_axi_wvalid <= 1'b0;
            m_axi_bready <= 1'b0;
            m_axi_arid <= '0;
            m_axi_araddr <= '0;
            m_axi_arlen <= '0;
            m_axi_arsize <= '0;
            m_axi_arburst <= '0;
            m_axi_arlock <= '0;
            m_axi_arcache <= '0;
            m_axi_arprot <= '0;
            m_axi_arqos <= '0;
            m_axi_arvalid <= 1'b0;
            m_axi_rready <= 1'b0;

            // Reset core control
            core_pause <= '0;
            core_stop <= '0;
            core_resume <= '0;
            rp_decouple <= '0;
            rp_status <= '0;

            // Reset ICAP/PCAP
            if (USE_ICAP) begin
                icap_clk <= 1'b0;
                icap_ce_n <= 1'b1;
                icap_write_n <= 1'b1;
                icap_din <= '0;
            end else begin
                pcap_clk <= 1'b0;
                pcap_csib <= 1'b1;
                pcap_rdwrb <= 1'b1;
                pcap_din <= '0;
            end

            // Reset configuration access
            cfg_active <= 1'b0;
            cfg_word_counter <= '0;
            cfg_data <= '0;
            cfg_write_en <= 1'b0;

            // Reset status outputs
            dfx_done <= 1'b0;
            dfx_error <= 1'b0;
            irq_out <= 1'b0;

            // Initialize bitstream tracking
            for (int i = 0; i < NUM_RPS; i++) begin
                configured_bitstreams[i] <= '0;
            end

            dfx_err_code <= DFX_ERR_NONE;
        end else begin
            // Default next state
            dfx_state <= dfx_next_state;
            mem_state <= mem_next_state;
            cfg_state <= cfg_next_state;

            // Handle AXI4-Lite interface
            s_axil_awready <= 1'b1;
            s_axil_wready <= 1'b1;

            if (write_en) begin
                // Process write
                if (waddr < NUM_REGS) begin
                    for (int i = 0; i < AXI_DATA_WIDTH/8; i++) begin
                        if (s_axil_wstrb[i]) begin
                            regs[waddr][i*8 +: 8] <= s_axil_wdata[i*8 +: 8];
                        end
                    end

                    // Handle special registers
                    case (waddr)
                        DFX_REG_CTRL: begin
                            // Extract command
                            cmd_type <= dfx_cmd_t'(s_axil_wdata[DFX_CTRL_CMD_SHIFT +: 4]);

                            // Handle self-clearing bits
                            if (s_axil_wdata[DFX_CTRL_START_BIT]) begin
                                cmd_start <= 1'b1;
                            end

                            if (s_axil_wdata[DFX_CTRL_ABORT_BIT]) begin
                                cmd_abort <= 1'b1;
                            end

                            if (s_axil_wdata[DFX_CTRL_CLR_ERR_BIT]) begin
                                dfx_err_code <= DFX_ERR_NONE;
                                dfx_error <= 1'b0;
                                int_error_status <= 1'b0;
                            end

                            if (s_axil_wdata[DFX_CTRL_SELF_TEST_BIT]) begin
                                // Self-test would be implemented here
                            end

                            if (s_axil_wdata[DFX_CTRL_SW_RESET_BIT]) begin
                                // Perform soft reset
                                dfx_state <= DFX_STATE_IDLE;
                                mem_state <= MEM_IDLE;
                                cfg_state <= CFG_IDLE;
                                dfx_err_code <= DFX_ERR_NONE;
                                core_pause <= '0;
                                core_stop <= '0;
                                core_resume <= '0;
                                rp_decouple <= '0;
                                cfg_active <= 1'b0;
                            end
                        end

                        DFX_REG_RP_SELECT: begin
                            selected_rp <= s_axil_wdata[RP_ID_WIDTH-1:0];
                        end

                        DFX_REG_BS_ADDR_LOW: begin
                            bs_addr[31:0] <= s_axil_wdata;
                        end

                        DFX_REG_BS_ADDR_HIGH: begin
                            bs_addr[63:32] <= s_axil_wdata;
                        end

                        DFX_REG_BS_SIZE: begin
                            bs_size <= s_axil_wdata;
                        end

                        DFX_REG_BS_ID: begin
                            current_bs_id <= s_axil_wdata;
                        end

                        DFX_REG_TIMEOUT: begin
                            timeout_counter <= s_axil_wdata;
                        end

                        DFX_REG_INT_ENABLE: begin
                            int_done_enable <= s_axil_wdata[DFX_INT_DONE_BIT];
                            int_error_enable <= s_axil_wdata[DFX_INT_ERROR_BIT];
                            int_timeout_enable <= s_axil_wdata[DFX_INT_TIMEOUT_BIT];
                            int_progress_enable <= s_axil_wdata[DFX_INT_PROGRESS_BIT];
                        end

                        DFX_REG_INT_STATUS: begin
                            // Clear interrupt status bits that are written with 1
                            if (s_axil_wdata[DFX_INT_DONE_BIT])
                                int_done_status <= 1'b0;
                            if (s_axil_wdata[DFX_INT_ERROR_BIT])
                                int_error_status <= 1'b0;
                            if (s_axil_wdata[DFX_INT_TIMEOUT_BIT])
                                int_timeout_status <= 1'b0;
                            if (s_axil_wdata[DFX_INT_PROGRESS_BIT])
                                int_progress_status <= 1'b0;
                        end

                        default: begin
                            // Other registers handled directly
                        end
                    endcase
                end

                // Generate write response
                s_axil_bvalid <= 1'b1;
                s_axil_bresp <= 2'b00; // OKAY
            end else if (s_axil_bvalid && s_axil_bready) begin
                s_axil_bvalid <= 1'b0;
            end

            // Handle AXI4-Lite read interface
            s_axil_arready <= 1'b1;

            if (read_en) begin
                s_axil_rvalid <= 1'b1;
                s_axil_rresp <= 2'b00; // OKAY

                if (raddr < NUM_REGS) begin
                    // Handle register reads
                    case (raddr)
                        DFX_REG_STATUS: begin
                            s_axil_rdata <= {
                                24'b0,
                                dfx_state,
                                1'b0,                   // Reserved
                                dfx_error,              // Error bit
                                dfx_done,               // Done bit
                                (dfx_state != DFX_STATE_IDLE) // Busy bit
                            };
                        end

                        DFX_REG_ERROR: begin
                            s_axil_rdata <= {28'b0, dfx_err_code};
                        end

                        DFX_REG_CONFIG_ID: begin
                            s_axil_rdata <= configured_bitstreams[selected_rp];
                        end

                        DFX_REG_PROGRESS: begin
                            s_axil_rdata <= progress_counter;
                        end

                        DFX_REG_INT_STATUS: begin
                            s_axil_rdata <= {
                                28'b0,
                                int_progress_status,
                                int_timeout_status,
                                int_error_status,
                                int_done_status
                            };
                        end

                        DFX_REG_RP_STATUS: begin
                            s_axil_rdata <= {
                                {(32-NUM_RPS){1'b0}},
                                rp_status
                            };
                        end

                        DFX_REG_VERSION: begin
                            s_axil_rdata <= 32'h00010000; // Version 1.0.0
                        end

                        default: begin
                            // Return directly from register array
                            s_axil_rdata <= regs[raddr];
                        end
                    endcase
                end else begin
                    s_axil_rdata <= 32'h00000000;
                    s_axil_rresp <= 2'b10; // SLVERR
                end
            end else if (s_axil_rvalid && s_axil_rready) begin
                s_axil_rvalid <= 1'b0;
            end

            // Handle command start and abort - default clear after one cycle
            if (cmd_start) cmd_start <= 1'b0;
            if (cmd_abort) cmd_abort <= 1'b0;

            // Main DFX state machine
            case (dfx_state)
                DFX_STATE_IDLE: begin
                    // Reset status indicators
                    dfx_done <= 1'b0;
                    progress_counter <= '0;

                    // Check for commands
                    if (cmd_start) begin
                        case (cmd_type)
                            DFX_CMD_LOAD: begin
                                if (selected_rp < NUM_RPS) begin
                                    dfx_next_state <= DFX_STATE_INIT;
                                end else begin
                                    dfx_err_code <= DFX_ERR_INVALID_RP;
                                    dfx_error <= 1'b1;
                                    int_error_status <= 1'b1;
                                    dfx_next_state <= DFX_STATE_ERROR;
                                end
                            end

                            DFX_CMD_RESET: begin
                                if (selected_rp < NUM_RPS) begin
                                    dfx_next_state <= DFX_STATE_SHUTDOWN;
                                end else begin
                                    dfx_err_code <= DFX_ERR_INVALID_RP;
                                    dfx_error <= 1'b1;
                                    int_error_status <= 1'b1;
                                    dfx_next_state <= DFX_STATE_ERROR;
                                end
                            end

                            DFX_CMD_STATUS: begin
                                // Just update status registers
                                dfx_done <= 1'b1;
                                int_done_status <= 1'b1;
                            end

                            DFX_CMD_ABORT, DFX_CMD_CLEAR_ERR, DFX_CMD_DEBUG, DFX_CMD_RESERVE: begin
                                // These commands don't do anything in idle
                                dfx_done <= 1'b1;
                                int_done_status <= 1'b1;
                            end

                            default: begin
                                dfx_err_code <= DFX_ERR_INVALID_CMD;
                                dfx_error <= 1'b1;
                                int_error_status <= 1'b1;
                                dfx_next_state <= DFX_STATE_ERROR;
                            end
                        endcase
                    end
                end

                DFX_STATE_INIT: begin
                    // Initialize the reconfiguration process
                    cfg_word_counter <= '0;

                    // Prepare for memory access to read bitstream header
                    m_axi_araddr <= bs_addr[31:0];
                    m_axi_arlen <= 8'd7; // Read 8 words (header size)
                    m_axi_arsize <= 3'b010; // 4 bytes per transfer
                    m_axi_arburst <= 2'b01; // INCR burst
                    m_axi_arvalid <= 1'b1;

                    mem_next_state <= MEM_ADDR;
                    dfx_next_state <= DFX_STATE_CHECK_BITSTREAM;
                end

                DFX_STATE_CHECK_BITSTREAM: begin
                    // Wait for memory read to complete
                    if (mem_state == MEM_DONE) begin
                        // Validate bitstream header
                        if (bitstream_buffer[0] == 32'h44465800) begin // "DFX\0"
                            // Check if target RP matches
                            if (bitstream_buffer[3] == selected_rp) begin
                                // Valid bitstream - continue to load prep
                                dfx_next_state <= DFX_STATE_SHUTDOWN;
                            end else begin
                                // Invalid target RP
                                dfx_err_code <= DFX_ERR_INVALID_BS;
                                dfx_error <= 1'b1;
                                int_error_status <= 1'b1;
                                dfx_next_state <= DFX_STATE_ERROR;
                            end
                        end else begin
                            // Invalid bitstream header
                            dfx_err_code <= DFX_ERR_INVALID_BS;
                            dfx_error <= 1'b1;
                            int_error_status <= 1'b1;
                            dfx_next_state <= DFX_STATE_ERROR;
                        end
                    end
                end

                DFX_STATE_SHUTDOWN: begin
                    // Signal cores to stop
                    core_pause[selected_rp] <= 1'b1;
                    core_stop[selected_rp] <= 1'b1;

                    // Wait for core to acknowledge shutdown
                    if (!core_status[selected_rp]) begin
                        // Enable RP isolation
                        rp_decouple[selected_rp] <= 1'b1;
                        core_pause[selected_rp] <= 1'b0;
                        core_stop[selected_rp] <= 1'b0;

                        if (cmd_type == DFX_CMD_LOAD) begin
                            dfx_next_state <= DFX_STATE_LOAD_PREP;
                        end else if (cmd_type == DFX_CMD_RESET) begin
                            // For reset, we're done with shutdown
                            dfx_next_state <= DFX_STATE_STARTUP;
                        end
                    end
                end

                DFX_STATE_LOAD_PREP: begin
                    // Initialize bitstream loading
                    buf_read_ptr <= '0;
                    buf_write_ptr <= '0;
                    buf_empty <= 1'b1;
                    buf_full <= 1'b0;

                    // Start memory read for bitstream
                    m_axi_araddr <= bs_addr[31:0] + 32; // Skip header
                    m_axi_arlen <= 8'd7; // Read 8 words at a time
                    m_axi_arsize <= 3'b010; // 4 bytes per transfer
                    m_axi_arburst <= 2'b01; // INCR burst
                    m_axi_arvalid <= 1'b1;

                    // Start configuration port
                    cfg_active <= 1'b1;
                    cfg_state <= CFG_INIT;

                    // Move to loading state
                    dfx_next_state <= DFX_STATE_LOADING;
                end

                DFX_STATE_LOADING: begin
                    // Check for abort command
                    if (cmd_abort) begin
                        cfg_active <= 1'b0;
                        dfx_next_state <= DFX_STATE_ERROR;
                        dfx_err_code <= DFX_ERR_NONE; // Aborted intentionally
                    end

                    // Update progress counter
                    progress_counter <= cfg_word_counter;

                    // Check timeout
                    if (timeout_counter > 0) begin
                        timeout_counter <= timeout_counter - 1;
                    end else begin
                        cfg_active <= 1'b0;
                        dfx_err_code <= DFX_ERR_TIMEOUT;
                        dfx_error <= 1'b1;
                        int_timeout_status <= 1'b1;
                        dfx_next_state <= DFX_STATE_ERROR;
                    end

                    // Check configuration completion
                    if (cfg_state == CFG_DONE) begin
                        cfg_active <= 1'b0;
                        dfx_next_state <= DFX_STATE_VERIFY;
                    end
                end

                DFX_STATE_VERIFY: begin
                    // For a real implementation, verify the loaded bitstream
                    // For now, we assume it worked

                    // Update configured bitstream ID
                    configured_bitstreams[selected_rp] <= current_bs_id;

                    // Move to startup
                    dfx_next_state <= DFX_STATE_STARTUP;
                end

                DFX_STATE_STARTUP: begin
                    // Disable RP isolation
                    rp_decouple[selected_rp] <= 1'b0;

                    // Signal core to resume
                    core_resume[selected_rp] <= 1'b1;

                    // Wait for core to acknowledge
                    if (core_status[selected_rp]) begin
                        core_resume[selected_rp] <= 1'b0;
                        dfx_next_state <= DFX_STATE_DONE;
                    end
                end

                DFX_STATE_DONE: begin
                    // Signal completion
                    dfx_done <= 1'b1;
                    int_done_status <= 1'b1;

                    // Automatically return to idle
                    dfx_next_state <= DFX_STATE_IDLE;
                end

                DFX_STATE_ERROR: begin
                    // Stay in error state until cleared
                    if (regs[DFX_REG_CTRL][DFX_CTRL_CLR_ERR_BIT]) begin
                        dfx_next_state <= DFX_STATE_IDLE;
                    end
                end

                default: begin
                    dfx_next_state <= DFX_STATE_IDLE;
                end
            endcase

            // Memory access state machine
            case (mem_state)
                MEM_IDLE: begin
                    m_axi_arvalid <= 1'b0;
                    m_axi_rready <= 1'b0;
                end

                MEM_ADDR: begin
                    // Wait for address to be accepted
                    if (m_axi_arready && m_axi_arvalid) begin
                        m_axi_arvalid <= 1'b0;
                        m_axi_rready <= 1'b1;
                        mem_next_state <= MEM_DATA;
                    end
                end

                MEM_DATA: begin
                    // Receive data
                    if (m_axi_rvalid && m_axi_rready) begin
                        // Store data in buffer
                        bitstream_buffer[buf_write_ptr[4:0]] <= m_axi_rdata;
                        buf_write_ptr <= buf_write_ptr + 1;

                        // Check for last data
                        if (m_axi_rlast) begin
                            m_axi_rready <= 1'b0;
                            mem_next_state <= MEM_DONE;
                        end
                    end
                end

                MEM_DONE: begin
                    // Memory access complete
                    mem_next_state <= MEM_IDLE;
                end

                default: begin
                    mem_next_state <= MEM_IDLE;
                end
            endcase

            // Configuration state machine
            case (cfg_state)
                CFG_IDLE: begin
                    // Reset configuration interface
                    if (USE_ICAP) begin
                        icap_ce_n <= 1'b1;
                        icap_write_n <= 1'b1;
                    end else begin
                        pcap_csib <= 1'b1;
                        pcap_rdwrb <= 1'b1;
                    end
                end

                CFG_INIT: begin
                    // Wait for buffer to have data
                    if (!buf_empty && cfg_active) begin
                        cfg_state <= CFG_SYNC;
                    end
                end

                CFG_SYNC: begin
                    // Send SYNC word sequence
                    if (USE_ICAP) begin
                        icap_ce_n <= 1'b0;
                        icap_write_n <= 1'b0;
                        icap_din <= 32'hAA995566; // SYNC word
                    end else begin
                        pcap_csib <= 1'b0;
                        pcap_rdwrb <= 1'b0;
                        pcap_din <= 32'hAA995566; // SYNC word
                    end

                    cfg_next_state <= CFG_WRITE;
                end

                CFG_WRITE: begin
                    // Check if we need more data
                    if (buf_empty && cfg_word_counter < bs_size/4) begin
                        // Request more data
                        m_axi_araddr <= bs_addr[31:0] + 32 + (cfg_word_counter * 4);
                        m_axi_arlen <= 8'd7; // Read 8 words at a time
                        m_axi_arvalid <= 1'b1;
                        mem_next_state <= MEM_ADDR;

                        // Pause until data arrives
                        if (USE_ICAP) begin
                            icap_ce_n <= 1'b1;
                        end else begin
                            pcap_csib <= 1'b1;
                        end
                    end

                    // Send configuration data
                    if (!buf_empty) begin
                        if (USE_ICAP) begin
                            icap_ce_n <= 1'b0;
                            icap_write_n <= 1'b0;
                            // Note: ICAP requires byte-swapped data
                            icap_din <= {
                                bitstream_buffer[buf_read_ptr[4:0]][7:0],
                                bitstream_buffer[buf_read_ptr[4:0]][15:8],
                                bitstream_buffer[buf_read_ptr[4:0]][23:16],
                                bitstream_buffer[buf_read_ptr[4:0]][31:24]
                            };
                        end else begin
                            pcap_csib <= 1'b0;
                            pcap_rdwrb <= 1'b0;
                            pcap_din <= bitstream_buffer[buf_read_ptr[4:0]];
                        end

                        // Update read pointer and counter
                        buf_read_ptr <= buf_read_ptr + 1;
                        cfg_word_counter <= cfg_word_counter + 1;

                        // Check if buffer is now empty
                        if (buf_read_ptr + 1 == buf_write_ptr) begin
                            buf_empty <= 1'b1;
                        end

                        // Check for completion
                        if (cfg_word_counter + 1 >= bs_size/4) begin
                            cfg_next_state <= CFG_DESYNC;
                        end
                    end
                end

                CFG_DESYNC: begin
                    // Send DESYNC command
                    if (USE_ICAP) begin
                        icap_ce_n <= 1'b0;
                        icap_write_n <= 1'b0;
                        icap_din <= 32'h0000000D; // DESYNC command
                    end else begin
                        pcap_csib <= 1'b0;
                        pcap_rdwrb <= 1'b0;
                        pcap_din <= 32'h0000000D; // DESYNC command
                    end

                    cfg_next_state <= CFG_DONE;
                end

                CFG_DONE: begin
                    // Disable configuration interface
                    if (USE_ICAP) begin
                        icap_ce_n <= 1'b1;
                        icap_write_n <= 1'b1;
                    end else begin
                        pcap_csib <= 1'b1;
                        pcap_rdwrb <= 1'b1;
                    end
                end

                default: begin
                    cfg_next_state <= CFG_IDLE;
                end
            endcase

            // Check buffer state
            buf_empty <= (buf_read_ptr == buf_write_ptr);
            buf_full <= (buf_write_ptr + 1 == buf_read_ptr);

            // Update RP status
            rp_status <= core_status;

            // Generate interrupt
            irq_out <= (int_done_status & int_done_enable) |
                       (int_error_status & int_error_enable) |
                       (int_timeout_status & int_timeout_enable) |
                       (int_progress_status & int_progress_enable);
        end
    end

endmodule

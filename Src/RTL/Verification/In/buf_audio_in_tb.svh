`ifndef __AUDIO_DEFS_TB_VH__
`define __AUDIO_DEFS_TB_VH__


// Testbench parameters
localparam int TB_NUM_AUDIO_CHANNELS = 1;


`ifndef RESET_CYCLE
`define RESET_CYCLE \
    begin \
        sys_rst = 1'b1;    \
        #(SYS_CLK_PERIOD); \
        sys_rst = 1'b0;    \
        $display("Time %0t: Reset deasserted", $time); \
        #(SYS_CLK_PERIOD); \
    end
`endif

`ifndef READ_ENABLE
`define READ_ENABLE \
    begin \
        adv_read_req = 1'b1; \
        @(posedge sys_clk); \
    end
`endif

`ifndef READ_DISABLE
`define READ_DISABLE \
    begin \
        adv_read_req = 1'b0; \
        @(posedge sys_clk); \
    end
`endif

`ifndef READ_ONCE
`define READ_ONCE \
    begin \
        `READ_ENABLE \
        `READ_DISABLE \
    end
`endif

`endif // __AUDIO_DEFS_TB_VH__

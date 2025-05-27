`ifndef __AUDIO_DEFS_TB_VH__
`define __AUDIO_DEFS_TB_VH__

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
        @(negedge sys_clk); \
        read_enable = 1'b1; \
        @(posedge sys_clk); \
        @(negedge sys_clk); \
        read_enable = 1'b0; \
        @(posedge sys_clk); \
    end
`endif

`endif // __AUDIO_DEFS_TB_VH__

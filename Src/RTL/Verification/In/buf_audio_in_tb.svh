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

`ifndef adv_read_enable
`define adv_read_enable \
    begin \
        @(negedge sys_clk); \
        adv_read_enable = 1'b1; \
        @(posedge sys_clk); \
        @(negedge sys_clk); \
        adv_read_enable = 1'b0; \
        @(posedge sys_clk); \
    end
`endif

`endif // __AUDIO_DEFS_TB_VH__

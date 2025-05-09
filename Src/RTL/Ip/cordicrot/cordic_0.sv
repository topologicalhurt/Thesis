module cordic_0 (
	input wire aclk, s_axis_phase_tvalid, s_axis_cartesian_tvalid,
	input wire [23:0] s_axis_phase_tdata, s_axis_cartesian_tdata,
	output wire m_axis_dout_tvalid,
	output wire [47:0] m_axis_dout_tdata
);

endmodule

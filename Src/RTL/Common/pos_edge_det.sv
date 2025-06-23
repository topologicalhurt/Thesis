module pos_edge_det (
    input sig,
    input clk,
    output pe
);
    reg sig_d;

    // This always block ensures that sig_dly is exactly 1 clock behind sig
	always @ (posedge clk) begin
		sig_d <= sig;
	end

	assign pe = sig & ~sig_d;
endmodule

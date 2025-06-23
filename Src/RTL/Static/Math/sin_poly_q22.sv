`include "Src/RTL/Static/Cores/consts.svh"

module sin_poly_q22 (
    input  logic [23:0] theta_in,    // 24-bit input angle, Q2.22 format (0 to 2π)
    output logic [23:0] sine_out    // 24-bit output sine, Q1.23 format (signed)
);
    // Coefficients for sin(x) ~ x + a3*x^3 + a5*x^5 + a7*x^7 on [0, π/2]
    // Represented in Q1.23 (for the polynomial output which is [-1,1]).
    localparam logic [23:0] A1 = 24'd8388607;   // ~0.9999999 in Q1.23
    localparam logic [23:0] A3 = 24'hD55555;    // ~-0.1666665 in Q1.23 (two’s complement)
    localparam logic [23:0] A5 = 24'h05550F;    // ~0.0083322 in Q1.23
    localparam logic [23:0] A7 = 24'hFFFECE;    // ~-0.0001951 in Q1.23

    // 1. Range reduction to [0, π/2]
    logic [23:0] angle_mod;
    logic [1:0] quadrant;

    // (Compute quadrant and reduced angle)
    // Here, assume theta_in is 0 to 2π (unsigned). Compute quadrant = theta_in / (0x400000) // 0x400000 ~ π/2 in Q2.22.
    always_comb begin
        if (theta_in < `PI_OVER_2) begin
            quadrant = 2'd0;
            angle_mod = theta_in;
        end else if (theta_in < `PI) begin
            quadrant = 2'd1;
            angle_mod = `PI - theta_in;         // reflect in QII
        end else if (theta_in < `THREE_PI_OVER_2) begin
            quadrant = 2'd2;
            angle_mod = theta_in - `PI;         // shift to [0, π/2] in QIII
        end else begin
            quadrant = 2'd3;
            angle_mod = (`TWO_PI - theta_in); // 2π (in Q2.22) minus theta_in
        end
    end

    // 2. Polynomial evaluation on angle_mod (now in [0, π/2] Q2.22)
    // First, compute powers u = x^2 and u2 = x^4 for reuse. Use 48-bit for multiplication.
    logic [47:0] prod48;
    logic signed [23:0] x, u, u2;
    assign x = angle_mod[23:0];  // treat as Q2.22 value
    // x^2 (Q4.44 initially, take upper 24 bits to get Q2.22)
    assign prod48 = {{24{1'b0}}, x} * {{24{1'b0}}, x};
    assign u = prod48[45:22];  // high 24 bits (bit45 downto 22) -> Q2.22 result
    // x^4 = u^2
    assign prod48 = {{24{1'b0}}, u} * {{24{1'b0}}, u};
    assign u2 = prod48[45:22]; // Q2.22

    // Horner-like evaluation:
    // sin(x) ≈ x * (A1 + A3*u + A5*u^2 + A7*u^3). We already have u and u2; u^3 = u * u^2.
    logic [23:0] u3, poly_val;
    // u^3 = u * u2 (again 48-bit multiply)
    assign prod48 = {{24{1'b0}}, u} * {{24{1'b0}}, u2};
    assign u3 = prod48[45:22];
    // Evaluate even polynomial f(u) = A1 + A3*u + A5*u^2 + A7*u^3
    // We do this via Horner: f(u) = A1 + u * (A3 + u * (A5 + u * A7))
    logic [23:0] temp1, temp2;
    assign temp1 = A5 + ( ({{24{1'b0}}, A7} * {{24{1'b0}}, u}) >> 22 );      // A5 + A7*u
    assign temp2 = A3 + ( ({{24{1'b0}}, temp1} * {{24{1'b0}}, u}) >> 22 );   // A3 + (A5 + A7*u)*u
    assign poly_val = A1 + ( ({{24{1'b0}}, temp2} * {{24{1'b0}}, u}) >> 22 );// A1 + ... * u
    // Now poly_val = f(u) in Q1.23 format (since A* were Q1.23 and u is Q2.22, we shifted 22 bits after multiply).
    // Finally sin(x) = x * f(u). Multiply x (Q2.22) and f(u) (Q1.23) -> result Q? We have 1+2 int bits and 23+22 frac = 45 bits.
    assign prod48 = $signed({{24{x[23]}}, x}) * $signed({{24{poly_val[23]}}, poly_val});
    // Since x had 2 int bits and poly_val has 0 int (just sign), the result has 2+0=2 int bits -> Q2.44. We want Q1.23.
    // Take the appropriate top bits (shift right by 21 to reduce 44 frac to 23 frac, and also adjust int bits).
    wire signed [47:0] rounded = prod48 + 48'h0_100000;  // rounding: add 0.5 LSB at bit21
    wire signed [23:0] sin_q23 = rounded[46:23];  // take sign + 1 int + 22 frac = 24 bits
    // sin_q23 is the sine value in Q1.23.

    // 3. Apply quadrant sign
    always_comb begin
        if (quadrant == 2'd2 || quadrant == 2'd3)
            sine_out = -sin_q23;   // negate for QIII, QIV
        else
            sine_out = sin_q23;
    end
endmodule

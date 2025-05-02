`include "Src/RTL/Static/Cores/consts.svh"

module cos_poly_q22 (
    input  logic [23:0] theta_in,  // 24-bit input angle, Q2.22 format (0 to 2π)
    output logic [23:0] cos_out    // 24-bit output cosine, Q1.23 format (signed)
);
    import math::angle_shift_q22;

    logic [24:0] add_tmp;      // 1 extra bit for carry
    logic [23:0] theta_shift;  // wrapped angle for sine core

    always_comb begin
        theta_shift = angle_shift_q22(theta);
    end

    sin_poly_q22 sin_core (
        .theta_in (theta_shift),
        .sine_out (cos_out)    // cos θ = sin(θ+π/2)
    );
endmodule

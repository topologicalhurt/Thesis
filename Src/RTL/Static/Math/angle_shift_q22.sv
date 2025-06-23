package math;

    function automatic logic [23:0] angle_shift_q22 (
        input logic [23:0] x
    );
        logic [24:0] tmp;
        tmp = {1'b0, x} + {1'b0, PI_OVER_2};
        if (tmp >= TWO_PI)
            angle_shift_q22 = tmp - `TWO_PI;
        else
            angle_shift_q22 = tmp[23:0];
    endfunction

endpackage

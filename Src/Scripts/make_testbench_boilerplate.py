#!/usr/bin/env python
"""
------------------------------------------------------------------------
Filename: 	make_testbench_boilerplate.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Makes a boilerplate testbench / test harness for module under test in RTL
to avoid having to write one out every time

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the SCRIPTS module
It is intended to be run as a script for use with developer operations, automation / task assistance or as a wrapper for the RTL code.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

# TODO:
# (1) Get portlist and create dud variables for the portlist then wire correctly

import os
import functools
import argparse as ap


from Scripts.write_file_header import write_headers_to_files, write_resources_file
from Scripts.argparse_helpers import get_action_from_parser_by_name, str2path_belongs_in
from Scripts.consts import VERIFICATION_DIR


def main():
    parser = ap.ArgumentParser(description=__doc__.strip())

    parser.add_argument('dir', type=functools.partial(str2path_belongs_in, ancestor=VERIFICATION_DIR, enforce_exists=False),
                        help='The output directory for the testbench.'
                        )

    args = vars(parser.parse_args())

    if os.path.exists(args['dir']):
        err_invoker = get_action_from_parser_by_name(parser, 'dir')
        raise ap.ArgumentError(err_invoker,
                               f'The dir argument must not already exist. Check: {args["dir"]} doesn\'t exist already'
                               )

    if args['dir'].suffix != '.sv':
        args['dir'] = args['dir'].with_suffix('.sv')

    # First of all, create the file
    with open(args['dir'], 'w+') as _:
        pass

    # Second, add the standard script header info
    write_resources_file([args['dir']])
    write_headers_to_files()

    # Third, write the boilerplate info
    module_name = args['dir'].stem
    if module_name.endswith('_tb'):
        base_module_name = module_name[:-3]  # Remove '_tb'
    else:
        base_module_name = module_name
        module_name += '_tb'  # Add '_tb' if not present

    boilerplate = f'''
module {module_name};

    parameter SYS_CLK_PERIOD = 10;      // I.e. 10 = 100 MHz system clock

    // Clock generation
    reg clk;

    // Instantiate the DUT (Device Under Test)
    {base_module_name} #(
    ) dut (
        .i_clk(clk)
    );

    // System clock generation
    initial begin
        clk = 0;
        forever #(SYS_CLK_PERIOD/2) clk = ~clk;
    end

    // Test sequence
    initial begin
        $display("Starting {base_module_name.upper()} testbench");

        // DO TESTING HERE

        $display("{base_module_name.upper()} testbench completed successfully");
        $finish;
    end

endmodule'''

    with open(args['dir'], 'a') as f:
        f.write(boilerplate)


if __name__ == '__main__':
    main()

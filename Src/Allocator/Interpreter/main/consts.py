"""
------------------------------------------------------------------------
Filename: 	consts.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the ALLOCATOR module
It is intended to be used as part of the allocator design which is responsible for the soft-core, or offboard, management of the on-fabric components.
Please refer to docs/whitepaper first, which provides a complete description of the project & it's motivations.

The design is NOT COVERED UNDER ANY WARRANTY.

LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------

"""

import importlib
import logging

from Allocator.Interpreter.main.dataclass import PROGRAM_META_INFO


util_helpers = importlib.import_module('.util_helpers', package='Allocator.Interpreter.main')
get_repo_root = util_helpers.get_repo_root
set_logger_opts = util_helpers.set_logger_opts


META_INFO = PROGRAM_META_INFO(
    **{
        'DEBUG': True,
        'GIT_ROOT': get_repo_root(),
    }
)

#################
# TARGET FPGA'S #
#################

xilinx_name_validator = importlib.import_module('.xilinx_name_validator', package='Allocator.Interpreter.main')
XilinxDeviceSet = xilinx_name_validator.XilinxDeviceSet

GEN7_ARTIX_TARGET_NAMES = ['XC7A100+T']
GEN7_KINTEX_TARGET_NAMES = ['XC7K100+T']
GEN7_VIRTEX_TARGET_NAMES = ['XC7V330+T']
ZYNQ_ULTRASCALE_TARGET_NAMES = ['ZU2+CG', 'ZU2+EG']
XILINX_ALL_TARGET_NAMES = GEN7_ARTIX_TARGET_NAMES + GEN7_KINTEX_TARGET_NAMES + GEN7_VIRTEX_TARGET_NAMES + ZYNQ_ULTRASCALE_TARGET_NAMES
XILINX_TARGETS = XilinxDeviceSet(names=XILINX_ALL_TARGET_NAMES)

###########
# LOGGING #
###########


LOG_DIR = get_repo_root() / 'bin' / 'logs'

LOGGER = logging.getLogger(__name__)
DYADIC_POLY_PREFIX='\n[*] DYADIC_POLY [*] \n{}'
LOGGER = set_logger_opts(LOGGER, dir=LOG_DIR)

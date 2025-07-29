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
import logging.handlers


######################################
# GENERAL PROGRAM / META INFO / MISC #
######################################

dataclass = importlib.import_module('.dataclass', package='Allocator.Interpreter')
ProgramMetaInformation = dataclass.ProgramMetaInformation

META_INFO = ProgramMetaInformation(
    **{
        'DEBUG': True
    }
)

#################
# TARGET FPGA'S #
#################

xilinx_name_validator = importlib.import_module('.xilinx_name_validator', package='Allocator.Interpreter')
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

LOGGER = logging.getLogger(__name__)


def set_logger_opts():
    global LOGGER

    # Set circular logger
    LOGGER.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename='info.log',
        encoding='utf-8',
        maxBytes=2 * 1024 * 1024,  # 2 MiB files
        backupCount=5 # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(('[{asctime}] [{levelname:<8}] PID {process} @ {threadName}: '
                                '{message}'), dt_fmt, style='{')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    LOGGER.addHandler(handler)


# set_logger_opts()

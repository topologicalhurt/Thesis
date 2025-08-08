"""
------------------------------------------------------------------------
Filename: 	consts.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

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


import sys
import traceback
import logging
import logging.handlers
import datetime as dt

from pathlib import Path
from textwrap import TextWrapper

from Scripts.util_helpers import get_repo_root, get_git_author
from Scripts.dataclass import PROGRAM_META_INFO
from Allocator.Interpreter.dataclass import XILINX_BRAM_SIZES


#############
# IN CONSTS #
#############

# Audio & channel parameters
STEREO=1
SAMPLE_RATE=96 # In kHz

# Audio buffer sizes
BUF_DEPTH=32
HOP_SIZE=16

# Downsampler coefficients
DOWNSAMPLE_COEFFS_NTAPS=127
COMMON_RATES = [44100, 32000, 24000, 16000, 8000] # Common output rates

##############
# LUT CONSTS #
##############

LUT_DEFAULT_BRAM = XILINX_BRAM_SIZES.members_from_indx(idx=2)[XILINX_BRAM_SIZES.ULTRASCALE_DUALPORT]

######################################
# GENERAL PROGRAM / META INFO / MISC #
######################################

META_INFO = PROGRAM_META_INFO(
    **{
        'DATE_RUN': dt.datetime.now(),
        'DEBUG': True,
        'GIT_ROOT': get_repo_root(),
        'AUTHOR_CREDENTIALS': get_git_author(),
        'EXCLUDED_DIRS': {'.git', '__pycache__', '.venv', 'node_modules', 'obj_dir', '.cache'}
    }
)

###########
# LOGGING #
###########

MONO_STEREO_WRAPPER_PREFIX='\n[*] MONO_STEREO_WRAPPER [*] \n{}'
GENERATE_TRIG_LUTS_PREFIX='\n[*] TRIG_LUT_GENERATOR[*] \n{}'
GENERATE_DOWNSAMPLE_LUTS_PREFIX='\n[*] DOWNSAMPLE_GENERATOR [*] \n{}'
UNWRAP_VEO_PREFIX='\n[*] VEO_UNWRAPPER [*] \n{}'
WRITE_FILE_HEADER_PREFIX='\n[*] HEADER_WRITER [*] \n{}'
MAKE_TESTBENCH_BOILERPLATE_PREFIX='\n[*] TESTBENCH_BOILERPLATE_MAKER [*] \n{}'

LOGGER = logging.getLogger(__name__)
LOGGER_LINE_WIDTH = 100
log_wrapper = TextWrapper(width=LOGGER_LINE_WIDTH)


def set_logger_opts():
    global LOGGER

    # Set circular logger
    LOGGER.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename='info_scripts.log',
        encoding='utf-8',
        maxBytes=2 * 1024 * 1024,  # 2 MiB files
        backupCount=5 # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(('\n[{asctime}] [{levelname:<8}] PID {process} @ {threadName}: '
                                '{message}'), dt_fmt, style='{')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    LOGGER.addHandler(handler)


def excepthook(type, value, tback):
    msg = '\n' + '=' * LOGGER_LINE_WIDTH
    msg += '\nUncaught exception:\n'
    msg += log_wrapper.fill(''.join(traceback.format_exception(type, value, tback, limit=1)))
    msg += '\n' + '=' * LOGGER_LINE_WIDTH
    LOGGER.error(msg)
    traceback.print_exception(type, value, tback)


sys.excepthook = excepthook
set_logger_opts()


# File paths (relative to script)
CURRENT_DIR = Path(__file__).parent.resolve()
RTL_DIR = (CURRENT_DIR / '../../RTL').resolve()
SRC_DIR = RTL_DIR.parent
ALLOCATOR_DIR = SRC_DIR / 'Allocator'
DEMO_DIR = SRC_DIR / 'Demo'
RESOURCES_DIR = SRC_DIR / 'Resources'
VERIFICATION_DIR = RTL_DIR / 'Verification'
DOCUMENT_META = RESOURCES_DIR / 'document_meta.yaml'
RTL_IN_DIR = RTL_DIR / 'In'
RTL_TRIG_HEX_DIR = RTL_DIR / 'Static' / 'Math'
I2S_DUPLICATE_REGISTER_HEADER_PATH = RTL_IN_DIR / 'buf_audio_in.svh'
I2S_DUPLICATE_REGISTER_PATH = RTL_IN_DIR / 'buf_audio_in.sv'

DEFAULT_VEO_LOCATION = RTL_DIR / 'Ip'

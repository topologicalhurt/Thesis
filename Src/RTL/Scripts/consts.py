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


import os
import datetime as dt

from RTL.Scripts.util_helpers import get_repo_root, get_git_author
from RTL.Scripts.dataclass import ProgramMetaInformation


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

######################################
# GENERAL PROGRAM / META INFO / MISC #
######################################

# Meta
META_INFO = ProgramMetaInformation(
    **{
        'DATE_RUN': dt.datetime.now(),
        'GIT_ROOT': get_repo_root(),
        'AUTHOR_CREDENTIALS': get_git_author()
    }
)

# Logging
MONO_STEREO_WRAPPER_PREFIX='[*] MONO_STEREO_WRAPPER [*] {}'

# File paths (relative to script)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RTL_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'RTL')
SRC_DIR = os.path.dirname(RTL_DIR)
ALLOCATOR_DIR = os.path.join(SRC_DIR, 'Allocator')
DEMO_DIR = os.path.join(SRC_DIR, 'Demo')
RESOURCES_DIR = os.path.join(RTL_DIR, 'Resources')
VERIFICATION_DIR = os.path.join(RTL_DIR, 'Verification')
DOCUMENT_META = os.path.join(RESOURCES_DIR, 'document_meta.yaml')
RTL_IN_DIR = os.path.join(RTL_DIR, 'In')
RTL_HEX_DIR = os.path.join(RTL_DIR, 'Static', 'Cores', 'Math')
I2S_DUPLICATE_REGISTER_HEADER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.svh')
I2S_DUPLICATE_REGISTER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.sv')

import os


#############
# IN CONSTS #
#############
STEREO=1
BUF_DEPTH=32
HOP_SIZE=16
SAMPLE_RATE=96 # In kHz

DOWNSAMPLE_COEFFS_NTAPS=127

# Common output rates
COMMON_RATES = [44100, 32000, 24000, 16000, 8000]


# Logging
MONO_STEREO_WRAPPER_PREFIX='[*] MONO_STEREO_WRAPPER [*] {}'


# File paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RTL_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'RTL')
RTL_IN_DIR = os.path.join(RTL_DIR, 'In')
RTL_HEX_DIR = os.path.join(RTL_DIR, 'Static', 'Cores', 'Math')
I2S_DUPLICATE_REGISTER_HEADER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.svh')
I2S_DUPLICATE_REGISTER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.sv')

import os


MONO_STEREO_WRAPPER_PREFIX='[*] MONO_STEREO_WRAPPER [*] {}'

# File paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RTL_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'RTL')
RTL_IN_DIR = os.path.join(RTL_DIR, 'In')
RTL_HEX_DIR = os.path.join(RTL_DIR, 'Static', 'Cores', 'Math')
I2S_DUPLICATE_REGISTER_HEADER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.svh')
I2S_DUPLICATE_REGISTER_PATH = os.path.join(RTL_IN_DIR, 'buf_audio_in.sv')

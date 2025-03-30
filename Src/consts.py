import logging
import logging.handlers 
import os


# Logging
LOGGER = logging.getLogger(__name__)
MONO_STEREO_WRAPPER_PREFIX='[*] MONO_STEREO_WRAPPER [*] {}'

# File paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
I2S_DUPLICATE_REGISTER_HEADER_PATH = os.path.join(CURRENT_DIR, 'In', 'i2s_duplicate_register.vh')
I2S_DUPLICATE_REGISTER_PATH = os.path.join(CURRENT_DIR, 'In', 'i2s_duplicate_register.v')


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


set_logger_opts()

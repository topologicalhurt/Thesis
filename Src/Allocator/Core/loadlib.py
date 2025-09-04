import ctypes

from pathlib import Path


def load_libs(libs: list[str]) -> list[ctypes.CDLL]:
    here = Path(__file__).parent
    loaded_libs = []
    for candidate in libs:
        # Try loading from build path first, then system path
        build_path = here / 'build' / candidate
        if build_path.exists():
            try:
                loaded_libs.append(ctypes.CDLL(str(build_path)))
            except OSError:
                pass
            finally:
                continue
        try:
            loaded_libs.append(ctypes.CDLL(candidate))
        except OSError:
            pass

    if not loaded_libs:
        raise OSError(f'Could not load all of {libs}; tried searching in build path and system path.')

    return loaded_libs

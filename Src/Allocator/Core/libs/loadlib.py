import ctypes

from pathlib import Path


def load_libs(libs: list[str]) -> list[ctypes.CDLL]:
    build_path = Path(__file__).resolve().parent.parent / 'build'
    loaded_libs: list[ctypes.CDLL] = []
    for candidate in libs:

        # Try loading from build path first
        cand_build = build_path / candidate
        if cand_build.exists():
            try:
                loaded_libs.append(ctypes.CDLL(str(cand_build)))
                continue
            except OSError:
                pass

        # Fallback to system search path
        try:
            loaded_libs.append(ctypes.CDLL(candidate))
        except OSError as e:
            raise OSError(
                f"Could not load '{candidate}'. Tried '{cand_build}' and system path. Original error: {e}"
            ) from e

    return loaded_libs

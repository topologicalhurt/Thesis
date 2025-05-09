import os
import argparse as ap
from pathlib import Path


def str2bool(v) -> bool:
    if isinstance(v, bool):
        return v
    v = v.lower()
    if v in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ap.ArgumentTypeError('Boolean value expected.')


def str2path(v) -> Path:
    if not os.path.isfile(v) and not os.path.isdir(v):
        raise ap.ArgumentTypeError(f'Given path {v} does not exist')
    return Path(v)


def sign(a,b,c):
    return (a[0]-c[0])*(b[1]-c[1])-(b[0]-c[0])*(a[1]-c[1])

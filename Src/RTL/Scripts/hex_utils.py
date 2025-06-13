"""
Manage (write to, read from) a generic LUT table in a managed .hex file
"""


import os
import sys
import itertools
import datetime as dt
import numpy as np

from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from Allocator.Interpreter.dataclass import LUT

from RTL.Scripts.dataclass import ByteOrder
from RTL.Scripts.util_helpers import get_git_author


class HexLutManager:
    HEADER =('// Coefficient memory for {fn}'
    '\n// ----------------------------------------------'
    '\n//   Bits per coeff.:          {bit_width}'
    '\n//   Endianness.:              {endianness}'
    '\n//   Table mode:               {table_mode}'
    '\n//   Table size:               {table_sz}kB'
    '\n//   LOP (level of precision): {lop}'
    '\n//   Effective scaling factor: {scale_factor}'
    '\n//   Measured avg. accuracy:   {avg_acc}'
    '\n//   Min accuracy:             {min_acc}'
    '\n//   Max accuracy:             {max_acc}'
    '//\n'
    '\n// Each line contains a value (coeff.) corresponding to the function {fn}.'
    '\n// This file was automatically generated with the command: {cmd}'
    '\n// *Do not* make any manual changes to this file'
    '\n// File generated @ {ts}'
    '\n// Author: {author_name} {author_email}'
    '\n//\n//'
    )

    def __init__(self, dir: Path):
        self.dir = dir

    @staticmethod
    def _get_byte_order_symbol_from_sys():
        return '<' if sys.byteorder == 'little' else '>'

    @staticmethod
    def _get_byte_order_symbol_from_target(target_order: ByteOrder = ByteOrder.BIG) -> str:
        if target_order == ByteOrder.BIG:
            target_order = '>'
        elif target_order ==  ByteOrder.LITTLE:
            target_order = '<'
        elif target_order == ByteOrder.NATIVE:
            target_order = HexLutManager._get_byte_order_symbol_from_sys()
        else:
            raise ValueError('Endian must be contained in ByteOrder')
        return target_order

    @staticmethod
    def _convert_to_byte_order(f: np.floating, target_order: ByteOrder = ByteOrder.BIG) -> bytes:
        target_order = HexLutManager._get_byte_order_symbol_from_target(target_order)
        f_type = np.dtype(f)
        current_order = f_type.byteorder
        if current_order == '=':
            current_order = HexLutManager._get_byte_order_symbol_from_sys()

        if current_order == target_order:
            packed_bytes = f.tobytes(target_order)
        else:
            packed_bytes = f.astype(f.dtype.newbyteorder(target_order)).tobytes()

        return packed_bytes

    @staticmethod
    def float_to_hex(f: float, target_order: ByteOrder = ByteOrder.BIG) -> str:
        """
        Converts a np n-bit float (E.g. np.float64) into its raw character
        hexadecimal string representation (IEEE 754 format).

        ## Args:
            f: The float value to convert.

        ## Returns:
            A string of hexadecimal characters (e.g., '400921fb54442d18').
        """
        packed_bytes = HexLutManager._convert_to_byte_order(f, target_order=target_order)
        return packed_bytes.hex()

    @staticmethod
    def hex_to_float(hex_str: str, dtype: np.floating, target_order: ByteOrder = ByteOrder.BIG) -> np.floating:
        """
        Converts a raw hexadecimal string representation (IEEE 754 format)
        back into a numpy n-bit float. Assumes the hex string is in
        big-endian format.

        Args:
            hex_str: A string of hexadecimal characters (e.g., '400921fb54442d18').
            dtype: The target numpy float type (e.g., np.float32, np.float64).
                This determines how many bytes to interpret.

        Returns:
            A numpy float value of the specified dtype.
        """
        # Ensure the hex string has an even number of characters
        if len(hex_str) % 2 != 0:
            raise ValueError('Hex string must have an even number of characters.')

        # Convert the hexadecimal string into a bytes object
        packed_bytes = bytes.fromhex(hex_str)

        # Check if the length of the bytes matches the expected size for the dtype
        if len(packed_bytes) != np.dtype(dtype).itemsize:
            raise ValueError(
                f'Length of hex string ({len(hex_str)} chars) does not match '
                f'the expected size for dtype {np.dtype(dtype).name} '
                f'({np.dtype(dtype).itemsize * 2} chars).'
            )

        # Use numpy.frombuffer to interpret the raw bytes as a numpy array.
        # The dtype is set to be big-endian ('>') by default to match the input format.
        target_order = HexLutManager._get_byte_order_symbol_from_target(target_order=target_order)
        return np.frombuffer(packed_bytes, dtype=np.dtype(dtype).newbyteorder(target_order))[0]


    def _get_valid_file_path(self, file_name: str, ow: bool | None = None) -> Path:
        """# Summary

        Gets the file_name relative to dir IFF the full path is valid.
        Raises an appropriate error if O.T.W.

        ## Args:
            file_name (str): the file name to check relative to the managed directory
            ow (bool): aliases write_lut_to_hex (overwrite permission: can overwrite if True, can't if false
            and ignored if None)

        ## Returns:
            str: The absolute path to the file in the managed directory if no errors raised
        """
        _, ext = os.path.splitext(file_name)
        if not ext:
            file_name += '.hex'
        elif ext != '.hex':
            raise ValueError('Lut to hex only supports .hex file extensions')

        file_path = Path(os.path.join(self.dir, file_name))
        if ow is False and os.path.exists(file_path):
            raise FileExistsError(f'File already exists at location: {file_path}')

        return file_path

    def write_lut_to_hex(self, file_name: str, lut: LUT, ow: bool=False,
                         target_order: ByteOrder = ByteOrder.BIG) -> None:
        """# Summary

        Writes a lut to a .hex file at the specified file path &
        with the specified name

        ## Args:
            fn (str): name
            lut (LUT): lut (see: LUT dataclass)
            ow (bool): overwrite files with same name?
        """
        file_path = self._get_valid_file_path(file_name=file_name, ow=ow)

        # Do the required formatting for the file header...
        header = HexLutManager.HEADER
        f_map = asdict(lut)
        f_map['fn'] = f_map['fn'].__name__
        f_map['endianness'] = f_map['endianness'].name.lower()
        f_map['lop'] = f_map['lop'].name.lower()
        f_map['table_mode'] = f_map['table_mode'].name.lower()
        f_map['ts'] = dt.datetime.now()
        acc_report = f_map.pop('acc_report')
        f_map['avg_acc'] = acc_report['avg_acc']
        f_map['min_acc'] = acc_report['min_acc']
        f_map['max_acc'] = acc_report['max_acc']
        f_map['author_name'], f_map['author_email'] = get_git_author()
        if f_map['scale_factor'] != 1:
            f_map['scale_factor'] = f'1/{f_map["scale_factor"]}'
        header = header.format_map(f_map)

        with open(file_path, 'w') as f:
            f.write(header)
            for entry in lut.lut:
                f.write(f'\n{HexLutManager.float_to_hex(entry, target_order=target_order)}')

    def read_lut_from_hex(self, file_name: str, dtype: np.floating,
                          target_order: ByteOrder = ByteOrder.NATIVE) -> Sequence[np.floating]:
        file_path = self._get_valid_file_path(file_name=file_name)
        with open(file_path, 'r') as f:
            after_header = itertools.dropwhile(lambda ln: ln.startswith('//') or ln == '\n', f)
            data = []
            for ln in after_header:
                ln = ln.strip()
                data.append(HexLutManager.hex_to_float(ln, dtype, target_order=target_order))
            return data

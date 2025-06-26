"""
------------------------------------------------------------------------
Filename: 	hex_utils.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	Manage (write to, read from) a generic LUT table in a managed .hex file

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

# TODO's
# (1) Properly format downsample lut file
# (2) Use the INT NPMAP to convert hex to int rather than improper type coverage solution that exists now


import os
import sys
import itertools
import datetime as dt
import numpy as np

from typing import assert_never
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from Allocator.Interpreter.dataclass import LUT, BYTEORDER

from RTL.Scripts.consts import META_INFO


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
        self._author_info = META_INFO.AUTHOR_CREDENTIALS
        self._fmap = {
                'fn': 'N/A',
                'bit_width': 'N/A',
                'endianness': 'N/A',
                'table_mode': 'N/A',
                'table_sz': 'N/A',
                'lop': 'N/A',
                'scale_factor': 'N/A',
                'avg_acc': 'N/A',
                'min_acc': 'N/A',
                'max_acc': 'N/A',
                'cmd': 'N/A',
                'ts': 'N/A',
                'author_name': 'N/A',
                'author_email': 'N/A'
        }
        self._header = self._get_header()

    def _change_format_mapping(self, fmap: Mapping) -> Mapping:
        fmap['ts'] = dt.datetime.now()

        if hasattr(fmap['fn'], '__name__'):
            fmap['fn'] = fmap['fn'].__name__

        if self._author_info is not None:
            fmap['author_name'], fmap['author_email'] = self._author_info

        if hasattr(fmap['endianness'], 'name'):
            fmap['endianness'] = fmap['endianness'].name.lower()

        fmap = {k: 'N/A' if v is None else v for k,v in fmap.items()} # Values with None will show 'N/A'
        return fmap

    def _get_header(self) -> str:
        fmap = self._change_format_mapping(self._fmap)
        header = HexLutManager.HEADER.format_map(fmap)
        return header

    @property
    def header(self) -> str:
        return self._header

    @staticmethod
    def _get_byte_order_symbol_from_sys():
        return '<' if sys.byteorder == 'little' else '>'

    @staticmethod
    def _get_byte_order_symbol_from_target(target_order: BYTEORDER = BYTEORDER.BIG) -> str:
        match target_order:
            case BYTEORDER.BIG:
                target_order = '>'
            case BYTEORDER.LITTLE:
                target_order = '<'
            case BYTEORDER.NATIVE:
                target_order = HexLutManager._get_byte_order_symbol_from_sys()
            case _:
                assert_never('Endian must be contained in BYTEORDER')
        return target_order

    @staticmethod
    def _convert_to_byte_order(f: np.floating | np.integer, target_order: BYTEORDER = BYTEORDER.BIG) -> bytes:
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
    def float_to_hex(f: float, target_order: BYTEORDER = BYTEORDER.BIG) -> str:
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
    def hex_to_dtype(hex_str: str, dtype: np.floating | np.integer,
                      target_order: BYTEORDER = BYTEORDER.BIG) -> np.floating | np.integer:
        """
        Converts a raw hexadecimal string representation
        back into a numpy n-bit float or integer. Assumes the hex string is in
        big-endian format.

        Args:
            hex_str: A string of hexadecimal characters (e.g., '400921fb54442d18').
            dtype: The target numpy float or integer type (e.g., np.float32, np.float64, np.int32, np.int64 Etc.)
            This determines how many bytes to interpret.

        Returns:
            A numpy float or integer value of the specified dtype.
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
        return np.frombuffer(packed_bytes, dtype=np.dtype(dtype).newBYTEORDER(target_order))[0]

    @staticmethod
    def int_to_hex(i: int | np.integer, target_order: BYTEORDER = BYTEORDER.BIG) -> str:
        """# Summary

        Converts a numpy n-bit integer (e.g. np.int32, np.uint64) into its raw
        hexadecimal string representation.

        ## Args:
            i: The integer value to convert.
            target_order: The byte order for the output hex string.

        ## Returns:
            A string of hexadecimal characters (e.g., '0000beef').
        """
        if not isinstance(i, np.integer):
            if isinstance(i, int):
                if 0 <= i.bit_length() < 31:
                    i = np.int32(i)
                elif 31 <= i.bit_length() < 63:
                    i = np.int64(i)
                elif 63 <= i.bit_length() < 127:
                    i = np.int128(i)
                else:
                    raise ValueError(f'Integer {i} is too large for standard numpy integer types')
            else:
                raise TypeError(f'Expected int or np.integer, got {type(i)} instead')

        packed_bytes = HexLutManager._convert_to_byte_order(i, target_order=target_order)
        return packed_bytes.hex()

    @staticmethod
    def hex_to_int(hex_str: str, dtype: np.integer, target_order: BYTEORDER = BYTEORDER.BIG) -> np.integer:
        """# Summary

        Converts a raw hexadecimal string representation back into a numpy n-bit integer.

        ## Args:
            hex_str: A string of hexadecimal characters (e.g., '0000beef').
            dtype: The target numpy integer type (e.g., np.int32, np.uint64).
            target_order: The byte order of the input hex string.

        ## Returns:
            A numpy integer value of the specified dtype.
        """
        return HexLutManager.hex_to_dtype(hex_str, dtype, target_order=target_order)

    @staticmethod
    def hex_to_float(hex_str: str, dtype: np.floating, target_order: BYTEORDER = BYTEORDER.BIG) -> np.floating:
        """# Summary

        Converts a raw hexadecimal string representation (IEEE 754 format)
        back into a numpy n-bit float.

        ## Args:
            hex_str: A string of hexadecimal characters (e.g., '400921fb54442d18').
            dtype: The target numpy float type (e.g., np.float32, np.float64).
            target_order: The byte order of the input hex string.

        ## Returns:
            A numpy float value of the specified dtype.
        """
        return HexLutManager.hex_to_dtype(hex_str, dtype, target_order=target_order)

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

    def write_lut_to_hex(self, file_name: str, lut: LUT,
                         write_type: Callable[..., str],
                         ow: bool=False,
                         target_order: BYTEORDER = BYTEORDER.BIG) -> None:
        """# Summary

        Writes a lut to a .hex file at the specified file path &
        with the specified name

        ## Args:
            fn (str): name
            lut (LUT): lut (see: LUT dataclass)
            ow (bool): overwrite files with same name?
        """
        self._fmap.update(asdict(lut)) # Modify the format map based on the LUT (do a dict update)

        file_path = self._get_valid_file_path(file_name=file_name, ow=ow)
        with open(file_path, 'w') as f:
            f.write(self._get_header())
            for entry in lut.lut:
                f.write(f'\n{write_type(entry, target_order=target_order)}')

    def read_lut_from_hex(self, file_name: str, dtype: np.floating,
                          read_type: Callable[..., np.floating | np.integer],
                          target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.floating]:
        file_path = self._get_valid_file_path(file_name=file_name)
        with open(file_path, 'r') as f:
            after_header = itertools.dropwhile(lambda ln: ln.startswith('//') or ln == '\n', f)
            data = []
            for ln in after_header:
                ln = ln.strip()
                data.append(read_type(ln, dtype, target_order=target_order))
            return data


class TrigLutManager(HexLutManager):
        def __init__(self, dir: Path):
            super().__init__(dir)

        def _change_format_mapping(self, fmap: Mapping) -> Mapping:
            # Handle enum fields that might be placeholder strings
            if hasattr(fmap['lop'], 'name'):
                fmap['lop'] = fmap['lop'].name.lower()
            if hasattr(fmap['table_mode'], 'name'):
                fmap['table_mode'] = fmap['table_mode'].name.lower()

            # Handle acc_report field that might be placeholder
            if isinstance(fmap.get('acc_report'), dict):
                acc_report = fmap.pop('acc_report')
                fmap['avg_acc'] = acc_report['avg_acc']
                fmap['min_acc'] = acc_report['min_acc']
                fmap['max_acc'] = acc_report['max_acc']

            if fmap['scale_factor'] != 'N/A' and fmap['scale_factor'] != 1:
                fmap['scale_factor'] = f'1/{fmap["scale_factor"]}'

            super()._change_format_mapping(fmap)
            return fmap

        def _get_header(self) -> str:
            return super()._get_header()

        def write_lut_to_hex(self, file_name: str, lut: LUT, ow: bool = False, target_order: BYTEORDER = BYTEORDER.BIG) -> None:
            return super().write_lut_to_hex(file_name, lut, write_type=HexLutManager.float_to_hex,
                                            ow=ow, target_order=target_order)

        def read_lut_from_hex(self, file_name: str, dtype: np.floating, target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.floating]:
            return super().read_lut_from_hex(file_name, dtype, read_type=HexLutManager.hex_to_float,
                                             target_order=target_order)


class DownSamplerLutManager(HexLutManager):
    def __init__(self, dir: Path):
        super().__init__(dir)

    def _change_format_mapping(self, fmap: Mapping) -> Mapping:
        return super()._change_format_mapping(fmap)

    def _get_header(self) -> str:
        return super()._get_header()

    def write_lut_to_hex(self, file_name: str, lut: LUT, ow: bool = False, target_order: BYTEORDER = BYTEORDER.BIG) -> None:
        return super().write_lut_to_hex(file_name, lut, write_type=HexLutManager.float_to_hex,
                                        ow=ow, target_order=target_order)

    def read_lut_from_hex(self, file_name: str, dtype: np.integer, target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.integer]:
        return super().read_lut_from_hex(file_name, dtype, read_type=HexLutManager.hex_to_float,
                                         target_order=target_order)

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

import sys
import itertools
import re
import numpy as np
import datetime as dt

from typing import assert_never, override
from abc import ABC
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, fields
from pathlib import Path

from Allocator.Interpreter.main.dataclass import LUT, BYTEORDER, LUT_ACC_REPORT, LUT_FN_DEFS, PREC_MODE, TABLE_MODE, QFormat
from Allocator.Interpreter.main.common_utils import join_regex, rename_keys, underline_matches

from Scripts.argparse_helpers import str2num, str2varname, str2frac
from Scripts.exceptions import ExpectedFloatParseException, ExpectedIntParseException
from Scripts.consts import META_INFO


class HexLutManager(ABC):
    __slots__ = ('_entries', 'dir')

    HEADER =('// Coefficient memory for {fn}'
    '\n// ----------------------------------------------'
    '\n//   Bits per coeff.:                {bit_width}'
    '\n//   Q-format:                       {q_format}'
    '\n//   Endianness.:                    {endianness}'
    '\n//   Table mode:                     {table_mode}'
    '\n//   Table size:                     {table_sz}kB'
    '\n//   LOP (level of precision):       {lop}'
    '\n//   Effective scaling factor:       {scale_factor}'
    '\n//'
    '\n//   Stats:'
    '\n//'
    '\n//   [*] Measured Quantization error [*]'
    '\n//\t   Measured avg. accuracy:       {avg_acc}'
    '\n//\t   Min accuracy:                 {min_acc}'
    '\n//\t   Max accuracy:                 {max_acc}'
    '\n//\t   Std:                          {std}'
    '\n//'
    '\n//   [*] Measured THD+N (Total Harmonic Distortion + noise) [*]'
    '\n//\t   Measured avg. THD+N:          {thd_n}'
    '\n//\t   Measured avg. THD+N (dB):     {thd_n_dB}'
    '\n//'
    '\n// ----------------------------------------------'
    '\n//'
    '\n// Each line after this header contains a value (coeff.) corresponding to the function {fn}.'
    '\n// This file was automatically generated with the command:'
    '\n// {cmd}'
    '\n//'
    '\n// *Do not* make any manual changes to this file'
    '\n// File generated @ {ts}'
    '\n//'
    '\n// Author: {author_name} {author_email}'
    '\n//'
    )

    NULL_PLACEHOLDER = 'N/A'

    def __init__(self, dir: Path):
        self.dir = dir

        # Internal list of managed LUT entries
        # Each entry: { 'lut': LUT, 'fmap': Mapping, 'header': str, 'file_name': Optional[str] }
        self._entries: list[dict] = []

    @property
    def luts(self) -> list[LUT] | None:
        if not self._entries:
            return None
        return [entry['lut'] for entry in self._entries]

    @staticmethod
    def _get_expected_header_keys() -> set[str]:
        expected_keys = set(('fn',))
        lns = HexLutManager.HEADER.splitlines()
        for ln in lns:
            match = re.match(r'\/{2}(.+):\s*{[\w_]+}', ln)
            if match:
                key = str2varname(match.group(1))
                expected_keys.add(key)

        return expected_keys

    @staticmethod
    def _comment_newlines_in_format_mapping(fmap: Mapping) -> Mapping:
        for k, v in fmap.items():
            if not isinstance(v, str):
                continue

            lns = v.splitlines()
            if (len_lns := len(lns)) > 1:
                for i in range(1, len_lns):
                    if not lns[i].startswith('//'):
                        lns[i] = f'// {lns[i]}'

            fmap[k] = '\n'.join(lns)

        return fmap

    @staticmethod
    def _base_fmap() -> Mapping:
        return {f.name: HexLutManager.NULL_PLACEHOLDER for f in fields(LUT)}

    @staticmethod
    def _make_header(fmap: Mapping) -> str:
        return HexLutManager.HEADER.format_map(fmap)

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
    def hex_to_dtype(hex_str: str, dtype: np.number,
                      target_order: BYTEORDER = BYTEORDER.BIG) -> np.number:
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
        if len(hex_str) % 2 != 0:
            raise ValueError('Hex string must have an even number of characters.')

        packed_bytes = bytes.fromhex(hex_str)

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

    @staticmethod
    def int_to_hex(i: np.integer, target_order: BYTEORDER = BYTEORDER.BIG) -> str:
        """# Summary

        Converts a numpy n-bit integer (e.g. np.int32, np.uint64) into its raw
        hexadecimal string representation.

        ## Args:
            i: The integer value to convert.
            target_order: The byte order for the output hex string.

        ## Returns:
            A string of hexadecimal characters (e.g., '0000beef').
        """
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

    def _get_valid_file_path(self, file_name: Path | str, ow: bool | None = None) -> Path:
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
        if isinstance(file_name, str):
            file_name = Path(file_name)

        file_path = self.dir / file_name
        if not file_path.suffix:
            file_path = file_path.with_suffix('.hex')
        elif file_path.suffix != '.hex':
            raise ValueError('Lut to hex only supports .hex file extensions')

        if ow is False and file_path.exists():
            raise FileExistsError(f'File already exists at location: {file_path}')

        return file_path

    def _change_format_mapping(self, fmap: Mapping) -> Mapping:
        auth_name, auth_email = META_INFO.AUTHOR_CREDENTIALS
        to_update = {
            'fn': fmap.get('fn').__name__ if hasattr(fmap.get('fn'), '__name__') else None,
            'ts': dt.datetime.now(),
            'endianness': fmap.get('endianness', '').name.lower()\
                if hasattr(fmap.get('endianness'), 'name') else None,
            'author_name': auth_name,
            'author_email': auth_email
        }

        fmap = {k: HexLutManager.NULL_PLACEHOLDER if v is None else v for k,v in fmap.items()}
        fmap.update(to_update)
        return fmap

    def _build_fmap_for_lut(self, lut: LUT, recursive: bool = False) -> Mapping:
        m: dict = HexLutManager._base_fmap()

        if recursive:
            m.update(asdict(lut))
        else:
            m.update({f.name: getattr(lut, f.name) for f in fields(lut)})

        m = self._change_format_mapping(m)
        return HexLutManager._comment_newlines_in_format_mapping(m)

    def add_lut(self, lut: LUT, *, recursive: bool = False, file_name: str | None = None) -> int:
        """Add a LUT to the manager and prepare its header mapping.

        Returns the index of the created entry for later reference.
        """
        fmap = self._build_fmap_for_lut(lut, recursive=recursive)
        header = self._make_header(fmap)
        self._entries.append({'lut': lut, 'fmap': fmap, 'header': header, 'file_name': file_name})
        return len(self._entries) - 1

    def write_lut_to_hex(self, file_name: str, lut: LUT,
                         write_type: Callable[..., str],
                         ow: bool=False,
                         recursive: bool=False,
                         target_order: BYTEORDER = BYTEORDER.BIG) -> None:
        """# Summary

        Writes a lut to a .hex file at the specified file path & with the specified name

        ## Args:
            file_name (str): name of file to write out
            lut (LUT): lut (see: LUT dataclass)
            ow (bool): overwrite files with same name?
            recursive (bool): recursively format? I.e. if true then nested dataclasses will be formatted too for writing
            target_order (BYTEORDER): the byteorder to write out I.e. Big Endian, Little Endian etc.
        """

        lut_to_write = lut.q_format.get_converted(lut.table)

        # Build per-LUT format map and header
        fmap = self._build_fmap_for_lut(lut, recursive=recursive)
        header = self._make_header(fmap)

        file_path = self._get_valid_file_path(file_name=file_name, ow=ow)
        with open(file_path, 'w') as f:
            f.write(header)
            for entry in lut_to_write:
                f.write(f'\n{write_type(entry, target_order=target_order)}')

    def write_all(self, file_namer: Callable[[LUT, int], str],
                  write_type: Callable[..., str],
                  ow: bool=False,
                  recursive: bool=False,
                  target_order: BYTEORDER = BYTEORDER.BIG) -> None:
        """Write all managed LUTs to hex files using the provided naming function."""
        for idx, entry in enumerate(self._entries):
            lut: LUT = entry['lut']
            fname = entry.get('file_name') or file_namer(lut, idx)
            self.write_lut_to_hex(fname, lut, write_type=write_type, ow=ow,
                                   recursive=recursive, target_order=target_order)

    def get_lut(self, index: int | None = None) -> LUT | None:
        """Get a LUT by its index.
        If index is None, return the most recently added LUT.
        """
        if index is None:
            return self._entries[-1]['lut'] if self._entries else None
        return self._entries[index]['lut'] if 0 <= index < len(self._entries) else None

    def _parse_lut_header(self, file_path: Path | str) -> Mapping:
        """Parse the header of a LUT file and return a mapping of its fields."""
        fmap = {}
        with open(file_path, 'r') as f:
            # Get fn from last word of first line
            fn = next(f).split()[-1]
            fmap['fn'] = fn

            header = itertools.takewhile(lambda ln: ln.startswith('//') or ln == '\n', f)

            for ln in header:
                ln = ln.lstrip('//').strip()
                match = re.split(r'\s*:\s*', ln, maxsplit=1)
                match_len = len(match)

                if match_len == 2 and match[1].strip():
                    # Argument (RHS) on same line as keyword (LHS)
                    key, value = match
                    value, key = value.strip(), key.strip()
                elif match_len == 2:
                    # Implies new-line separates the RHS
                    key = match[0]
                    next_non_empty_ln = next((match for ln in f if (match := ln.lstrip('//')).strip()), None)
                    value = next_non_empty_ln
                else:
                    continue

                key = str2varname(key)
                fmap[key] = value

        return fmap

    def _parse_lut_header_with_checks(self, file_path: Path | str) -> Mapping:
        fmap = self._parse_lut_header(file_path=file_path)

        expected = self._get_expected_header_keys()
        if not expected.issubset(fmap.keys()):
            keys_not_found = expected.difference(fmap.keys())
            keys_not_found = join_regex(*keys_not_found, non_capture=False)
            raise ValueError(f'Not all of the expected keys were found in header of {file_path.name}.'
                             f' The following are missing:'
                             f'\n{underline_matches(str(list(expected)), keys_not_found,
                                                    match_all=True, literal=False)}')

        fmap = {k: v for k, v in fmap.items() if k in expected} # Drop any unexpected keys

        # Rename keys to lut kwargs
        rename_keys(fmap, {'lop_level_of_precision': 'lop',
                           'bits_per_coeff': 'bw'})

        # Map enum fields to their values, other edge cases
        table_mode_type: TABLE_MODE = TABLE_MODE.get_subclass_from_name(fmap['fn'])
        fmap['table_mode'] = table_mode_type.get_member_via_name(fmap['table_mode'])
        prec_mode_type: PREC_MODE = PREC_MODE.get_subclass_from_name(fmap['fn'])
        fmap['lop'] = prec_mode_type.get_member_via_name(fmap['lop'])
        fmap['effective_scaling_factor'] = str2frac(fmap['effective_scaling_factor'])
        fn_class_type : LUT_FN_DEFS = LUT_FN_DEFS.get_subclass_from_name(fmap['fn'])
        fmap['fn'] = fn_class_type.get_member_via_name(fmap['fn'])

        fmap['endianness'] = BYTEORDER.get_member_via_name(fmap['endianness'])
        fmap['qformat'] = QFormat(fmap['qformat'])

        # Parse values from remaining strings
        for k, v in fmap.items():
            if not isinstance(v, str):
                continue

            # Parse placeholder values as None
            if v == HexLutManager.NULL_PLACEHOLDER:
                fmap[k] = None

            # Parse numbers (floats, integers)
            try:
                fmap[k] = str2num(v)
            except (ExpectedFloatParseException, ExpectedIntParseException):
                continue

        return fmap

    def read_lut_from_hex(self, file_name: Path | str, dtype: np.number,
                          read_type: Callable[..., np.number],
                          target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.number]:
        file_path = self._get_valid_file_path(file_name=file_name)
        header = self._parse_lut_header_with_checks(file_path) # noqa: F841

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

        @override
        def _change_format_mapping(self, fmap: Mapping) -> Mapping:
            lop = fmap.get('lop')
            if hasattr(lop, 'name'):
                fmap['lop'] = lop.name.lower()

            table_mode = fmap.get('table_mode')
            if hasattr(table_mode, 'name'):
                fmap['table_mode'] = table_mode.name.lower()

            # Expand accuracy report into flat fields
            acc = fmap.pop('_acc_report', None)
            if isinstance(acc, LUT_ACC_REPORT):
                fmap.update({
                    'avg_acc': f'{acc.quant_acc_report.avg_acc:.8f}',
                    'min_acc': f'{acc.quant_acc_report.min_acc:.8f}',
                    'max_acc': f'{acc.quant_acc_report.max_acc:.8f}',
                    'std': f'{acc.quant_acc_report.std:.8f}',
                })

                fmap.update({
                    'thd_n': f'{acc.thd_acc_report.thd_scalar:.8f}',
                    'thd_n_dB': f'{acc.thd_acc_report.thd_dB:.8f}',
                })
            else:
                fmap.update({
                    'avg_acc': HexLutManager.NULL_PLACEHOLDER,
                    'min_acc': HexLutManager.NULL_PLACEHOLDER,
                    'max_acc': HexLutManager.NULL_PLACEHOLDER,
                    'std': HexLutManager.NULL_PLACEHOLDER,
                })

                fmap.update({
                    'thd_n': HexLutManager.NULL_PLACEHOLDER,
                    'thd_n_dB': HexLutManager.NULL_PLACEHOLDER,
                })

            sf = fmap.get('scale_factor')
            if sf != HexLutManager.NULL_PLACEHOLDER and sf is not None and sf != 1:
                fmap['scale_factor'] = f'1/{sf}'

            return super()._change_format_mapping(fmap)

        @override
        def write_lut_to_hex(self, file_name: str, lut: LUT, ow: bool = False, target_order: BYTEORDER = BYTEORDER.BIG) -> None:
            return super().write_lut_to_hex(file_name, lut, write_type=HexLutManager.int_to_hex,
                                            ow=ow, target_order=target_order)

        @override
        def read_lut_from_hex(self, file_name: str, dtype: np.number, target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.number]:
            return super().read_lut_from_hex(file_name, dtype, read_type=HexLutManager.hex_to_int,
                                             target_order=target_order)


class DownSamplerLutManager(HexLutManager):
    def __init__(self, dir: Path):
        super().__init__(dir)

    @override
    def _change_format_mapping(self, fmap: Mapping) -> Mapping:
        return super()._change_format_mapping(fmap)

    @override
    def write_lut_to_hex(self, file_name: Path | str, lut: LUT, ow: bool = False, target_order: BYTEORDER = BYTEORDER.BIG) -> None:
        return super().write_lut_to_hex(file_name, lut, write_type=HexLutManager.float_to_hex,
                                        ow=ow, target_order=target_order)

    @override
    def read_lut_from_hex(self, file_name: Path | str, dtype: np.number, target_order: BYTEORDER = BYTEORDER.NATIVE) -> Sequence[np.number]:
        return super().read_lut_from_hex(file_name, dtype, read_type=HexLutManager.hex_to_float,
                                         target_order=target_order)

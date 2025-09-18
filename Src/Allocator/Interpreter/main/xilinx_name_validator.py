"""
------------------------------------------------------------------------
Filename: 	xilinx_name_validator.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the None module
None
LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""

import importlib
import re

from collections.abc import Sequence
from typing import assert_never
from enum import Enum

from Allocator.Interpreter.main.util_helpers import greater_than_n_regex
from Allocator.Interpreter.main.common_utils import sort_relative_to, underline_first_non_captured_group, underline_matches
from Allocator.Interpreter.main.dataclass import XILINX_FAMILY_CLASSES, XILINX_GEN7_LUT_IDENTIFIERS, XILINX_GENERATION, XILINX_NAME_SCHEME_STRUCTURE, XILINX_SUPPORTED_APU_RPU,\
XILINX_SUPPORTED_ENGINE, XILINX_SUPPORTED_FAMILIES, XILINX_SUPPORTED_LUT_SIZES, XILINX_SUPPORTED_PACKAGES, XILINX_SUPPORTED_SPEED_GRADES,\
XILINX_ULTRASCALE_VALUE_IDENTIFIERS


consts = importlib.import_module('.consts', package='Allocator.Interpreter.main')
META_INFO = consts.META_INFO


class _XilinxNameScheme:

    @classmethod
    def _get_product_meta_for_generation(cls, generation: XILINX_GENERATION) -> Sequence[Enum]:
        """Gets the supported product meta for a given generation."""
        pattern = re.compile(rf'^{generation.name}_\w+$')
        all_attrs = vars(cls)
        matching_attr_names = [name for name in all_attrs if pattern.match(name)]

        group_names = sort_relative_to(matching_attr_names,
                                   {f'{generation.name}_PACKAGES': 0,
                                    f'{generation.name}_FAMILIES': 1,
                                    f'{generation.name}_SPEED_GRADES': 2,
                                    f'{generation.name}_LUT_COUNT': 3,
                                    f'{generation.name}_APU_RPU_TYPE': 4,
                                    f'{generation.name}_ENGINE_TYPE': 5
                                   })
        return [all_attrs[name] for name in group_names]

    @classmethod
    def get_regex_for_generation(cls, generation: XILINX_GENERATION) -> str:
        """Gets the regex for a given generation."""
        groups = cls._get_product_meta_for_generation(generation)
        structure = XILINX_NAME_SCHEME_STRUCTURE(*groups, product_generation=generation)
        return structure.get_regex_for_generation(generation)

    @classmethod
    def get_validated_regex_for_generation(cls, string: str, generation: XILINX_GENERATION) -> Sequence[str]:
        """Validates a regex for a given generation."""
        groups_regex = cls.get_regex_for_generation(generation)
        string_no_ops = re.sub(r'[^\w\s]', '', string)

        matches = underline_first_non_captured_group(groups_regex, string_no_ops)
        if isinstance(matches, str):
            raise ValueError(f'Invalid XILINX product name: {matches}')

        # Check lut size supported
        if generation == XILINX_GENERATION.GEN7:
            lut_sz: XILINX_SUPPORTED_LUT_SIZES = getattr(XILINX_SUPPORTED_LUT_SIZES, generation.name)
            if lut_sz.is_supported(int(matches[3])):
                raise ValueError(f'Invalid XILINX product name (must provide a lut size >= {lut_sz.value}):'
                                 f'\n{underline_matches(string, matches[3])}'
                                 )

        return matches

    @classmethod
    def get_generation_from_name(cls, name: str) -> XILINX_GENERATION:
        prefix = re.match(r'\w{1,2}', name)
        if prefix is None:
            raise ValueError('Could not parse a generation value E.g.'
                             ' The name must start with either a product or family class identifier.'
                             )
        prefix = prefix.group(0)

        try:
            family: XILINX_FAMILY_CLASSES = XILINX_FAMILY_CLASSES.get_member_via_value(prefix)
            return family.get_generation()
        except ValueError:
            # Indicates the family class didn't come first, as no family class could be found at the start of the name
            # => the generation value must occur in the 2nd position
            generation_digit = re.search(rf'(?:{prefix})(\d+)', name)
            if generation_digit is None:
                raise ValueError('Could not parse a generation value, even though the product identifier came first E.g.'
                                 f'{underline_matches(name, r'(?:\w{2})', literal=False)}'
                                 )
            generation_digit = int(generation_digit.group(1))
            return XILINX_GENERATION.get_member_via_value(generation_digit)

    def __init__(self, names: Sequence[str]):
        self.names = []
        for name in names:
            validated_names = self.get_validated_names(name)
            if isinstance(validated_names, list):
                self.names.extend(validated_names)
            elif isinstance(validated_names, str):
                self.names.append(validated_names)
            else:
                assert_never(type(name))

    def __str__(self):
        result = ['---Supported XILINX devices---']
        result.append(', '.join(self.names))
        result[1] = '(' + result[1] + ')'
        if META_INFO.DEBUG:
            for generation in XILINX_GENERATION:
                result.append(f'---{generation.name} support---')
                product_meta_classes = self._get_product_meta_for_generation(generation)
                for meta_class in product_meta_classes:
                    if hasattr(meta_class, generation.name):
                        supported_member = getattr(meta_class, generation.name)
                        result.append(f'\t{meta_class.__name__}: {supported_member.value}')
        return '\n\n'.join(result) + '\n'

    def get_validated_names(self, name: str) -> Sequence[str]:
        """Tries to validate a name against all supported generations."""
        try:
            generation = self.get_generation_from_name(name)
            captured_groups = self.get_validated_regex_for_generation(name, generation)
            return self.generate_names_from_regex(name, generation, captured_groups)
        except (ValueError, NotImplementedError) as e:
            raise(e)

    def generate_names_from_regex(self, string: str, generation: XILINX_GENERATION,
                                  captured_groups: Sequence[str]) -> Sequence[str] | str:
        result = []
        if generation == XILINX_GENERATION.ULTRASCALE:
            # Handle the '+' character next to the value index indentifier
            # Which is interpreted to mean 'select all products above that value index'
            value_index_identifier = re.search(r'^.+(\d+)\+', string)
            if value_index_identifier is not None:
                value_index = int(value_index_identifier.group(1))
                product_family = captured_groups[1]
                value_indices_gt_regex = rf'^{product_family}_VI({greater_than_n_regex(value_index)})\w?$'

                # Get all value identifiers above the product index using the naming scheme
                to_replace = XILINX_ULTRASCALE_VALUE_IDENTIFIERS.get_members_from_pattern(value_indices_gt_regex)

        elif generation == XILINX_GENERATION.GEN7:
            # Handle the '+' character next to the LUT size indentifier
            # Which is interpreted to mean 'select all products above that lut size'
            lut_index_identifier = re.search(r'(\d+)\+', string)
            if lut_index_identifier is not None:
                product_family = captured_groups[2]
                lut_indices_regex = rf'^{product_family}_LI\d+\w?$'
                lut_index = int(lut_index_identifier.group(1))
                lut_indices = XILINX_GEN7_LUT_IDENTIFIERS.get_members_from_pattern(lut_indices_regex)
                to_replace = [member for member in lut_indices if member.value >= lut_index]

        for m in to_replace:
            result.append(re.sub(r'\d+\+', str(m.value), string))

        return result


class XilinxDeviceSet(_XilinxNameScheme):
    GEN7_PACKAGES = XILINX_SUPPORTED_PACKAGES
    GEN7_FAMILIES = XILINX_SUPPORTED_FAMILIES
    GEN7_SPEED_GRADES = XILINX_SUPPORTED_SPEED_GRADES
    GEN7_LUT_COUNT = XILINX_SUPPORTED_LUT_SIZES
    GEN7_APU_RPU_TYPE = None
    GEN7_ENGINE_TYPE = None

    ULTRASCALE_PACKAGES = XILINX_SUPPORTED_PACKAGES
    ULTRASCALE_FAMILIES = XILINX_SUPPORTED_FAMILIES
    ULTRASCALE_SPEED_GRADES = XILINX_SUPPORTED_SPEED_GRADES
    ULTRASCALE_LUT_COUNT = None
    ULTRASCALE_APU_RPU_TYPE = XILINX_SUPPORTED_APU_RPU
    ULTRASCALE_ENGINE_TYPE = XILINX_SUPPORTED_ENGINE

import pytest

import Allocator.Interpreter.extendedenum as ext
from Allocator.Interpreter.extendedenum import ExtendedEnum


@pytest.fixture
def base_enum():
	class Base(ExtendedEnum):
		pass

	return Base


@pytest.fixture
def unique_subclasses(base_enum):
	Base = base_enum

	class SubA(Base):
		FOO = 1

	class SubB(Base):
		BAR = 2

	return Base, SubA, SubB


@pytest.fixture
def ambiguous_subclasses(base_enum):
	Base = base_enum

	class SubA(Base):
		CLASH = 1

	class SubB(Base):
		CLASH = 2

	return Base, SubA, SubB


def test_get_subclass_from_name_unique(unique_subclasses):
	Base, SubA, SubB = unique_subclasses

	assert Base.get_subclass_from_name('FOO') is SubA
	assert Base.get_subclass_from_name('BAR') is SubB
	# Case-insensitive name lookup via __contains__ in metaclass
	assert Base.get_subclass_from_name('foo') is SubA


def test_get_subclass_from_name_none(base_enum):
	class SubA(base_enum):
		FOO = 1

	assert base_enum.get_subclass_from_name('MISSING') is None


def test_get_subclass_from_name_ambiguous_raises(ambiguous_subclasses, monkeypatch):
	Base, SubA, SubB = ambiguous_subclasses

	# Patch join_regex used by extendedenum to avoid type issues when formatting error message
	def _safe_join_regex(*items, **kwargs):
		return '|'.join(getattr(i, '__name__', str(i)) for i in items)

	monkeypatch.setattr(ext, 'join_regex', _safe_join_regex, raising=True)

	with pytest.raises(ValueError, match=r'Ambiguous .* subclass name: CLASH'):
		Base.get_subclass_from_name('CLASH')

"""
------------------------------------------------------------------------
Filename: 	singleton.py

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

import warnings

from collections.abc import Hashable
from abc import ABCMeta


class _SingletonControlMeta(ABCMeta):
    """Base metaclass that accepts a 'frozen' class kwarg and sets a flag on the class."""
    def __new__(mcls, name, bases, namespace, **kwargs):
        # Inherit frozen from bases if not provided explicitly
        inherited = any(bool(getattr(b, '__singleton_frozen__')) for b in bases if hasattr(b, '__singleton_frozen__'))

        if 'frozen' in kwargs:
            frozen = bool(kwargs.pop('frozen'))
        else:
            frozen = bool(namespace.get('__singleton_frozen__', inherited if inherited else False))

        cls = super().__new__(mcls, name, bases, namespace)
        setattr(cls, '__singleton_frozen__', frozen)
        return cls


class SingletonMetaInstance(_SingletonControlMeta):
    """Create singleton per class instance"""
    __slots__ = ()

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]


class SingletonMetaSubclass(_SingletonControlMeta):
    """Create singleton based on subclass"""
    __slots__ = ()

    _instance = None
    _ctor_sig = None

    def __call__(cls, *args, **kwargs):
        """Always return the same instance per subclass; __singleton_frozen__ controls refresh."""

        def _make_hashable(obj):
            """Best-effort: turn possibly-unhashable objects into a hashable representation."""
            if isinstance(obj, Hashable):
                return ('H', obj)
            dtype = getattr(obj, 'dtype', None)
            shape = getattr(obj, 'shape', None)
            tobytes = getattr(obj, 'tobytes', None)
            if dtype is not None and shape is not None and callable(tobytes):
                try:
                    b = obj.tobytes()
                except Exception:
                    b = repr(obj).encode('utf-8', errors='ignore')
                return ('ND', str(dtype), tuple(shape), hash(b))
            if isinstance(obj, dict):
                return ('D', tuple(sorted((k, _make_hashable(v)) for k, v in obj.items())))
            if isinstance(obj, (list, tuple)):
                return ('T', tuple(_make_hashable(e) for e in obj))
            if isinstance(obj, (set, frozenset)):
                return ('S', tuple(sorted(_make_hashable(e) for e in obj)))
            return ('R', repr(obj))

        def _sig_hash(a, kw):
            try:
                a_h = tuple(_make_hashable(x) for x in a)
                kw_h = tuple(sorted((k, _make_hashable(v)) for k, v in kw.items()))
                return hash(('SIG', a_h, kw_h))
            except Exception:
                return hash(('IDSIG', tuple(id(x) for x in a), tuple(sorted((k, id(v)) for k, v in kw.items()))))

        if cls._instance is None:
            instance = super().__call__(*args, **kwargs)
            setattr(cls, '_instance', frozenset((instance,)))
            setattr(cls, '_ctor_sig', _sig_hash(args, kwargs))
            return instance

        inst_set = getattr(cls, '_instance', None)
        if inst_set is None:
            raise ValueError(f'Expected instance {cls.__name__} to be in the singleton instance cache.')
        if len(inst_set) != 1:
            raise TypeError(f'Expected singleton instance {cls.__name__} to be unique.'
                            f'Instead instance cache contains {list(inst_set)}')
        instance = next(iter(inst_set))

        cls_frozen: bool | None = getattr(cls, '__singleton_frozen__', None)
        if cls_frozen is None:
            cls_frozen = any(bool(getattr(b, '__singleton_frozen__', False)) for b in cls.__mro__[1:])

        if not cls_frozen:
            cls.__init__(instance, *args, **kwargs)
        else:
            new_sig_hsh = _sig_hash(args, kwargs)
            old_sig_hsh = getattr(cls, '_ctor_sig', None)
            if old_sig_hsh is not None and new_sig_hsh != old_sig_hsh:
                warnings.warn(
                    f'{cls.__name__} is frozen; ignoring new constructor args/kwargs.'
                    '\n This may be intentional behaviour if the first subclass consumer of'
                    f' {cls.__bases__[0].__name__}, with MRO:'
                    f'\n\n{cls.__bases__[0].__mro__[1:]}\n\n'
                    'was the intended one. Note: all subsequent children will now return this cached instance, '
                    'disregarding any further calls.\n'
                    f'First call hash={old_sig_hsh:X}, newest call hash={new_sig_hsh:X}\n'
                )
            setattr(cls, '_ctor_sig', old_sig_hsh if old_sig_hsh is not None else new_sig_hsh)

        return instance


class _SingletonBase:
    """Base class for all singleton types."""
    def __init_subclass__(cls, *, frozen: bool = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if frozen is not None:
            cls.__singleton_frozen__ = bool(frozen)


class SingletonInstanceBase(_SingletonBase, metaclass=SingletonMetaInstance):
    """Base class for instance-level singletons."""


class SingletonSubclassBase(_SingletonBase, metaclass=SingletonMetaSubclass):
    """Base class for subclass-level singletons."""

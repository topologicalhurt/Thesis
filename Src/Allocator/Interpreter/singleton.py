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

import itertools
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
        """ Always return the same instance per subclass;
        __singleton_frozen__ controls whether to refresh state"""

        # Check constructor arguments are hashable
        if cls._instance is None:
            for a, b in itertools.zip_longest(args, kwargs.values()):
                if not (a_is_hashable := isinstance(a, Hashable)) or not isinstance(b, Hashable):
                    err_term = a if not a_is_hashable else b
                    raise TypeError(f'Singleton metaclass received unsupported keyword argument: {err_term!r}. '
                                    f'Hashable types are required.')

            instance = super().__call__(*args, **kwargs)
            setattr(cls, '_instance', frozenset((instance,)))

            # Record construction signature
            sig = (frozenset(args), frozenset(kwargs.items()))
            setattr(cls, '_ctor_sig', sig)

            return instance

        instance = getattr(cls, '_instance', None)

        if instance is None:
            # This shouldn't trigger as cls._instance is immutable. Probably interference from GC.
            raise ValueError(f'Expected instance {cls.__name__} to be in the singleton instance cache.')

        if len(instance) != 1:
            # This shouldn't trigger as cls._instance is immutable. Improper initialization probably occurred.
            raise TypeError(f'Expected singleton instance {cls.__name__} to be unique.'
                            f'Instead instance cache contains {list(instance)}')

        instance = next(iter(instance))

        # Robust frozen detection: prefer explicit flag; otherwise inherit from MRO
        cls_frozen: bool | None = getattr(cls, '__singleton_frozen__', None)
        if cls_frozen is None:
            cls_frozen = any(bool(getattr(b, '__singleton_frozen__', False)) for b in cls.__mro__[1:])

        if not cls_frozen:
            # Re-invoke the subclass __init__ to refresh attributes w/o reallocating
            cls.__init__(instance, *args, **kwargs)
        else:
            """Frozen: ignore new args/kwargs; if they differ, warn for visibility.
            This is a relatively expensive path, so if frozen = True for the concrete baseclass
            it's best not to provide any new args to subclassed calls as we expect the global instance
            to be returned from instance cache."""

            new_sig = (frozenset(args), frozenset(kwargs.items()))
            old_sig = getattr(cls, '_ctor_sig', None)
            new_sig_hsh, old_sig_hsh = hash(new_sig), hash(old_sig) if old_sig is not None else None

            if old_sig is not None and new_sig_hsh != old_sig_hsh:
                warnings.warn(
                    f'{cls.__name__} is frozen; ignoring new constructor args/kwargs.'
                    '\n This may be intentional behaviour if the first subclass consumer of'
                    f' {cls.__bases__[0].__name__}, with MRO:'
                    f'\n\n{cls.__bases__[0].__mro__[1:]}\n\n'
                    'was the intended one. Note: all subsequent children will now return this cached instance, '
                    'disregarding any further calls.\n'
                    f'First call hash={old_sig_hsh:X}, newest call hash={new_sig_hsh:X}\n'
                )

            # Keep the original signature
            setattr(cls, '_ctor_sig', old_sig if old_sig is not None else new_sig)

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

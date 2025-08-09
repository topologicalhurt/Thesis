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

class SingletonMetaInstance(type):
    """Create singleton per class instance"""
    __slots__ = ()
    _instances = {}
    _initialized = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
            cls._initialized[cls] = False

        instance = cls._instances[cls]

        # Only call __init__ once per class type
        if not cls._initialized[cls]:
            instance.__init__(*args, **kwargs)
            cls._initialized[cls] = True

        return instance


class SingletonMetaSubclass(type):
    """Create singleton based on subclass"""
    __slots__ = ()
    _instances = {}
    _initialized = {}

    def __call__(cls, *args, **kwargs):
        # Only create one instance per class, always return the same one
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class SingletonInstance(metaclass=SingletonMetaInstance):
    def __init__(self, *args, **kwargs):
        self.initialized = True
        super().__init__(*args, **kwargs)

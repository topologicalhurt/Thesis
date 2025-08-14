import numpy as np

from abc import ABC, abstractmethod
from dataclasses import dataclass

from Allocator.Interpreter.dataclass import SIGNAL_METRIC, SIGNAL_TYPE
from Allocator.Interpreter.singleton import SingletonSubclassBase


class SignalStatistic(ABC, SingletonSubclassBase, frozen=False):

    __slots__ = ('_signal_metric', '_signal', '_signal_type', '_signal_norm',
    '_signal_name', '_signal_mean', '_is_periodic', '_unbiased_signal', '_unbiased_signal_norm')

    def __init__(self, signal: np.ndarray[np.number], signal_type: SIGNAL_TYPE, signal_name: str | None = None):
        self._signal = signal
        self._signal_type = signal_type
        self._signal_name = signal_name

        # Defer to property time creation, I.e. lazy load
        self._signal_metric = None
        self._signal_mean = None
        self._signal_norm = None
        self._is_periodic = None
        self._unbiased_signal = None
        self._unbiased_signal_norm = None

    @abstractmethod
    def get_report(self) -> dataclass:
        pass

    @abstractmethod
    def get_base_report(self) -> dataclass:
        pass

    @property
    def signal(self):
        return self._signal

    @property
    def signal_name(self):
        return self._signal_name

    @property
    def signal_type(self):
        return self._signal_type

    @property
    def signal_metric(self):
        if self._signal_metric is None:
            self._signal_metric = SIGNAL_METRIC(
                signal=self._signal,
                signal_type=self._signal_type,
                signal_name=self._signal_name
            )
        return self._signal_metric

    @property
    def signal_mean(self):
        if self._signal_mean is None and self.signal is not None:
            self._signal_mean = np.mean(self.signal_metric.signal)
        return self._signal_mean

    @property
    def signal_norm(self):
        if self._signal_norm is None and self.signal is not None:
            self._signal_norm =  np.sum(self.signal**2) if self.signal.size > 0 else 1.0
        return self._signal_norm

    @property
    def is_periodic(self):
        if self._is_periodic is None and self.signal is not None:
            self._is_periodic = self.signal_metric.signal_type == SIGNAL_TYPE.TRIG\
                  and self.signal_metric.signal_name in ('sin', 'cos', 'tan')
        return self._is_periodic

    @property
    def unbiased_signal(self):
        if self._unbiased_signal is None and self.signal is not None:
            self._unbiased_signal = self.signal_metric.signal - self.signal_mean
        return self._unbiased_signal

    @property
    def unbiased_signal_norm(self):
        if self._unbiased_signal_norm is None and self.unbiased_signal is not None:
            us = self.unbiased_signal
            self._unbiased_signal_norm = np.sum(us**2) if us.size > 0 else 1.0
        return self._unbiased_signal_norm

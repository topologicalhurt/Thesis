import warnings
import functools

from collections.abc import Callable
from typing import TypeVar, ParamSpec


rT = TypeVar('rT')
pT = ParamSpec('pT')
def deprecated(func: Callable[pT, rT]) -> Callable[pT, rT]:
    """# Summary

    Use this decorator to mark functions as deprecated.
    Every time the decorated function runs, it will emit
    a "deprecation" warning.

    Credit for this function goes to:
    https://stackoverflow.com/a/30253848/10019450

    Included under CC BY-SA 4.0
    https://creativecommons.org/licenses/by-sa/4.0/
    """
    @functools.wraps(func)
    def wrapped(*args: pT.args, **kwargs: pT.kwargs):
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn('Call to a deprecated function {}.'.format(func.__name__),
                      category=DeprecationWarning,
                      stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter
        return func(*args, **kwargs)
    return wrapped


def warning(message_template: str) -> Callable[[Callable[pT, rT]], Callable[pT, rT]]:
    """ # Summary

    A decorator factory that takes a message template and prints a warning.

    The message_template is a string that can be formatted with details from
    the function call. The following placeholders are available:
    - {f_name}: The name of the decorated function.
    - {result}: The return value of the function call.
    - {args}: The tuple of positional arguments.
    - {kwargs}: The dictionary of keyword arguments.

    ## Args:
        message_template: A string to be formatted with call details.

    ## Returns:
        A decorator that can be applied to a function.
    """
    def decorator(func: Callable[pT, rT]) -> Callable[pT, rT]:
        @functools.wraps(func)
        def wrapped(*args: pT.args, **kwargs: pT.kwargs):
            result = func(*args, **kwargs)

            format_context = {
                'f_name': func.__name__,
                'result': result,
                'args': args,
                'kwargs': kwargs
            }

            print(f'⚠️ Warning: {message_template.format(**format_context)}\n')
            return result
        return wrapped
    return decorator

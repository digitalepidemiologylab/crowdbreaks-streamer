# Modified from:
# https://stackoverflow.com/questions/50563546/validating-detailed-types-in-python-dataclasses

import typing
from functools import wraps
from dataclasses import fields, is_dataclass


def _find_type_origin(type_hint):
    if isinstance(type_hint, typing._SpecialForm):
        # case of typing.Any, typing.ClassVar, typing.Final, typing.Literal,
        # typing.NoReturn, typing.Optional, or typing.Union without parameters
        yield typing.Any
        return

    actual_type = typing.get_origin(type_hint) or type_hint
    if isinstance(actual_type, typing._SpecialForm):
        # case of typing.Union[...] or typing.ClassVar[...] or ...
        for origins in map(_find_type_origin, typing.get_args(type_hint)):
            yield from origins
    else:
        yield actual_type


def _check_types(args):
    for field in fields(args[0]):
        type_hint = typing.Any if field.type is None else field.type
        value = getattr(args[0], field.name)
        actual_types = tuple(
            origin
            for origin in _find_type_origin(type_hint)
            if origin is not typing.Any)
        if actual_types and not isinstance(value, actual_types):
            raise TypeError(
                f"Expected type '{type_hint}' for argument '{field.name}' "
                f"but received type '{type(value)}' instead.")


def enforce_types(object):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            _check_types(args)
        return wrapper

    if is_dataclass(object):
        object.__init__ = decorate(object.__init__)
        return object
    else:
        raise TypeError('This decorator can only be used on classes.')

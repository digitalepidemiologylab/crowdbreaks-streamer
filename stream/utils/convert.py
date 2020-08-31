import typing
from functools import wraps
from dataclasses import fields, is_dataclass

from enforce_types import _find_type_origin


def _check_types(args, converter=None):
    if converter is None:
        converter = {}
    for field in fields(args[0]):
        type_hint = typing.Any if field.type is None else field.type
        value = getattr(args[0], field.name)
        actual_types = tuple(
            origin
            for origin in _find_type_origin(type_hint)
            if origin is not typing.Any)
        if actual_types and not isinstance(value, actual_types):
            try:
                field_converter = converter[field.type]
            except KeyError:
                raise TypeError(
                    f"Expected type '{type_hint}' for argument '{field.name}' "
                    f"but received type '{type(value)}' instead.")
            args[0].__dict__[field.name] = field_converter(value)
    return args


class convert(object):
    def __init__(self, converter=None):
        self.converter = {} if converter is None else converter

    def __call__(self, object):
        def decorate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                args = _check_types(args, self.converter)
            return wrapper

        if is_dataclass(object):
            object.__init__ = decorate(object.__init__)
            return object
        else:
            raise TypeError('This decorator can only be used on dataclasses.')

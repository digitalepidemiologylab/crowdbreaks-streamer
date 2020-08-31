import pytest

from enum import Enum
from dataclasses import dataclass

from stream.utils.convert import convert
from stream.utils.enforce_types import enforce_types


def test_convert():
    Color = Enum('Color', 'RED GREEN BLUE')
    converter = {Color: lambda x: Color[x]}

    @convert(converter=converter)
    @dataclass(frozen=True)
    class Apple:
        color: Color
        taste: str

    apple = Apple(**{'color': 'GREEN', 'taste': 'sweet'})
    assert apple.color == Color.GREEN, 'Incorrect conversion.'
    with pytest.raises(KeyError):
        Apple(**{'color': 'PURPLE', 'taste': 'sweet'})

    # Can only be used on dataclasses
    with pytest.raises(TypeError):
        @convert(converter=converter)
        class PlainApple:
            def __init__(self, color, taste):
                self.color = color
                self.taste = taste


def test_enforce_types():
    Color = Enum('Color', 'RED GREEN BLUE')

    @enforce_types
    @dataclass(frozen=True)
    class Apple:
        color: Color
        taste: str

    Apple(**{'color': Color.RED, 'taste': 'sweet'})
    Apple(**{'color': Color.GREEN, 'taste': 'sweet'})
    Apple(**{'color': Color.BLUE, 'taste': 'sweet'})
    with pytest.raises(TypeError):
        Apple(**{'color': 'green', 'taste': 'sweet'})
    with pytest.raises(TypeError):
        Apple(**{'color': Color.RED, 'taste': 10})

    # Can only be used on classes
    with pytest.raises(TypeError):
        @enforce_types
        def apple():
            pass


def test_convert_enforce_types_compatibility():
    Color = Enum('Color', 'RED GREEN BLUE')
    converter = {Color: lambda x: Color[x]}

    @enforce_types
    @convert(converter=converter)
    @dataclass(frozen=True)
    class Apple:
        color: Color
        taste: str

    Apple(**{'color': 'GREEN', 'taste': 'sweet'})
    with pytest.raises(KeyError):
        Apple(**{'color': 'green', 'taste': 'sweet'})
    with pytest.raises(TypeError):
        Apple(**{'color': 'GREEN', 'taste': 10})

    # Don't work in a different order
    @convert(converter=converter)
    @enforce_types
    @dataclass(frozen=True)
    class ReverseApple:
        color: Color
        taste: str

    with pytest.raises(TypeError):
        ReverseApple(**{'color': 'GREEN', 'taste': 'sweet'})

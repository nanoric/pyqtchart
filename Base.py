from enum import Enum
from typing import TYPE_CHECKING, TypeVar, Union

from PyQt5.QtGui import QColor

if TYPE_CHECKING:
    pass

T = TypeVar("T")

ColorType = Union[
    str,  # "red", "#RGB", "#RRGGBB", "#AARRGGBB", "#RRRGGGBBB", "#RRRRGGGGBBBB"
    int,  # Qt.GlobalColor
    QColor,  # QtCore.QColor
    None,  # Don't draw
]


class Orientation(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


class TickType(Enum):
    VALUE = 0  # label is bound to a value
    BAR = 1  # label is bound to a bar( a range of value )


class TickPosition(Enum):
    """
    indicate where to show a label for TickType == BAR
    """
    BEGIN = 0
    MID = 1
    END = 2


class TickSource(Enum):
    """
    indicate where a label value comes from if TickType == BAR
    """
    BEGIN = 0
    MID = 1
    END = 2



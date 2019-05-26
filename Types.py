from typing import Union

from PyQt5.QtGui import QColor

ColorType = Union[
    str,  # "red", "#RGB", "#RRGGBB", "#AARRGGBB", "#RRRGGGBBB", "#RRRRGGGGBBBB"
    int,  # Qt.GlobalColor
    QColor,  # QtCore.QColor
    None,  # Don't draw
]



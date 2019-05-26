from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, IntFlag, unique
from typing import TYPE_CHECKING, Tuple, Union, Dict, Optional

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QFont

if TYPE_CHECKING:
    from DrawerConfig import DrawConfig
    from Types import ColorType


class Orientation(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


def _generate_sequence(begin, end, step):
    """输出[start, end)中的序列"""
    i = begin
    while i < end:
        yield i
        i += step


class Axis:
    def __init__(self, orientation: Orientation):
        self.orientation = orientation

        self.grid_color: "ColorType" = Qt.lightGray

        self.label_color: "ColorType" = Qt.black
        self.label_font: QFont = QFont()
        # margin to plot_area, right for Vertical Axis, top for Horizontal
        self.label_margin: int = 2

    # @virtual
    def prepare_draw(self, config: "DrawConfig"):
        pass

    @abstractmethod
    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        pass

    @abstractmethod
    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        pass


class StringAxis(Axis):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)

        self.strings: Dict[float, str] = {}  # sorted value=>label mapping

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        if self.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        if self.orientation is Orientation.VERTICAL:
            return self.draw_labels_vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_labels_horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for value, label in self.strings.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for value, label in self.strings.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            left_point = QPointF(grid_left, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)

    def draw_labels_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1

        for value, label in self.strings.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)

            text = f"{value:.2f}"
            text_pos = QRectF(0, ui_y - 10, label_right - self.label_margin, 20)
            painter.drawText(text_pos, Qt.AlignRight | Qt.AlignVCenter, text)
        pass

    def draw_labels_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1
        label_width = 100 # assume no label is longer than this
        label_height = 100  # assume no label is higher than this

        for value, label in self.strings.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)

            text = f"{value:.2f}"
            text_pos = QRectF(ui_x - label_width/2, label_top + self.label_margin,
                              label_width, label_height)
            painter.drawText(text_pos, Qt.AlignTop | Qt.AlignHCenter, text)


class StringBarAxis(Axis):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        # sorted [begin, end)=>label mapping
        self.strings: Dict[Tuple[float, Optional[float]], str] = {}

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        grid_color = self.grid_color
        orientation = self.orientation

        if grid_color is not None:
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.setPen(QColor(grid_color))
            if orientation is Orientation.VERTICAL:
                return self.draw_grid_vertical(config, painter)
            if orientation is Orientation.HORIZONTAL:
                return self.draw_grid_horizontal(config, painter)

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        label_color = self.label_color
        orientation = self.orientation

        if label_color is not None:
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.setPen(QColor(label_color))
            painter.setFont(self.label_font)
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.setPen(QColor(label_color))
            if orientation is Orientation.VERTICAL:
                return self.draw_labels_vertical(config, painter)
            if orientation is Orientation.HORIZONTAL:
                return self.draw_labels_horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for value, label in self.strings.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for value, label in self.strings.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            left_point = QPointF(grid_left, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)

    def draw_labels_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1

        for value, label in self.strings.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)

            text = f"{value:.2f}"
            text_pos = QRectF(0, ui_y - 10, label_right - self.label_margin, 20)
            painter.drawText(text_pos, Qt.AlignRight | Qt.AlignVCenter, text)
        pass

    def draw_labels_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1
        label_width = 100 # assume no label is longer than this
        label_height = 100  # assume no label is higher than this

        for value, label in self.strings.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)

            text = f"{value:.2f}"
            text_pos = QRectF(ui_x - label_width/2, label_top + self.label_margin,
                              label_width, label_height)
            painter.drawText(text_pos, Qt.AlignTop | Qt.AlignHCenter, text)


class ValueAxis(StringAxis):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        self.tick_count: int = 10
        self.format: str = "%.2f"

    # @virtual
    def prepare_draw(self, config: "DrawConfig"):
        if self.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high
        step = (end - begin) / self.tick_count
        self.strings = {
            value: self.format % value
            for value in _generate_sequence(begin, end, step)
        }



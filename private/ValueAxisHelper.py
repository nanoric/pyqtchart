from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainter, QTransform

from Base import Orientation, TickPosition, TickSource
from Drawer import DrawConfig

if TYPE_CHECKING:
    from Axis import AutoTickAxisBase


def _generate_sequence(begin, end, step):
    """output a sequence between [start, end)"""
    i = begin
    while i < end:
        yield i
        i += step


class AxisHelper(ABC, WorldTransformStack):

    def __init__(self, axis: "AutoTickAxisBase"):
        super().__init__()
        self.axis = axis
        self._last_transform = None

    @abstractmethod
    def prepare_draw(self, config: "DrawConfig", painter: "QPainter"):
        raise NotImplementedError()

    @abstractmethod
    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    @abstractmethod
    def draw_labels_(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


class ValueAxisHelper(AxisHelper):

    def __init__(self, axis: "AutoTickAxisBase"):
        super().__init__(axis)
        self._label_for_values: Dict[float, QRectF] = {}

    def prepare_draw(self, config: "DrawConfig", painter: "QPainter"):
        axis = self.axis

        if axis.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high

        step = (end - begin) / axis.label_count

        if axis.orientation is Orientation.VERTICAL:
            begin += step  # skip the lowest tick which is useless & can never be fully printed

        self._label_for_values: Dict[float, QRectF] = {
            value: axis.label_bounding_rect_for_value(value, painter)
            for value in _generate_sequence(begin,
                                            end,
                                            step)
        }

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_labels_(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_labels__vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_labels__horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for value, _ in self._label_for_values.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for value, _ in self._label_for_values.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            left_point = QPointF(grid_left, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)

    def draw_labels__horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1 + self.axis.label_spacing_to_plot_area

        for value, tick in self._label_for_values.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            label_width = tick.height()

            pos = QPointF(ui_x - label_width,
                          label_top,
                          )

            self.switch_to_pos(pos, painter)
            self.axis.draw_label_for_value(value, painter)
            self.switch_back(painter)

    def draw_labels__vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1 - self.axis.label_spacing_to_plot_area

        for value, rect in self._label_for_values.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            label_width = rect.width()
            label_height = rect.height()

            pos = QPointF(
                label_right - label_width,
                ui_y - label_height / 2)
            self.switch_to_pos(pos, painter)
            self.axis.draw_label_for_value(value, painter)
            self.switch_back(painter)


@dataclass()
class BarInfo:
    label_value: float
    label_pos: float
    head: float
    tail: float
    rect: QRectF


class BarAxisHelper(AxisHelper):

    def __init__(self, axis: "AutoTickAxisBase"):
        super().__init__(axis)

        # intermediate variables
        self._grid_tail_length: int = 5
        self._bars: List[BarInfo] = []
        self._grid_spacing_in_drawer: Optional[float] = None

    def prepare_draw(self, config: "DrawConfig", painter):
        axis = self.axis

        # initialize begin, end & step & grid_tail_length
        if axis.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
            self._grid_spacing_in_drawer = config.drawing_cache.ui_width_to_drawer(
                self.axis.label_spacing_to_grid
            )
        else:
            begin, end = config.y_low, config.y_high
            self._grid_spacing_in_drawer = config.drawing_cache.ui_height_to_drawer(
                self.axis.label_spacing_to_grid
            )

        step = (end - begin) / axis.label_count

        # generate bars
        self._bars = [
            self._get_bar_info(bar_head, step, config, painter)
            for bar_head in _generate_sequence(begin, end, step)
        ]

    def _get_bar_info(self, bar_head, step, config, painter):
        value_source = self.axis.label_source
        pos_source = self.axis.label_position
        bar_tail = bar_head + step
        bar_mid = (bar_head + bar_tail) / 2
        if value_source == TickSource.BEGIN:
            label_value = bar_head
        elif value_source == TickSource.MID:
            label_value = bar_mid
        else:
            label_value = bar_tail
        rect = self.axis.label_bounding_rect_for_bar(label_value, bar_head, bar_tail, painter)
        ui_width_half = config.drawing_cache.ui_width_to_drawer(rect.width())
        if pos_source == TickPosition.BEGIN:
            label_pos = bar_head + self._grid_spacing_in_drawer
        elif pos_source == TickPosition.MID:
            label_pos = bar_mid - ui_width_half / 2
        else:
            label_pos = bar_tail - ui_width_half - self._grid_spacing_in_drawer
        return BarInfo(label_value, label_pos, bar_head, bar_tail, rect)

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_labels_(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_labels__vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_labels__horizontal(config, painter)

    def _get_grid_tail_length(self, bar):
        if self.axis.grid_tail_length is None:
            if self.axis.orientation is Orientation.HORIZONTAL:
                return bar.rect.height()
            else:
                return bar.rect.width()
        return self.axis.grid_tail_length

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        if not self._bars:
            return
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        def draw_line(ui_x, bar):
            grid_tail_length = self._get_grid_tail_length(bar)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom + grid_tail_length)
            painter.drawLine(top_point, bottom_point)

        for bar in self._bars:
            begin, end = bar.head, bar.tail
            ui_x = drawing_cache.drawer_x_to_ui(begin)
            draw_line(ui_x, bar)

        bar = self._bars[-1]
        ui_x = drawing_cache.drawer_x_to_ui(bar.tail)
        if ui_x < drawing_cache.plot_area.right():
            draw_line(ui_x, bar)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        if not self._bars:
            return
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - self._grid_tail_length
        grid_right = drawing_cache.plot_area.right() - 1

        def draw_line(ui_y, bar):
            window_bottom: float = painter.window().bottom()
            if ui_y > window_bottom and ui_y - window_bottom <= 2.5:
                ui_y = window_bottom
            grid_tail_length = self._get_grid_tail_length(bar)
            left_point = QPointF(grid_left - grid_tail_length, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)

        for bar in self._bars:
            begin, end = bar.head, bar.tail
            ui_y = drawing_cache.drawer_y_to_ui(begin)
            draw_line(ui_y, bar)

        bar = self._bars[-1]
        ui_y = drawing_cache.drawer_y_to_ui(bar.tail)
        if ui_y - bar.rect.height() > drawing_cache.plot_area.top():
            draw_line(ui_y, bar)

    def draw_labels__horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1 + self.axis.label_spacing_to_plot_area

        for bar in self._bars:
            ui_x = drawing_cache.drawer_x_to_ui(bar.label_pos)

            pos = QPointF(ui_x,
                          label_top,
                          )

            self.switch_to_pos(pos, painter)
            self.axis.draw_label_for_value(bar.label_value, painter)
            self.switch_back(painter)

    def draw_labels__vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1 - self.axis.label_spacing_to_plot_area

        for bar in self._bars:
            ui_y = drawing_cache.drawer_y_to_ui(bar.label_pos)
            pos = QPointF(
                label_right - bar.rect.width(),
                ui_y - bar.rect.height())
            self.switch_to_pos(pos, painter)
            self.axis.draw_label_for_value(bar.label_value, painter)
            self.switch_back(painter)

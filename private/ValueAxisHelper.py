from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainter, QTransform

from Base import Orientation, TickPosition, TickSource
from Drawer import DrawConfig

if TYPE_CHECKING:
    from Axis import AxisBase


def _generate_sequence(begin, end, step):
    """output a sequence between [start, end)"""
    i = begin
    while i < end:
        yield i
        i += step


class AxisHelper(ABC):

    def __init__(self, axis: "AxisBase"):
        self.axis = axis
        self._last_transform = None

    @abstractmethod
    def prepare_draw(self, config: "DrawConfig", painter: "QPainter"):
        raise NotImplementedError()

    @abstractmethod
    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    @abstractmethod
    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    def _switch_to_pos(self, pos: QPointF, painter: "QPainter"):
        self._last_transform = painter.worldTransform()
        new_transform = self._last_transform * QTransform.fromTranslate(pos.x(), pos.y())
        painter.setWorldTransform(new_transform)

    def _switch_back(self, painter: "QPainter"):
        painter.setWorldTransform(self._last_transform)


class ValueAxisHelper(AxisHelper):

    def __init__(self, axis: "AxisBase"):
        super().__init__(axis)
        self._tick_for_values: Dict[float, QRectF] = {}

    def prepare_draw(self, config: "DrawConfig", painter: "QPainter"):
        axis = self.axis

        if axis.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high

        step = (end - begin) / axis.tick_count

        if axis.orientation is Orientation.VERTICAL:
            begin += step  # skip the lowest tick which is useless & can never be fully printed

        self._tick_for_values: Dict[float, QRectF] = {
            value: axis.tick_bounding_rect_for_value(value, painter)
            for value in _generate_sequence(begin,
                                            end,
                                            step)
        }

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_ticks_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_ticks_horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for value, _ in self._tick_for_values.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for value, _ in self._tick_for_values.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            left_point = QPointF(grid_left, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)

    def draw_ticks_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        tick_top = drawing_cache.plot_area.bottom() + 1 + self.axis.tick_spacing_to_plot_area

        for value, tick in self._tick_for_values.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)
            tick_width = tick.height()

            pos = QPointF(ui_x - tick_width,
                          tick_top,
                          )

            self._switch_to_pos(pos, painter)
            self.axis.draw_tick_for_value(value, painter)
            self._switch_back(painter)

    def draw_ticks_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        tick_right = drawing_cache.plot_area.left() - 1 - self.axis.tick_spacing_to_plot_area

        for value, rect in self._tick_for_values.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)
            tick_width = rect.width()
            tick_height = rect.height()

            pos = QPointF(
                tick_right - tick_width,
                ui_y - tick_height / 2)
            self._switch_to_pos(pos, painter)
            self.axis.draw_tick_for_value(value, painter)
            self._switch_back(painter)


@dataclass()
class BarInfo:
    tick_value: float
    tick_pos: float
    head: float
    tail: float
    rect: QRectF


class BarAxisHelper(AxisHelper):

    def __init__(self, axis: "AxisBase"):
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
                self.axis.tick_spacing_to_grid
            )
        else:
            begin, end = config.y_low, config.y_high
            self._grid_spacing_in_drawer = config.drawing_cache.ui_height_to_drawer(
                self.axis.tick_spacing_to_grid
            )

        step = (end - begin) / axis.tick_count

        # generate bars
        self._bars = [
            self._get_bar_info(bar_head, step, config, painter)
            for bar_head in _generate_sequence(begin, end, step)
        ]

    def _get_bar_info(self, bar_head, step, config, painter):
        value_source = self.axis.tick_source
        pos_source = self.axis.tick_position
        bar_tail = bar_head + step
        bar_mid = (bar_head + bar_tail) / 2
        if value_source == TickSource.BEGIN:
            tick_value = bar_head
        elif value_source == TickSource.MID:
            tick_value = bar_mid
        else:
            tick_value = bar_tail
        rect = self.axis.tick_bounding_rect_for_bar(tick_value, bar_head, bar_tail, painter)
        ui_width_half = config.drawing_cache.ui_width_to_drawer(rect.width())
        if pos_source == TickPosition.BEGIN:
            tick_pos = bar_head + self._grid_spacing_in_drawer
        elif pos_source == TickPosition.MID:
            tick_pos = bar_mid - ui_width_half / 2
        else:
            tick_pos = bar_tail - ui_width_half - self._grid_spacing_in_drawer
        return BarInfo(tick_value, tick_pos, bar_head, bar_tail, rect)

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        if self.axis.orientation is Orientation.VERTICAL:
            return self.draw_ticks_vertical(config, painter)
        if self.axis.orientation is Orientation.HORIZONTAL:
            return self.draw_ticks_horizontal(config, painter)

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

    def draw_ticks_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        tick_top = drawing_cache.plot_area.bottom() + 1 + self.axis.tick_spacing_to_plot_area

        for bar in self._bars:
            ui_x = drawing_cache.drawer_x_to_ui(bar.tick_pos)

            pos = QPointF(ui_x,
                          tick_top,
                          )

            self._switch_to_pos(pos, painter)
            self.axis.draw_tick_for_value(bar.tick_value, painter)
            self._switch_back(painter)

    def draw_ticks_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        tick_right = drawing_cache.plot_area.left() - 1 - self.axis.tick_spacing_to_plot_area

        for bar in self._bars:
            ui_y = drawing_cache.drawer_y_to_ui(bar.tick_pos)
            pos = QPointF(
                tick_right - bar.rect.width(),
                ui_y - bar.rect.height())
            self._switch_to_pos(pos, painter)
            self.axis.draw_tick_for_value(bar.tick_value, painter)
            self._switch_back(painter)

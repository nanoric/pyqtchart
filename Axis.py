from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, List, Any

from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtGui import QFont, QPainter, QPalette, QPen, QColor, QTransform

from Base import ColorType, Orientation, TickPosition, TickSource, TickType

if TYPE_CHECKING:
    from Drawer import DrawConfig
    from DataSource import CandleDataSourceType


def _generate_sequence(begin, end, step):
    """output a sequence between [start, end)"""
    i = begin
    while i < end:
        yield i
        i += step


class GridDrawer(ABC):
    @abstractmethod
    def draw_grid(self, data: Any, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


class TickDrawer(ABC):
    @abstractmethod
    def draw_label(self, label: Any, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()



class AxisBase(ABC):

    def __init__(self, orientation: "Orientation"):
        self.axis_visible: bool = True
        self.orientation = orientation

        self.grid_visible: bool = True
        self.grid_source: List[Any] = []

        self.tick_visible = True
        # spacing to plot_area: spacing-right for Vertical AxisBase, spacing-top for Horizontal
        self.tick_spacing_to_plot_area: int = 2
        self.tick_source: List[Any] = []

    # @virtual
    def prepare_draw_axis(self, config: "DrawConfig", painter: "QPainter")->None:
        pass

    def prepare_draw_grids(self, config: "DrawConfig", painter: "QPainter") ->None:
        pass

    def prepare_draw_ticks(self, config: "DrawConfig", painter: "QPainter") ->None:
        pass

    @abstractmethod
    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    @abstractmethod
    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


@dataclass()
class LineGridInfo:
    value: float
    tail_length: float


class LineGridAxisBase(AxisBase, ABC):
    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        self.grid_color: "ColorType" = QPalette().color(QPalette.Dark)
        self.grids: List[LineGridInfo] = []

    # @virtual
    def prepare_draw_grids(self, config: "DrawConfig", painter: "QPainter") ->None:
        pass

    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        painter.setPen(QPen(QColor(self.grid_color)))
        if self.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for grid in self.grids:
            ui_x = drawing_cache.drawer_x_to_ui(grid.value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom + grid.tail_length)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for grid in self.grids:
            ui_y = drawing_cache.drawer_y_to_ui(grid.value)
            left_point = QPointF(grid_left - grid.tail_length, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)


TextFlag = Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap


class TextTickInfo:
    value: float
    text: str


class WorldTransformStack:
    def __init__(self):
        self._last_transform = None

    def push(self, pos: QPointF, painter: "QPainter"):
        self._last_transform = painter.worldTransform()
        new_transform = self._last_transform * QTransform.fromTranslate(pos.x(), pos.y())
        painter.setWorldTransform(new_transform)

    def pop(self, painter: "QPainter"):
        painter.setWorldTransform(self._last_transform)

class TextAxisBase(AxisBase, , ABC):

    def __init__(self, orientation: "Orientation", tick_type: "TickType"):
        super().__init__(orientation, tick_type)
        palette = QPalette()
        self.label_color = palette.color(QPalette.Foreground)
        self.label_font = QFont()

        self.texts: List[TextTickInfo] = []
        self._transform_stack = WorldTransformStack()

    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        painter.setPen(QPen(self.label_color))
        painter.setFont(self.label_font)
        if self.orientation is Orientation.VERTICAL:
            return self.draw_ticks_vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_ticks_horizontal(config, painter)

    def draw_ticks_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        text_top = drawing_cache.plot_area.bottom() + 1 + self.tick_spacing_to_plot_area

        for text_info in self.texts:
            ui_x = drawing_cache.drawer_x_to_ui(text_info.value)
            text = text_info.text
            rect = painter.boundingRect(0,0,1000,1000, TextFlag, text)
            text_width = rect.height()

            pos = QPointF(ui_x - text_width,
                          text_top,
                          )

            self._transform_stack.push(pos, painter)
            self.draw_tick_for_value(value, painter)
            self._transform_stack.pop(painter)

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
            self.switch_to_pos(pos, painter)
            self.axis.draw_tick_for_value(value, painter)
            self.switch_back(painter)

    def draw_tick_for_value(self, value: float, painter: "QPainter"):
        label = self.label_for_value(value)
        painter.drawText(0, 0, 1000, 1000, TextFlag, label)

    def draw_tick_for_bar(self, value: float, head: float, tail: float,
                          painter: "QPainter"):
        label = self.label_for_bar(value, head, tail)
        painter.drawText(0, 0, 1000, 1000, TextFlag, label)

    def tick_bounding_rect_for_bar(self,
                                   value: float,
                                   head: float,
                                   tail: float,
                                   painter: "QPainter") -> "QRectF":
        text = self.label_for_bar(value, head, tail)
        return QRectF(painter.boundingRect(0, 0, 1000, 1000, TextFlag,
                                           text))

    def tick_bounding_rect_for_value(self,
                                     value: float,
                                     painter: "QPainter") -> "QRectF":
        text = self.label_for_value(value)
        return painter.boundingRect(0, 0, 1000, 1000, TextFlag,
                                    text)

    def label_for_bar(self, value: float, start: float, end: float) -> str:
        return self.label_for_value(value)

    @abstractmethod
    def label_for_value(self, value: float) -> str:
        raise NotImplementedError()


class AutoTickAxisBase(AxisBase):

    def __init__(self, orientation: "Orientation", tick_type: "TickType"):
        super().__init__(orientation)
        palette = QPalette()
        self.axis_visible: bool = True
        self.orientation = orientation

        self.grid_visible: bool = True
        self.grid_color: "ColorType" = palette.color(QPalette.Dark)

        self.tick_visible = True
        self.tick_type = tick_type
        self.tick_count = 5

        # for tick_type == TickType.BAR only:
        self.tick_source = TickSource.BEGIN
        self.tick_position = TickPosition.BEGIN
        self.grid_tail_length: Optional[int] = None  # None means auto
        self.tick_spacing_to_grid: int = 2

    @property
    def tick_type(self):
        return self._tick_type

    @tick_type.setter
    def tick_type(self, value: "TickType"):
        if value == TickType.VALUE:
            from private.ValueAxisHelper import ValueAxisHelper
            self._helper = ValueAxisHelper(self)
        else:
            from private.ValueAxisHelper import BarAxisHelper
            self._helper = BarAxisHelper(self)
        self._tick_type = value

    def prepare_draw_axis(self, config: "DrawConfig", painter: "QPainter"):
        self.prepare_draw_tick(config, painter)
        self._helper.prepare_draw(config, painter)

    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        self._helper.draw_grid(config, painter)

    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        self.prepare_draw_tick(config, painter)
        self._helper.draw_ticks(config, painter)

    def draw_tick_for_bar(self, value: float, head: float, tail: float,
                          painter: "QPainter"):
        return self.draw_tick_for_value(value, painter)

    def tick_bounding_rect_for_bar(self,
                                   value: float,
                                   head: float,
                                   tail: float,
                                   painter: "QPainter") -> "QRectF":
        return self.tick_bounding_rect_for_value(value, painter)

    @abstractmethod
    def prepare_draw_tick(self, config: "DrawConfig", painter: "QPainter"):
        """
        Call before any call to tick_for_xxx or tick_bounding_rect_for_xxx
        You should do set pen, brush and font here.
        """
        pass

    @abstractmethod
    def tick_bounding_rect_for_value(self,
                                     value: float,
                                     painter: "QPainter") -> "QRectF":
        """
        :return the size of drawn picture.
        """
        raise NotImplementedError()

    @abstractmethod
    def draw_tick_for_value(self, value: float, painter: "QPainter"):
        """
        Draw your tick at (0,0)
        Size to draw should be the same as return value of tick_bounding_rect_for_value().
        """
        raise NotImplementedError()
class ValueAxis(TextAxisBase):

    def __init__(self, orientation: Orientation, tick_type: "TickType"):
        super().__init__(orientation, tick_type)
        self.tick_count: int = 10
        self.format: str = "%.2f"

    def label_for_value(self, value: float) -> str:
        return self.format % value


class ValueAxisX(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.HORIZONTAL, TickType.VALUE)


class ValueAxisY(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.VERTICAL, TickType.VALUE)


class BarAxisX(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.HORIZONTAL, TickType.BAR)


class BarAxisY(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.VERTICAL, TickType.BAR)


# noinspection PyAbstractClass
class CandleAxisX(TextAxisBase):

    def __init__(self, data_source: "CandleDataSourceType"):
        super().__init__(Orientation.HORIZONTAL, TickType.BAR)
        self.label_count = 5
        self.data_source: "CandleDataSourceType" = data_source
        self.foramt = "%Y-%m-%d"

    def label_for_value(self, value: float) -> str:
        return self.data_source[int(value)].datetime.strftime(self.foramt)

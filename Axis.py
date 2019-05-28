from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QFont, QPainter, QPalette, QPen, QPicture

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


Tick = QPicture


class AxisBase(ABC):

    def __init__(self, orientation: "Orientation", tick_type: "TickType"):
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

        # spacing to plot_area: spacing-right for Vertical AxisBase, spacing-top for Horizontal
        self.tick_spacing_to_plot_area: int = 2

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

    def prepare_draw(self, config: "DrawConfig", painter: "QPainter"):
        self.prepare_draw_tick(config, painter)
        self._helper.prepare_draw(config, painter)

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        self._helper.draw_grid(config, painter)

    def draw_ticks(self, config: "DrawConfig", painter: QPainter):
        self.prepare_draw_tick(config, painter)
        self._helper.draw_ticks(config, painter)

    def draw_tick_for_bar(self, value: float, head: float, tail: float,
                          painter: "QPainter") -> "Tick":
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
    def draw_tick_for_value(self, value: float, painter: "QPainter") -> "Tick":
        """
        Draw your tick at (0,0)
        Size to draw should be the same as return value of tick_bounding_rect_for_value().
        """
        raise NotImplementedError()


TextFlag = Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap


class TextAxisBase(AxisBase):

    def __init__(self, orientation: "Orientation", tick_type: "TickType"):
        super().__init__(orientation, tick_type)
        palette = QPalette()
        self.label_color = palette.color(QPalette.Foreground)
        self.label_font = QFont()

    def prepare_draw_tick(self, config: "DrawConfig", painter: "QPainter"):
        painter.setFont(self.label_font)
        painter.setPen(QPen(self.label_color))

    def draw_tick_for_value(self, value: float, painter: "QPainter") -> "Tick":
        label = self.label_for_value(value)
        painter.drawText(0, 0, 1000, 1000, TextFlag, label)

    def draw_tick_for_bar(self, value: float, head: float, tail: float,
                          painter: "QPainter") -> "Tick":
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

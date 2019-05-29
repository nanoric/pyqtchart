from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING, TypeVar

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPalette, QPen

from Base import ColorType, Orientation, TickPosition, TickSource, TickType
from DataSource import DataSource

if TYPE_CHECKING:
    from Drawer import DrawConfig


def _generate_sequence(begin, end, step):
    """output a sequence between [start, end)"""
    i = begin
    while i < end:
        yield i
        i += step


T = TypeVar("T")


class GridDrawer(ABC):

    def __init__(self, orientation: "Orientation"):
        self.orientation = orientation
        self.grids_data_source: List[Any] = []

    @abstractmethod
    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


class LabelDrawer(ABC):

    def __init__(self, orientation: "Orientation"):
        self.orientation = orientation
        self.label_data_source: List[Any] = []

    @abstractmethod
    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


class AxisBase(ABC):
    """
    overload mehtod calling sequence:
    prepare_draw_axis()
    prepare_draw_grids()
    draw_grids()
    prepare_draw_labels()
    draw_labels_()
    """

    def __init__(self, orientation: "Orientation"):
        self.axis_visible: bool = True
        self.orientation = orientation

        self.grids_visible: bool = True

        self.label_visible = True
        # spacing to plot_area: spacing-right for Vertical AxisBase, spacing-top for Horizontal
        self.label_spacing_to_plot_area: int = 2

    def prepare_draw_axis(self, config: "DrawConfig", painter: "QPainter") -> None:
        pass

    def prepare_draw_grids(self, config: "DrawConfig", painter: "QPainter") -> None:
        pass

    def prepare_draw_labels(self, config: "DrawConfig", painter: "QPainter") -> None:
        pass

    @abstractmethod
    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    @abstractmethod
    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


@dataclass()
class LineGridInfo:
    value: float
    tail_length: float


class LineGridDrawer(GridDrawer):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        self.grid_color = QPalette().color(QPalette.Dark)

    def draw_grids(self, config: "DrawConfig",
                   painter: QPainter):
        painter.setPen(QPen(QColor(self.grid_color)))
        if self.orientation is Orientation.VERTICAL:
            return self.draw_grid_vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_grid_horizontal(config, painter)

    def draw_grid_horizontal(self, config: "DrawConfig",
                             painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_top = drawing_cache.plot_area.top()
        grid_bottom = drawing_cache.plot_area.bottom()

        for grid in self.grids_data_source:
            ui_x = drawing_cache.drawer_x_to_ui(grid.value)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom + grid.tail_length)
            painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig",
                           painter: QPainter):
        drawing_cache = config.drawing_cache

        grid_left = drawing_cache.plot_area.left() - 1
        grid_right = drawing_cache.plot_area.right()

        for grid in self.grids_data_source:
            ui_y = drawing_cache.drawer_y_to_ui(grid.value)
            left_point = QPointF(grid_left - grid.tail_length, ui_y)
            right_point = QPointF(grid_right, ui_y)
            painter.drawLine(left_point, right_point)


TextFlag = Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap


class TextLabelInfo:
    value: float
    text: str


class TextLabelDrawer(LabelDrawer):

    def __init__(self, orientation: "Orientation", label_spacing_to_plot_area: float):
        super().__init__(orientation)
        palette = QPalette()
        self.label_spacing_to_plot_area: float = label_spacing_to_plot_area
        self.label_color = palette.color(QPalette.Foreground)
        self.label_font = QFont()

    def draw_labels(self, config: "DrawConfig",
                    painter: QPainter):
        painter.setPen(QPen(self.label_color))
        painter.setFont(self.label_font)
        if self.orientation is Orientation.VERTICAL:
            return self.draw_labels__vertical(config, painter)
        if self.orientation is Orientation.HORIZONTAL:
            return self.draw_labels__horizontal(config, painter)

    def draw_labels__horizontal(self, config: "DrawConfig",
                              painter: QPainter):
        drawing_cache = config.drawing_cache

        text_top = drawing_cache.plot_area.bottom() + 1 + self.label_spacing_to_plot_area

        for text_info in self.label_data_source:
            ui_x = drawing_cache.drawer_x_to_ui(text_info.value)
            text = text_info.text
            rect = painter.boundingRect(0, 0, 1000, 1000, TextFlag, text)
            text_width = rect.height()

            pos = QPointF(ui_x - text_width,
                          text_top,
                          )
            painter.drawText(pos, text)

    def draw_labels__vertical(self, config: "DrawConfig",
                            painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1 - self.label_spacing_to_plot_area

        for text_info in self.label_data_source:
            ui_y = drawing_cache.drawer_y_to_ui(text_info.value)
            text = text_info.text
            rect = painter.boundingRect(0, 0, 1000, 1000, TextFlag, text)
            label_width = rect.width()
            label_height = rect.height()

            pos = QPointF(
                label_right - label_width,
                ui_y - label_height / 2)
            painter.drawText(pos, text)


class ValueDataSource(DataSource):

    def __init__(self, orientation: "Orientation"):
        super().__init__()
        self.label_spacing_to_grid: float = 0
        self.orientation = orientation
        self.label_count = 5

        self.data_list: List["float"] = []

    def prepare(self, config: "DrawConfig", painter: "QPainter"):
        if self.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high

        step = (end - begin) / self.label_count

        if self.orientation is Orientation.VERTICAL:
            begin += step  # skip the lowest tick which is useless & can never be fully printed

        self.data_list: List["float"] = [value for value in _generate_sequence(begin, end, step)]
        return self


class __TextLabelDataSources:
    """
    Generate values for AxisDataSource
    """

    def __init__(self, orientation: "Orientation", label_type: "TickType"):
        super().__init__(orientation)
        palette = QPalette()
        self.axis_visible: bool = True
        self.orientation = orientation

        self.grid_visible: bool = True
        self.grid_color: "ColorType" = palette.color(QPalette.Dark)

        self.label_visible = True
        self.label_type = label_type

        # for label_type == TickType.BAR only:
        self.label_source = TickSource.BEGIN
        self.label_position = TickPosition.BEGIN
        self.grid_tail_length: Optional[int] = None  # None means auto
        self.label_spacing_to_grid: int = 2

    @property
    def label_type(self):
        return self._label_type

    @label_type.setter
    def label_type(self, value: "TickType"):
        if value == TickType.VALUE:
            from private.ValueAxisHelper import ValueAxisHelper
            self._helper = ValueAxisHelper(self)
        else:
            from private.ValueAxisHelper import BarAxisHelper
            self._helper = BarAxisHelper(self)
        self._label_type = value

    def prepare_draw_axis(self, config: "DrawConfig", painter: "QPainter"):
        self.prepare_draw_tick(config, painter)
        self._helper.prepare_draw(config, painter)

    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        self._helper.draw_grid(config, painter)

    def draw_labels_(self, config: "DrawConfig", painter: QPainter):
        self.prepare_draw_tick(config, painter)
        self._helper.draw_labels_(config, painter)

    def draw_label_for_bar(self, value: float, head: float, tail: float,
                          painter: "QPainter"):
        return self.draw_label_for_value(value, painter)

    def label_bounding_rect_for_bar(self,
                                   value: float,
                                   head: float,
                                   tail: float,
                                   painter: "QPainter") -> "QRectF":
        return self.label_bounding_rect_for_value(value, painter)

    @abstractmethod
    def prepare_draw_tick(self, config: "DrawConfig", painter: "QPainter"):
        """
        Call before any call to label_for_xxx or label_bounding_rect_for_xxx
        You should do set pen, brush and font here.
        """
        pass

    @abstractmethod
    def label_bounding_rect_for_value(self,
                                     value: float,
                                     painter: "QPainter") -> "QRectF":
        """
        :return the size of drawn picture.
        """
        raise NotImplementedError()

    @abstractmethod
    def draw_label_for_value(self, value: float, painter: "QPainter"):
        """
        Draw your tick at (0,0)
        Size to draw should be the same as return value of label_bounding_rect_for_value().
        """
        raise NotImplementedError()


class ValueAxis(LineGridDrawer, TextLabelDrawer,
                AxisBase):

    def __init__(self, orientation: Orientation):
        AxisBase.__init__(self, orientation)
        TextLabelDrawer.__init__(self, orientation, self.label_spacing_to_plot_area)
        LineGridDrawer.__init__(self, orientation)
        self._data_source = ValueDataSource(self.orientation)
        self.format: str = "%.2f"

    def prepare_draw_grids(self, config: "DrawConfig", painter: "QPainter") -> None:
        self.grids_data_source = self._data_source.prepare(config, painter)

    def prepare_draw_labels(self, config: "DrawConfig", painter: "QPainter") -> None:
        self.label_data_source = self._data_source.prepare(config, painter)


class ValueAxisX(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.HORIZONTAL)


class ValueAxisY(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.VERTICAL)

class BarAxisX(ValueAxis):
    pass

#     def __init__(self):
#         super().__init__(Orientation.HORIZONTAL, TickType.BAR)
#
#
class BarAxisY(ValueAxis):
    pass
#
#     def __init__(self):
#         super().__init__(Orientation.VERTICAL, TickType.BAR)
#
#
# # noinspection PyAbstractClass
class CandleAxisX(AxisBase):
    pass
#
#     def __init__(self, data_source: "CandleDataSourceType"):
#         super().__init__(Orientation.HORIZONTAL, TickType.BAR)
#         self.label_count = 5
#         self.data_source: "CandleDataSourceType" = data_source
#         self.foramt = "%Y-%m-%d"
#
#     def label_for_value(self, value: float) -> str:
#         return self.data_source[int(value)].datetime.strftime(self.foramt)

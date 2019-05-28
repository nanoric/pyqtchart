from typing import Dict, List, Optional, TYPE_CHECKING, Tuple

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QFontInfo, QPainter

from Base import AxisBase, Orientation

if TYPE_CHECKING:
    from Base import DrawConfig
    from DataSource import CandleDataSourceType


def _generate_sequence(begin, end, step):
    """output a sequence between [start, end)"""
    i = begin
    while i < end:
        yield i
        i += step


class StringAxis(AxisBase):

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

    def draw_labels_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1
        label_width = 100  # assume no label is longer than this
        label_height = 100  # assume no label is higher than this

        for value, label in self.strings.items():
            ui_x = drawing_cache.drawer_x_to_ui(value)

            text_pos = QRectF(ui_x - label_width / 2, label_top + self.label_spacing_to_plot_area,
                              label_width, label_height)
            painter.drawText(text_pos, Qt.AlignTop | Qt.AlignHCenter, label)

    def draw_labels_vertical(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_right = drawing_cache.plot_area.left() - 1

        for value, label in self.strings.items():
            ui_y = drawing_cache.drawer_y_to_ui(value)

            text_pos = QRectF(0, ui_y - 10, label_right - self.label_spacing_to_plot_area, 20)
            painter.drawText(text_pos, Qt.AlignRight | Qt.AlignVCenter, label)
        pass


class StringBarAxis(AxisBase):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        # sorted [begin, end)=>label mapping
        Key = Tuple[float, Optional[float]]
        self.strings: Dict[Key, str] = {}

        # 网格探出绘图框的长度（有了这个，各个label的范围更明显） None为文字高度+margin
        self.grid_tail_length: Optional[int] = None
        self.label_spacing_to_grid = self.label_spacing_to_plot_area

        # intermediate variables
        self._keys: List[Key] = []
        self._values: List[str] = []
        self._n: int = 0
        self._grid_tail_length: int = 5

    def prepare_draw(self, config: "DrawConfig"):
        self._keys = list(self.strings.keys())
        self._values = list(self.strings.values())
        self._n = len(self._keys)
        grid_tail_length: int = self.grid_tail_length
        if grid_tail_length is None:
            grid_tail_length = QFontInfo(
                self.label_font).pixelSize() + self.label_spacing_to_plot_area
        self._grid_tail_length = grid_tail_length

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
        grid_bottom = drawing_cache.plot_area.bottom() + self._grid_tail_length

        for i in range(self._n):
            begin, end = self._keys[i]
            ui_x = drawing_cache.drawer_x_to_ui(begin)
            top_point = QPointF(ui_x, grid_top)
            bottom_point = QPointF(ui_x, grid_bottom)
            painter.drawLine(top_point, bottom_point)
            if end is not None:
                ui_x = drawing_cache.drawer_x_to_ui(begin)
                top_point = QPointF(ui_x, grid_top)
                bottom_point = QPointF(ui_x, grid_bottom)
                painter.drawLine(top_point, bottom_point)

    def draw_grid_vertical(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()

    def draw_labels_horizontal(self, config: "DrawConfig", painter: QPainter):
        drawing_cache = config.drawing_cache

        label_top = drawing_cache.plot_area.bottom() + 1
        label_height = 100  # assume no label is higher than this

        for i in range(self._n - 1):
            begin, end = self._keys[i]
            text = self._values[i]
            if end is None:
                end = self._keys[i + 1][0]
            begin_ui_x = drawing_cache.drawer_x_to_ui(begin)
            end_ui_x = drawing_cache.drawer_x_to_ui(end)

            text_pos = QRectF(begin_ui_x + self.label_spacing_to_grid,
                              label_top + self.label_spacing_to_plot_area,

                              end_ui_x - begin_ui_x,
                              label_height)
            painter.drawText(text_pos, Qt.AlignTop | Qt.AlignLeft, text)

        # draw the last label, and this label may don't has an end anchor
        begin, end = self._keys[-1]
        text = self._values[-1]
        begin_ui_x = drawing_cache.drawer_x_to_ui(begin)
        if end is None:
            end_ui_x = drawing_cache.drawer_area.right() + 3000  # should be large enough
        else:
            end_ui_x = drawing_cache.drawer_x_to_ui(end)

        text_pos = QRectF(begin_ui_x + self.label_spacing_to_grid,
                          label_top + self.label_spacing_to_plot_area,
                          end_ui_x - begin_ui_x,
                          label_height)
        painter.drawText(text_pos, Qt.AlignTop | Qt.AlignLeft, text)

    def draw_labels_vertical(self, config: "DrawConfig", painter: QPainter):
        raise NotImplementedError()


class ValueAxis(StringAxis):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        self.tick_count: int = 10
        self.format: str = "%.2f"
        self.show_lowest = False
        self.show_highest = False

    # @virtual
    def prepare_draw(self, config: "DrawConfig"):
        font_height = QFontInfo(self.label_font).pixelSize() + 2
        font_height_in_drawer = config.drawing_cache.ui_height_to_drawer(font_height)
        if self.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high

        if not self.show_lowest:
            begin += font_height_in_drawer
        if not self.show_highest:
            end -= font_height_in_drawer

        step = (end - begin) / self.tick_count
        self.strings = {
            value: self.format % value
            for value in _generate_sequence(begin, end, step)
        }


class ValueAxisX(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.HORIZONTAL)


class ValueAxisY(ValueAxis):

    def __init__(self):
        super().__init__(Orientation.VERTICAL)


class ValueBarAxis(StringBarAxis):

    def __init__(self, orientation: Orientation):
        super().__init__(orientation)
        self.tick_count: int = 10
        self.format: str = "%d"

    # @virtual
    def prepare_draw(self, config: "DrawConfig"):
        if self.orientation is Orientation.HORIZONTAL:
            begin, end = config.begin, config.end
        else:
            begin, end = config.y_low, config.y_high
        step = (end - begin) / self.tick_count
        self.strings = {
            (value, None): self.format % value
            for value in _generate_sequence(begin, end, step)
        }
        super().prepare_draw(config)


# noinspection PyAbstractClass
class CandleAxisX(StringBarAxis):

    def __init__(self, data_source: "CandleDataSourceType"):
        super().__init__(Orientation.HORIZONTAL)
        self.label_count = 5
        self.data_source: "CandleDataSourceType" = data_source

    def prepare_draw(self, config: "DrawConfig"):
        data_source = self.data_source
        n = config.end - config.begin
        step = int(n / self.label_count) + 1
        self.strings.clear()
        for i in range(config.begin, config.end, step):
            data = data_source[i]

            key = (i, None)
            label = data.datetime.strftime("%Y-%m-%d")
            self.strings[key] = label
        super().prepare_draw(config)

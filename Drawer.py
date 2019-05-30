from typing import Optional, TYPE_CHECKING, TypeVar

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter

from DataSource import CandleData, DataSource, ChartDrawerBase

if TYPE_CHECKING:
    from Base import ColorType, DrawConfig

T = TypeVar("T")


class CandleDrawer(ChartDrawerBase):
    """
    Drawer to present candlestick chart

    if cache is enabled
    """

    def __init__(self, data_source: Optional["DataSource"] = None):
        super().__init__(data_source)
        self.body_width = 0.95
        self.line_width = 0.15
        self.minimum_box_height = 0.01
        self.growing_color: "ColorType" = "red"
        self.falling_color: "ColorType" = "green"
        self.use_cache = True

        # cached variables for draw
        self._cache_raising = []
        self._cache_falling = []
        self._cache_end = 0

    def on_data_source_data_removed(self, begin: int, end: int):
        # todo: fix cache, but not to rebuild it.
        self.clear_cache()

    def prepare_draw(self, config: "DrawConfig") -> "DrawConfig":
        showing_data = self._data_source[config.begin:config.end]
        if showing_data:
            low = min(showing_data, key=lambda c: c.low).low
            high = max(showing_data, key=lambda c: c.high).high
            config.y_low, config.y_high = low, high
        return config

    def draw(self, config: "DrawConfig", painter: "QPainter"):
        raising_brush = QBrush(QColor(self.growing_color))
        falling_brush = QBrush(QColor(self.falling_color))

        begin, end = config.begin, config.end

        # 如果不使用cache，简单的做法就是每次绘图之前清空一下cache
        if not self.use_cache:
            self.clear_cache()
        data_len = len(self._data_source)
        if data_len > self._cache_end:
            self._generate_cache(self._cache_end, data_len)

        painter.setBrush(raising_brush)
        painter.drawRects([i for i in self._cache_raising[begin * 2:end * 2] if i])
        painter.setBrush(falling_brush)
        painter.drawRects([i for i in self._cache_falling[begin * 2:end * 2] if i])

    def clear_cache(self):
        self._cache_end = 0
        self._cache_raising = []
        self._cache_falling = []

    def _generate_cache(self, begin, end):
        for i in range(begin, end):
            data: "CandleData" = self._data_source[i]

            if data.open <= data.close:
                push_cache = self._cache_raising
                nop_cache = self._cache_falling
            else:
                push_cache = self._cache_falling
                nop_cache = self._cache_raising

            # draw box
            box = self.get_rect(i, data.open, data.close, self.body_width)
            push_cache.append(box)
            nop_cache.append(None)

            # draw line
            line = self.get_rect(i, data.low, data.high, self.line_width)
            push_cache.append(line)
            nop_cache.append(None)

        self._cache_end = end

    def get_rect(self, i, start_y, end_y, width):
        left = i + 0.5 - 0.5 * width
        rect = QRectF(left, min(start_y, end_y),
                      width, max(abs(start_y - end_y), self.minimum_box_height))
        return rect


class BarChartDrawer(ChartDrawerBase):
    """
    Drawer to present Histogram.

    When use_cache is disable, BarChartDrawer supports any list like DataSource,
      including un-formal DataSource).
    When use_cache is enabled, BarChartDrawer supports only formal DataSource
    """

    def __init__(self, data_source: Optional["DataSource"] = None):
        super().__init__(data_source)
        self.body_width = 1
        self.positive_color: "ColorType" = "red"
        self.negative_color: "ColorType" = "green"

        self.use_cache = True

        # cached variables for draw
        self._cache_positive = []
        self._cache_negative = []
        self._cache_end = 0

    def on_data_source_data_removed(self, begin: int, end: int):
        self.clear_cache()

    def prepare_draw(self, config: "DrawConfig") -> "DrawConfig":
        showing_data = self._data_source[config.begin:config.end]
        if showing_data:
            low = min(showing_data)
            high = max(showing_data)
            config.y_low, config.y_high = low, high
        return config

    def draw(self, config: "DrawConfig", painter: "QPainter"):
        raising_brush = QBrush(QColor(self.positive_color))
        falling_brush = QBrush(QColor(self.negative_color))

        begin, end = config.begin, config.end

        if not self.use_cache:
            self.clear_cache()
        cache_end = self._cache_end

        data_len = len(self._data_source)
        if data_len > cache_end:
            self._generate_cache(cache_end, data_len)

        painter.setBrush(raising_brush)
        painter.drawRects([i for i in self._cache_positive[begin:end] if i])
        painter.setBrush(falling_brush)
        painter.drawRects([i for i in self._cache_negative[begin:end] if i])

    def clear_cache(self):
        self._cache_end = 0
        self._cache_positive = []
        self._cache_negative = []

    def _generate_cache(self, begin, end):
        for i in range(begin, end):
            data: "float" = self._data_source[i]

            if data > 0:
                push_cache = self._cache_positive
                nop_cache = self._cache_negative
            else:
                push_cache = self._cache_negative
                nop_cache = self._cache_positive

            # draw box
            box = self.get_rect(i, 0, data, self.body_width)
            push_cache.append(box)
            nop_cache.append(None)

        self._cache_end = end

    def get_rect(self, i, start_y, end_y, width):
        left = i + 0.5 - 0.5 * width
        rect = QRectF(left, min(start_y, end_y),
                      width, abs(start_y - end_y),
                      )
        return rect


HistogramDrawer = BarChartDrawer



from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter

from Axis import StringBarAxis
from Base import DrawerBase, Orientation
from DataSource import DataSource

if TYPE_CHECKING:
    from Base import DrawConfig, ColorType

CandleDataSourceType = DataSource["CandleData"]


@dataclass
class CandleData:
    """
    CandleSeries中的单条数据
    不一定要这个类，但是如果是其他类，必须提供完全相同的字段（可以考虑使用@property作转换）
    """
    open: float
    low: float
    high: float
    close: float
    datetime: datetime


class CandleDrawer(DrawerBase):
    """
    管理一系列数据
    并且管理数据的绘制
    """

    def __init__(self, data_source: Optional["DataSource"] = None):
        super().__init__(data_source)
        self.body_width = 0.95
        self.line_width = 0.15
        self.minimum_box_height = 0.01
        self.growing_color: "ColorType" = "red"
        self.falling_color: "ColorType" = "green"

        # 当cache打开时，不允许向DataSource中间插入数据，只允许向DataSource末尾插入数据，否则绘制出来的图会出错
        # 数据量越大，cache的效率提升越明显
        # 如果让DataSource支持消息订阅，则可以在所有情况下使用cache，但是考虑到无论怎么用cache，效率应该和C++无脑绘制差不多，还是算了。
        self.use_cache = True

        # cached variables for draw
        self._cache_raising = []
        self._cache_falling = []
        self._cache_end = 0

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
            cache_end = 0
            self._cache_raising = []
            self._cache_falling = []
        else:
            cache_end = self._cache_end

        data_len = len(self._data_source)
        if data_len > cache_end:
            self._generate_cache(cache_end, data_len)

        painter.setBrush(raising_brush)
        painter.drawRects([i for i in self._cache_raising[begin*2:end*2] if i])
        painter.setBrush(falling_brush)
        painter.drawRects([i for i in self._cache_falling[begin*2:end*2] if i])

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

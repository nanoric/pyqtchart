from dataclasses import dataclass
from datetime import datetime
from typing import List, TYPE_CHECKING

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter

from Axis import StringBarAxis
from Base import DrawerBase, Orientation

if TYPE_CHECKING:
    from Base import DrawConfig, ColorType

CandleDataSourceType = List["CandleData"]


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

    def __init__(self):
        super().__init__()
        self.body_width = 0.95
        self.line_width = 0.15
        self.minimum_box_height = 0.01
        self.growing_color: "ColorType" = "red"
        self.falling_color: "ColorType" = "green"

        # cached variables for draw
        self._length = 0

    def prepare_draw(self, config: "DrawConfig") -> "DrawConfig":
        showing_data = self._data_source[config.begin:config.end]
        if showing_data:
            low = min(showing_data, key=lambda c: c.low).low
            high = max(showing_data, key=lambda c: c.high).high
            config.y_low, config.y_high = low, high
        return config

    def draw(self, config: "DrawConfig", painter: "QPainter"):
        growing_brush = QBrush(QColor(self.growing_color))
        falling_brush = QBrush(QColor(self.falling_color))
        for i in range(config.begin, config.end):
            data: "CandleData" = self._data_source[i]

            if data.open <= data.close:
                painter.setBrush(growing_brush)
            else:
                painter.setBrush(falling_brush)

            # draw box
            box = self.get_rect(i, data.open, data.close, self.body_width)
            painter.drawRect(box)

            # draw line
            line = self.get_rect(i, data.low, data.high, self.line_width)
            painter.drawRect(line)

    def get_rect(self, i, start_y, end_y, width):
        left = i + 0.5 - 0.5 * width
        rect = QRectF(left, min(start_y, end_y),
                      width, max(abs(start_y - end_y), self.minimum_box_height))
        return rect


class CandleAxisX(StringBarAxis):

    def __init__(self, data_source: "CandleDataSourceType"):
        super().__init__(Orientation.HORIZONTAL)
        self.label_count = 5
        self.data_source: "CandleDataSourceType" = data_source

    def prepare_draw(self, config: "DrawConfig"):
        data_source = self.data_source
        n = config.end - config.begin
        step = int(n / self.label_count)
        self.strings.clear()
        for i in range(config.begin, config.end, step):
            data = data_source[i]

            key = (i, None)
            label = data.datetime.strftime("%Y-%m-%d")
            self.strings[key] = label
        super().prepare_draw(config)

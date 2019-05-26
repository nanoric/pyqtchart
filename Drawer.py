from typing import TYPE_CHECKING

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor, QPainter

from Base import DrawerBase

if TYPE_CHECKING:
    from Base import DrawConfig, ColorType


class BarDrawer(DrawerBase):
    """
    管理一系列数据
    并且管理数据的绘制
    """

    def __init__(self):
        super().__init__()
        self.body_width = 1
        self.positive_color: "ColorType" = "red"
        self.negative_color: "ColorType" = "green"

        # 当cache打开时，不允许向DataSource中间插入数据，只允许向DataSource末尾插入数据，否则绘制出来的图会出错
        # 数据量越大，cache的效率提升越明显
        # 如果让DataSource支持消息订阅，则可以在所有情况下使用cache，但是考虑到无论怎么用cache，效率应该和C++无脑绘制差不多，还是算了。
        self.use_cache = True

        # cached variables for draw
        self._cache_positive = []
        self._cache_negative = []
        self._cache_end = 0

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

        # 如果不使用cache，简单的做法就是每次绘图之前清空一下cache
        if not self.use_cache:
            cache_end = 0
            self._cache_positive = []
            self._cache_negative = []
        else:
            cache_end = self._cache_end

        data_len = len(self._data_source)
        if data_len > cache_end:
            self._generate_cache(cache_end, data_len)

        painter.setBrush(raising_brush)
        painter.drawRects([i for i in self._cache_positive[begin:end] if i])
        painter.setBrush(falling_brush)
        painter.drawRects([i for i in self._cache_negative[begin:end] if i])

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

import csv
from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import QRectF, QTimer, Qt
from PyQt5.QtGui import QBrush, QColor, QPaintEvent, QPainter, QPen, QPicture, QTransform
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget


class AbstractAxis:

    def __init__(self):
        pass


def virtual(func):
    return func


class DataDrawer(ABC):
    """
    数据序列
    有两个职责：
    1、管理自身的数据
    2、将数据绘制出来

    各个虚函数的调用顺序是这样的：
    ```
    for series in all_series:
        series.before_draw()
           for i in ...:
               series.draw_item()
        series.after_draw()
    ```
    """

    def __init__(self):
        self._data_source: Optional["DataSource"] = None

    @abstractmethod
    def prepare_draw(self, config: "DrawConfig") -> "DrawConfig":
        """
        在准备绘制的时候会被调用，可能会被调用多次。
        这个函数应该根据config的值计算出自身所需的y值
        并且将[y_low, y_high]设置为自己绘制所有图像所覆盖的y值范围。
        绘图引擎会根据各个数据序列所覆盖的y值范围不断调整图表自身值的范围，直到刚好能显示所有数据序列为止

        注意：这里收到的config并不是draw_all时所使用的设置
        :return: "DrawConfig"
        """
        return config

    @abstractmethod
    def draw_all(self, config: "DrawConfig", painter: QPainter):
        """
        绘制数据，可以在整张图上任意绘制，但是该函数最好每次只绘制坐标属于x的图
        坐标系(以下称为drawer坐标系)使用和数据x-y值一致的坐标系:原点在左下角，x轴向右,y轴向上 => 坐下到右上
        整个图形的坐标范围为: (left, bottom, right, top) = (begin, y_low, end, y_high)
        因为图标并不知道数据的任何细节，所以draw_item函数应该自己检查x值是否越界
        """
        pass


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


class DataSource(list):

    def __init__(self, datas=None):
        super().__init__()
        self._drawers: List["DataDrawer"] = []

    def add_drawer(self, drawer: "DataDrawer"):
        if drawer not in self._drawers:
            self._drawers.append(drawer)
            drawer._data_source = self


class Pen:
    NO = QPen(QColor(0, 0, 0, 0))


class Brush:
    NO = QBrush(QColor(0, 0, 0, 0))
    RED = QBrush(QColor("red"))
    GREEN = QBrush(QColor("green"))
    DARK = QBrush(QColor("dark"))
    GRAY = QBrush(QColor("gray"))


class CandleDrawer(DataDrawer):
    """
    管理一系列数据
    并且管理数据的绘制
    """

    def __init__(self):
        super().__init__()
        self.body_width = 0.75
        self.line_width = 0.15
        self.minimum_box_height = 0.01

        # cached variables for draw
        self._length = 0

    def prepare_draw(self, config: "DrawConfig") -> "DrawConfig":
        showing_data = self._data_source[config.begin:config.end]
        low = min(showing_data, key=lambda c: c.low).low
        high = max(showing_data, key=lambda c: c.high).high
        config.y_low, config.y_high = low, high
        return config

    def draw_all(self, config: "DrawConfig", painter: QPainter):
        for i in range(config.begin, config.end):
            data: "CandleData" = self._data_source[i]

            if data.open <= data.close:
                painter.setBrush(Brush.RED)
            else:
                painter.setBrush(Brush.GREEN)

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


class DrawConfig:

    def __init__(self):
        self.begin: int = 0  # 第一个绘制的元素
        self.end: int = 0  # 最后一个绘制的元素+1：也就是说绘制元素的范围为[begin, end)
        self.y_low: float = 0  # 图表顶端所代表的y值
        self.y_high: float = 0  # 图表底端所代表的y值


class ExtraDrawConfig(DrawConfig):

    def __init__(self):
        super().__init__()
        self.y_scale = 1.1
        val = 100
        self.paddings = (val, val, val, val)

        self.axis_width = 1
        self.axis_color = QColor("black")


def scale_from_mid(low, high, ratio):
    mid = (low + high) / 2
    scaled_range_2 = (high - low) / 2 * ratio
    return mid - scaled_range_2, mid + scaled_range_2


class PlotWidget(QPicture):
    pass


class BarChartWidget(QWidget):
    """
    用于管理二维平面图，目前只支持x坐标值为线性整数的图标。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._draw_config = ExtraDrawConfig()
        self._drawers: List[DataDrawer] = []

        self._draw_config.begin = 0
        self._draw_config.end = 10

        self.axis_layer = QPicture()
        self._layers: List["QPicture"] = []

    def paintEvent(self, event: QPaintEvent):
        # copy config: ensure config is not change while painting
        config = copy(self._draw_config)

        # get preferred y range
        preferred_configs = [s.prepare_draw(copy(config)) for s in self._drawers]
        y_low = min(preferred_configs, key=lambda c: c.y_low).y_low
        y_high = max(preferred_configs, key=lambda c: c.y_high).y_high

        # scale y range
        y_low, y_high = config.y_low, config.y_high = scale_from_mid(y_low, y_high, config.y_scale)
        y_range = y_high - y_low
        x_range = config.end - config.begin

        primary_painter = QPainter(self)

        axis_pic = self.paint_axis_layer(config)
        axis_pic.play(primary_painter)

        # 绘制所有注册了的序列
        for i, s in enumerate(self._drawers):
            pic = self._layers[i]
            self.paint_drawer_layer(s, pic, config)
            pic.play(primary_painter)

        primary_painter.end()
        event.accept()

    def plot_area(self, config: "ExtraDrawConfig") -> QRectF:
        output: QRectF = QRectF(self.rect())
        paddings = config.paddings
        output = output.adjusted(paddings[0], paddings[1], -paddings[2], -paddings[3])
        return output

    def paint_drawer_layer(self, drawer: "DataDrawer", pic: QPicture, config: "ExtraDrawConfig"):
        painter = QPainter(pic)
        painter.setPen(Pen.NO)

        # 将drawer坐标转化为UI坐标
        drawer_area = QRectF(config.begin, config.y_low, config.end - config.begin,
                             config.y_high - config.y_low)
        ui_area = self.plot_area(config)
        transform = self._viewport_transform(drawer_area, ui_area)

        # 在UI坐标系中上下翻转图像
        transform *= QTransform.fromTranslate(0, self.size().height()).rotate(180, Qt.XAxis)

        painter.setWorldTransform(transform)
        painter.setWorldMatrixEnabled(True)

        drawer.draw_all(copy(config), painter)

        painter.end()

    def _viewport_transform(self, input: QRectF, output: QRectF):
        rx, ry = output.width() / input.width(), output.height() / input.height()
        t = QTransform.fromTranslate(-input.left(), -input.top())
        t *= QTransform.fromScale(rx, ry)
        t *= QTransform.fromTranslate(output.left(), output.top())
        return t

    def paint_axis_layer(self, config: "ExtraDrawConfig"):
        pic = self.axis_layer
        painter = QPainter(pic)
        plot_area = self.plot_area(config)
        painter.setBrush(Brush.NO)
        painter.setPen(QPen(QBrush(config.axis_color), config.axis_width))
        painter.drawRect(plot_area)
        painter.end()
        return pic

    def add_drawer(self, drawer: CandleDrawer):
        self._drawers.append(drawer)
        self._layers.append(QPicture())

    def set_x_range(self, begin: int, end: int):
        self._draw_config.begin, self._draw_config.end = begin, end


class MainWindow(QMainWindow):

    def __init__(self, datas: List["CandleData"], parent=None):
        super().__init__(parent)
        self.datas = datas
        self.data_last_index = 0

        data_source = DataSource()
        self.data_source = data_source

        drawer = CandleDrawer()
        self.data_source.add_drawer(drawer)
        self.drawer = drawer

        self.init_ui()
        self.chart.add_drawer(drawer)

        self.t = QTimer()
        self.t.timeout.connect(self.add_one_data)
        self.t.start(10)

        for i in range(100):
            # for i in range(300):
            # for i in range(30):
            self.add_one_data()

    def init_ui(self):
        self.chart = BarChartWidget(self)
        self.setCentralWidget(self.chart)
        pass

    def add_one_data(self):
        self.chart.repaint()
        if self.data_last_index == len(self.datas):
            self.data_last_index = 0
        data = self.datas[self.data_last_index]
        self.data_source.append(data)
        self.chart.set_x_range(0, self.data_last_index)

        self.data_last_index += 1


def parse_datetime(dt_str: str):
    return datetime.strptime(dt_str, "%Y-%m-%d")


def read_data():
    with open("Stk_Day.csv", "rt", encoding="gbk") as f:
        reader = csv.DictReader(f)
        i = 0
        for item in reader:
            symbol = item["代码"]
            if symbol != "SH600000":
                continue
            # 代码, 时间, 开盘价, 最高价, 最低价, 收盘价, 成交量(股), 成交额(元)
            open_price = float(item["开盘价"])
            high = float(item["最高价"])
            low = float(item["最低价"])
            close = float(item["收盘价"])
            dt_str = item["时间"]
            datetime = parse_datetime(dt_str)
            bar_data = CandleData(
                open=open_price,
                low=low,
                high=high,
                close=close,
                datetime=datetime,
            )
            i += 1
            yield bar_data


def main():
    app = QApplication([])

    datas = read_data()

    mainWindow = MainWindow(list(datas))
    mainWindow.setWindowTitle("Candlestick")
    availableGeometry = app.desktop().availableGeometry(mainWindow)
    size = availableGeometry.height() * 3 / 4
    mainWindow.resize(size, size)
    mainWindow.show()

    app.exec()


if __name__ == '__main__':
    main()

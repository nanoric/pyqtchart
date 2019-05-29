import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import List, Optional

from PyQt5 import QtChart
from PyQt5.QtCore import QPointF, QRectF, QTimer, Qt
from PyQt5.QtGui import QMouseEvent, QPainter, QWheelEvent
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QMainWindow,
    QStyleOptionGraphicsItem,
    QWidget,
)


def get_price_range(datas: List["InternalData"]):
    l = min(datas, key=lambda x: x.bar_data.low)
    h = max(datas, key=lambda x: x.bar_data.high)
    return l.bar_data.low, h.bar_data.high


@dataclass()
class InternalData:
    bar_data: "BarData"
    x: int

    def __post_init__(self):
        # self.x_labels = self.bar_data.datetime.strftime("%Y\n%m%d").split('\n')
        self.x_label = self.bar_data.datetime.strftime("%Y%m%d")
        self.qt_data = self.bar_data.to_qt_data(self.x)


@dataclass()
class DraggingInfo:
    start_pos: QPointF
    showing_index_end: int


class Indicator(QGraphicsItem):

    def __init__(self, data: "InternalData", scene: QGraphicsScene, parent=None):
        super().__init__(parent)
        self.rect = QRectF(0, 0, 0, 0)
        self.data: "InternalData" = data

    def boundingRect(self):
        # fucking PyQt5 binding: return value of boundingRect should be QRectF
        return QRectF(self.rect.adjusted(-2, -2, 2, 2))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget = None,
    ):
        painter.drawRect(self.rect)
        b = self.data.bar_data
        text = (
            f"open: {b.open}\n"
            f"high: {b.high}\n"
            f"low: {b.low}\n"
            f"close: {b.close}\n"
            f"date: {self.data.x}"
        )
        rect = painter.boundingRect(0.0, 0.0, 1000.0, 1000.0, Qt.AlignLeft, text)
        painter.drawText(self.rect, Qt.AlignLeft, text)
        self.rect = rect  # fixme: scrolling will make this mismatch


class CandlestickView(QtChart.QChartView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.series = QtChart.QCandlestickSeries()
        self.series.setUseOpenGL(True)
        self.chart = QtChart.QChart()
        self.chart.addSeries(self.series)
        self.setChart(self.chart)

        # x axis
        self.x_scrolling = QtChart.QValueAxis()  # x axis used for scrolling
        self.x_scrolling.setTickType(QtChart.QValueAxis.TicksFixed)
        self.x_scrolling.setLabelsVisible(False)
        self.x_scrolling.setVisible(False)
        self.chart.setAxisX(self.x_scrolling, self.series)

        # y axis
        self.y = QtChart.QValueAxis()
        self.y.setTitleText("price")

        self.chart.setAxisY(self.y, self.series)
        self.chart.legend().hide()
        self.chart.setTitle("BarData")

        # visual control
        self.days_to_show = 20
        self.price_window_scale = 1.1
        self.showing_index_end = 0  # 非正数表示数组最末尾的第n个，正数表示除了显示最新的数据以外还额外显示空白数据

        self.indicator: Optional[Indicator] = None
        self.crosshair_h: Optional[QGraphicsLineItem] = None
        self.crosshair_v: Optional[QGraphicsLineItem] = None
        self.indicator_index = None  # index in self.showing_records

        # config
        self.x_zoom_scale_ratio = 0.5
        self.max_padding_days = 3  # 最多显示的空白数据数量，也就是限制self.showing_index_end的最大值
        self.y_label_count = 30
        self.y_scale_threshold = 1.1

        # status variables
        self.dragging = False
        self.dragging_info: Optional[DraggingInfo] = None

        self.showing_records: List["InternalData"] = []

        # data record(use model/view to reduce memory if necessary)
        self.datas: List["InternalData"] = []

        # intermediate variables to speed up calculation
        self.y_range = 1  # used in redraw_indicator
        self.y_min = 1  # used in redraw_indicator
        self.y_max = 1  # used in redraw_indicator

        # redraw
        self.redraw_lock = Lock()
        self.redraw_scheduled = False
        self.redraw_y_lock = Lock()
        self.redraw_y_scheduled = False

    def append_record(self, bar_data):
        """Add a record"""
        i = len(self.datas)
        data = InternalData(bar_data, i)

        # add data to series
        self.series.append(data.qt_data)  # use redraw to sort data
        self.datas.append(data)

        # refresh chart
        self.schedule_redraw()

    def redraw(self):
        with self.redraw_lock:
            self.redraw_scheduled = False

        days_to_show = min(len(self.datas), self.days_to_show)
        if days_to_show < 2:
            return

        if self.showing_index_end >= 0:
            ndatas = (days_to_show - self.showing_index_end)
            records_to_show: List["InternalData"] = self.datas[-ndatas:]
            empty_columns = self.showing_index_end
        else:
            empty_columns = 0
            records_to_show = self.datas[:self.showing_index_end]
            records_to_show = records_to_show[-days_to_show:]
        if not records_to_show:
            return

        # x range
        self.fit_x_range(records_to_show, empty_columns)

        # y range
        self._schedule_fit_y_range(records_to_show)

        self.draw_indicator()
        self.showing_records: List["InternalData"] = records_to_show

    def draw_indicator(self):
        index = self.indicator_index
        if index is not None:
            index = max(0, index)
            index = min(len(self.showing_records) - 1, index)
            data = self.showing_records[index]
            x = self.column_width() * (index + 0.5) + self.plot_area().left()
            y_price = (data.bar_data.open + data.bar_data.close) / 2
            price_percent = (y_price - self.y_min) / self.y_range
            y = (1 - price_percent) * self.column_height() + self.plot_area().top()
            if self.indicator is None:
                scene: QGraphicsScene = self.scene()
                indicator = Indicator(data, scene)
                scene.addItem(indicator)
                self.indicator = indicator
                self.crosshair_h: QGraphicsLineItem = scene.addLine(
                    self.plot_area().left(), y, self.plot_area().left() + self.plot_area().width(),
                    y
                )
                self.crosshair_v: QGraphicsLineItem = scene.addLine(
                    x, 0, x, self.plot_area().height()
                )
            else:
                self.indicator.setX(x)
                self.indicator.setY(y)
                self.crosshair_h.setLine(
                    self.plot_area().left(), y, self.plot_area().left() + self.plot_area().width(),
                    y
                )
                self.crosshair_v.setLine(
                    x, self.plot_area().top(), x, self.plot_area().height() + self.plot_area().top()
                )
                self.indicator.data = data

    def fit_x_range(self, records_to_show: List["InternalData"], empty_columns: int):
        # scrolling by setRange
        start = records_to_show[0].x - 0.5
        end = records_to_show[-1].x + empty_columns + 0.5
        columns = len(records_to_show) + 1 + empty_columns
        if start != self.x_scrolling.min() or end != self.x_scrolling.max():
            self.x_scrolling.setRange(start, end)
            self.x_scrolling.setTickCount(columns)

    def _schedule_fit_y_range(self, records_to_show):
        with self.redraw_y_lock:
            if self.redraw_y_scheduled:
                return
            new_y_low, new_y_high = self.calculate_new_y_range(records_to_show)
            new_y_range = new_y_high - new_y_low
            if (new_y_low < self.y_min
                or new_y_high > self.y_max
                or self.y_range * self.y_scale_threshold < new_y_range
                or self.y_range / self.y_scale_threshold > new_y_range
            ):
                self.redraw_y_scheduled = records_to_show
                QTimer.singleShot(300, self._fit_y_range)

    def _fit_y_range(self):
        with self.redraw_y_lock:
            records_to_show = self.redraw_y_scheduled
            self.redraw_y_scheduled = None
        new_y_low, new_y_high = self.calculate_new_y_range(records_to_show)
        self.y.setRange(new_y_low, new_y_high)
        self.y_min = new_y_low
        self.y_max = new_y_high
        self.y_range = self.y.max() - self.y.min()
        self.y.setTickCount(self.y_label_count)

    def calculate_new_y_range(self, records_to_show):
        price_low, price_high = get_price_range(records_to_show)
        price_mid = (price_low + price_high) / 2
        price_length_2_scaled = (price_high - price_low) / 2 * self.price_window_scale
        new_y_low = price_mid - price_length_2_scaled
        new_y_high = price_mid + price_length_2_scaled
        return new_y_low, new_y_high

    def plot_area_fixed(self) -> QRectF:
        width = int(self.column_width()) * self.days_to_show
        area = self.plot_area()
        return area.adjusted(width - area.width(), 0, 0, 0)

    def plot_area(self) -> QRectF:
        return self.chart.plotArea()

    def column_height(self):
        return self.plot_area().height()

    def column_width(self):
        return self.plot_area().width() / self.days_to_show

    def mousePressEvent(self, event: QMouseEvent):
        if not self.dragging:
            self.dragging = True
            self.dragging_info = DraggingInfo(
                start_pos=event.localPos(),  # return value of localPos is float, pos is int.
                showing_index_end=self.showing_index_end
            )

    def schedule_redraw(self):
        with self.redraw_lock:
            if self.redraw_scheduled:
                return
            self.redraw_scheduled = True
        QTimer.singleShot(0, self.redraw)

    def mouseMoveEvent(self, event: QMouseEvent):
        new_pos = event.localPos()
        column_width = self.column_width()

        # dragging: scroll right or left
        if self.dragging:
            dpos: QPointF = new_pos - self.dragging_info.start_pos
            dx = round(dpos.x() / column_width)
            showing_index_end = self.dragging_info.showing_index_end - dx
            self.set_showing_index_end(showing_index_end)

        # mouse move: change pos of indicator
        pos_in_chart = new_pos - self.chart.plotArea().topLeft()
        indicator_index = int(pos_in_chart.x() / column_width)
        self.set_indicator_index(indicator_index)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.dragging:
            self.dragging = False

    def wheelEvent(self, event: QWheelEvent):
        p = event.angleDelta()
        dy = -p.y() / 360 * self.x_zoom_scale_ratio
        if not dy:
            return
        days_to_show = self.days_to_show
        ddays = int(days_to_show * dy)
        if ddays == 0:
            days_to_show += int(dy / dy)  # +=1 / -= 1
        else:
            days_to_show += ddays
        self.set_days_to_show(days_to_show)

    def set_indicator_index(self, index):
        index = max(0, index)
        index = min(len(self.showing_records) - 1, index)
        if index != self.indicator_index:
            self.indicator_index = index
            self.schedule_redraw()

    def set_showing_index_end(self, showing_index_end):
        if showing_index_end > self.max_padding_days:
            showing_index_end = self.max_padding_days
        if showing_index_end < -len(self.datas) + 1:
            showing_index_end = -len(self.datas) + 1
        if showing_index_end != self.showing_index_end:
            self.showing_index_end = showing_index_end
            self.schedule_redraw()

    def set_days_to_show(self, days_to_show):
        days_to_show = max(days_to_show, 1)  # minimum 1 days to show
        days_to_show = min(days_to_show,
                           len(self.datas) + self.max_padding_days)  # maximum 100 days to show
        if days_to_show != self.days_to_show:
            self.days_to_show = days_to_show
            self.schedule_redraw()


class MainWindow(QMainWindow):

    def __init__(self, datas: List["BarData"], parent=None):
        super().__init__(parent)
        self.bar_datas = datas
        self.data_last_index = 0

        self.init_ui()
        self.chart.days_to_show = 10

        self.t = QTimer()
        self.t.timeout.connect(self.add_one_data)
        # self.t.start(2000)

        for i in range(3000):
            # for i in range(300):
            # for i in range(30):
            self.add_one_data()

    def init_ui(self):
        self.chart = CandlestickView(self)
        self.setCentralWidget(self.chart)
        pass

    def add_one_data(self):
        bar_data = self.bar_datas[self.data_last_index]
        self.chart.append_record(bar_data)
        self.data_last_index += 1


def parse_datetime(dt_str: str):
    return datetime.strptime(dt_str, "%Y-%m-%d")


@dataclass()
class BarData:
    symbol: str
    open: float
    low: float
    high: float
    close: float
    datetime: datetime

    def to_qt_data(self, x):
        qt_data = QtChart.QCandlestickSet()
        qt_data.setOpen(self.open)
        qt_data.setClose(self.close)
        qt_data.setHigh(self.high)
        qt_data.setLow(self.low)
        qt_data.setTimestamp(x)
        return qt_data


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
            bar_data = BarData(
                symbol=symbol,
                open=open_price,
                low=low,
                high=high,
                close=close,
                datetime=datetime,
            )
            i += 1
            yield bar_data


if __name__ == "__main__":
    app = QApplication(sys.argv)

    datas = read_data()

    mainWindow = MainWindow(list(datas))
    mainWindow.setWindowTitle("Candlestick")
    availableGeometry = app.desktop().availableGeometry(mainWindow)
    size = availableGeometry.height() * 3 / 4
    mainWindow.resize(size, size)
    mainWindow.show()
    sys.exit(app.exec_())

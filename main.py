import csv
from dataclasses import dataclass
from datetime import datetime
from typing import List, TypeVar

import math
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QPen, QPicture
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from AdvancedBarChart import AdvancedBarChart
from Axis import CandleAxisX, ValueAxisY
from BarChart import BarChartWidget
from DataSource import CandleData, DataSource
from Drawer import BarChartDrawer, CandleDrawer

T = TypeVar("T")


class Pen:
    NO = QPen(QColor(0, 0, 0, 0))


class PlotWidget(QPicture):
    pass


@dataclass()
class MyData(CandleData):
    volume: float = 0


class FtpCounter(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._refresh_interval_ms = 1000
        self._tick = 0
        self.setMaximumHeight(30)

        timer = QTimer()
        timer.timeout.connect(self.update_tick)
        timer.start(self.refresh_interval_ms)
        self.timer = timer

    @property
    def refresh_interval_ms(self):
        return self._refresh_interval_ms

    @refresh_interval_ms.setter
    def refresh_interval_ms(self, val):
        self._refresh_interval_ms = val
        self.timer.start(self.refresh_interval_ms)

    def tick(self):
        self._tick += 1

    def update_tick(self):
        fps = self._tick * 1000 / self.refresh_interval_ms
        self.setText(f"{fps}")
        self._tick = 0


class MainWindow(QMainWindow):

    def __init__(self, datas: List["MyData"], parent=None):
        super().__init__(parent)
        self._init_ui()
        self.datas = datas
        self.data_last_index = 0

        main_data_source = DataSource(self)
        sub_data_source = DataSource(self)

        main_chart = BarChartWidget()
        sub_chart = BarChartWidget()

        main_chart.add_drawer(CandleDrawer(main_data_source))
        main_chart.add_drawer(CandleDrawer())
        main_chart.add_axis(CandleAxisX(main_data_source), ValueAxisY())

        # test for main chart axis
        # main_chart.add_axis(ValueAxisY())
        # main_chart.add_axis(BarAxisY())

        sub_chart.add_drawer(BarChartDrawer(sub_data_source))
        sub_chart.add_drawer(BarChartDrawer())
        sub_chart.add_axis(CandleAxisX(main_data_source), ValueAxisY())

        # test for sub chart axis
        # sub_chart.add_axis(ValueAxisX())
        # sub_chart.add_axis(CandleAxisX(main_data_source))

        self.main_chart = main_chart
        self.sub_chart = sub_chart

        self.main_data_source = main_data_source
        self.sub_data_source = sub_data_source

        cs1 = self.advanced_chart_widget.add_bar_chart(
            main_chart, 5
        ).create_cross_hair()
        cs2 = self.advanced_chart_widget.add_bar_chart(sub_chart, 1).create_cross_hair()
        cs1.sync_x_to(cs2)
        cs2.sync_x_to(cs1)

        self.t = QTimer()
        self.t.timeout.connect(self.on_timer)

        for i in range(3000):
            # for i in range(300):
            # for i in range(30):
            self.add_one_data()

        self.stress_fps_tick()
        # self.t.start(1000)

        self.hook_paint_event()

    def _init_ui(self):
        # status layout
        status_layout = QHBoxLayout()
        fps = FtpCounter()
        n = QLabel()
        n.setMaximumHeight(60)
        status_layout.addWidget(fps)
        status_layout.addWidget(n)

        # main layout
        main_layout = QVBoxLayout()

        advanced_chart_widget = AdvancedBarChart()

        main_layout.addLayout(status_layout)
        main_layout.addWidget(advanced_chart_widget)

        w = QWidget()
        w.setLayout(main_layout)
        self.setCentralWidget(w)
        self.advanced_chart_widget = advanced_chart_widget

        self.fps = fps
        self.n = n

    def hook_paint_event(self):
        org_paint_handler = self.main_chart.paintEvent

        def paintEventWithFPSCounter(*args):
            org_paint_handler(*args)
            self.fps.tick()

        self.main_chart.paintEvent = paintEventWithFPSCounter

    def on_timer(self):
        self.add_one_data()

    def stress_fps_tick(self):
        self.add_one_data()
        QTimer.singleShot(0, self.stress_fps_tick)

    def add_one_data(self):
        if self.data_last_index == len(self.datas):
            self.data_last_index = 0
            self.sub_data_source.clear()
        data = self.datas[self.data_last_index]

        self.main_data_source.append(data)
        self.sub_data_source.append(data.volume)
        self.main_chart.set_x_range(0, self.data_last_index)
        self.sub_chart.set_x_range(0, self.data_last_index)

        self.data_last_index += 1
        self.n.setText(
            f"# of showing:{self.data_last_index} \n"
            f"# of main datas: {len(self.main_data_source)}\n"
            f"# of sub datas: {len(self.sub_data_source)}"
        )


def parse_datetime(dt_str: str):
    return datetime.strptime(dt_str, "%Y-%m-%d")


def gen_wave(i, p=0, T=360, a=1000):
    return a * math.sin((i - p) / T * math.pi)


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
            bar_data = MyData(
                open=open_price,
                low=low,
                high=high,
                close=close,
                datetime=datetime,
                volume=gen_wave(i, 31) + gen_wave(i, 15, 70) + gen_wave(i, 30, 80),
            )
            i += 1
            yield bar_data


def main():
    app = QApplication([])

    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    datas = read_data()

    mainWindow = MainWindow(list(datas))
    mainWindow.setWindowTitle("Candlestick")
    availableGeometry = app.desktop().availableGeometry(mainWindow)
    size = availableGeometry.height() * 3 / 4
    mainWindow.resize(size, size)
    mainWindow.show()

    app.exec()


if __name__ == "__main__":
    main()

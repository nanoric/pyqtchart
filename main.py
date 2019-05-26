import csv
from datetime import datetime
from typing import List, TypeVar

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QPen, QPicture
from PyQt5.QtWidgets import QApplication, QMainWindow

from BarChart import BarChartWidget
from CandleDrawer import CandleData, CandleDrawer
from DataSource import DataSource

T = TypeVar("T")


class Pen:
    NO = QPen(QColor(0, 0, 0, 0))


class PlotWidget(QPicture):
    pass


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
        self.t.timeout.connect(self.on_timer)
        self.t.start(10)

        # for i in range(3600):
            # for i in range(300):
        for i in range(30):
            self.add_one_data()

    def init_ui(self):
        self.chart = BarChartWidget(self)
        self.setCentralWidget(self.chart)
        pass

    def on_timer(self):
        self.add_one_data()

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

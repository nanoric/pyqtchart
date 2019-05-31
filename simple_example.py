from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
)

from chart import ChartWidget, DataSource, HistogramDrawer, ValueAxisX, ValueAxisY


def main():
    app = QApplication([])

    data_source = DataSource()
    chart = ChartWidget()

    drawer = HistogramDrawer(data_source)
    drawer.positive_color = "red"
    drawer.negative_color = "green"
    chart.add_drawer(drawer)

    axis_x = ValueAxisX()
    axis_x.label_drawer.label_color = "blue"
    axis_x.label_drawer.label_font = QFont("新宋体")
    axis_x.grid_drawer.grid_color = "lightgray"
    axis_y = ValueAxisY()
    chart.add_axis(axis_x, axis_y)
    chart.show()
    chart.plot_area_edge_color = "black"

    data_source.append(100)
    data_source.append(110)
    data_source.append(120)
    data_source.append(90)
    data_source.append(130)
    data_source.extend([-130, -120])
    chart.set_x_range(0, 7)
    axis_x.label_count = 7


    app.exec()


if __name__ == "__main__":
    main()

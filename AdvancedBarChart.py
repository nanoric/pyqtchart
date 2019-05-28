from typing import List, TypeVar

from PyQt5.QtGui import QMouseEvent, QPainter
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from BarChart import BarChartWidget
from Base import AxisBase, DrawConfig, Orientation

T = TypeVar("T")


class CrossHairAxisX(AxisBase):

    def __init__(self):
        super().__init__(Orientation.HORIZONTAL)

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        pass

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        pass


class CrossHairAxisY(AxisBase):

    def __init__(self):
        super().__init__(Orientation.VERTICAL)

    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        pass

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        pass


class CrossHair:

    def __init__(self):
        self.axis_x = CrossHairAxisX()
        self.axis_y = CrossHairAxisY()


class ValuePannel(QWidget):
    pass


class AdvancedBarChart(QWidget):
    """
    AdvancedBarChart(ABC) is a  widget combining multiple BarChart.
    The data in different BarChart can have different Drawer and different DataSource,

    You can add multiple BarChart into one ABC.
    ABC also provide an Value Panel, and a CrossHair showing information about the value under cursor.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._charts: List["BarChartWidget"] = []

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)

        self.setLayout(main_layout)
        self.main_layout = main_layout

        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: "QMouseEvent"):
        event.ignore()

    @property
    def chart_spacing(self):
        return self.main_layout.spacing()

    @chart_spacing.setter
    def chart_spacing(self, spacing: int):
        self.main_layout.setSpacing(spacing)

    def add_bar_chart(self, chart: "BarChartWidget", weight: int = 1, show_cross_hair: bool = True):
        # size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # size_policy.setVerticalStretch(weight)
        # chart.setSizePolicy(size_policy)
        if chart not in self._charts:
            # fix padding
            left, right = 80, 10
            if self._charts:
                last_chart = self._charts[-1]
                l, t, r, b = last_chart.paddings
                last_chart.paddings = (l, t, r, 0)
            top, bottom = 0, 20
            chart.paddings = (left, top, right, bottom)

            # add axis as cross_hair
            chart.add_axis()

            self.main_layout.addWidget(chart, weight)
            self._charts.append(chart)

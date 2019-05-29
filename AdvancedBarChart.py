from typing import List, TypeVar

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QMouseEvent, QPainter
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from Axis import AxisBase
from BarChart import BarChartWidget
from Base import Orientation
from Drawer import DrawConfig

T = TypeVar("T")


class CrossHairAxisX(AxisBase):

    def __init__(self, underlying_axis: AxisBase):
        super().__init__(Orientation.HORIZONTAL)
        self.underlying_axis = underlying_axis
        self.x = 0

    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        return

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        return


class CrossHairAxisY(AxisBase):

    def __init__(self, underlying_axis: AxisBase):
        super().__init__(Orientation.VERTICAL)
        self.underlying_axis = underlying_axis

    def draw_grids(self, config: "DrawConfig", painter: QPainter):
        return

    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        return


class ValuePanel(QWidget):
    pass


class SubChartWrapper:

    def __init__(self, chart: "BarChartWidget", cross_hair_x, cross_hair_y):
        self.cross_hair_y: CrossHairAxisY = cross_hair_y
        self.cross_hair_x: CrossHairAxisX = cross_hair_x
        self.chart = chart

    def create_cross_hair_x(self):
        assert self.cross_hair_x is None
        chart = self.chart
        axis_x_list = chart.all_axis_x
        if len(axis_x_list) == 0:
            return
        choose = axis_x_list[0]
        axis = CrossHairAxisX(choose)
        self.chart.add_axis(axis)
        self.cross_hair_x = axis
        return self

    def create_cross_hair_y(self):
        assert self.cross_hair_y is None
        chart = self.chart
        axis_y_list = chart.all_axis_y
        if len(axis_y_list) == 0:
            return
        choose = axis_y_list[0]
        axis = CrossHairAxisY(choose)
        self.chart.add_axis(axis)
        self.cross_hair_y = axis
        return self

    def create_cross_hair(self):
        self.create_cross_hair_x()
        self.create_cross_hair_y()
        return self


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
        self._sub_wrappers: List["SubChartWrapper"] = []

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)
        self.main_layout = main_layout

        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: "QMouseEvent"):
        pos = event.localPos()
        x = pos.x()
        y = pos.y()
        for wrapper in self._sub_wrappers:
            if wrapper.cross_hair_x:
                wrapper.cross_hair_x.x = x
            if wrapper.cross_hair_y:
                wrapper.cross_hair_y.y = y

    @property
    def chart_spacing(self):
        return self.main_layout.spacing()

    @chart_spacing.setter
    def chart_spacing(self, spacing: int):
        self.main_layout.setSpacing(spacing)

    def add_bar_chart(self,
                      chart: "BarChartWidget",
                      weight: int = 1,
                      cross_hair_x: "CrossHairAxisX" = None,
                      cross_hair_y: "CrossHairAxisY" = None,
                      ):
        if chart not in self._sub_wrappers:
            # fix padding
            left, right = 80, 10
            if self._sub_wrappers:
                last_chart = self._sub_wrappers[-1].chart
                l, t, r, b = last_chart.paddings
                last_chart.paddings = (l, t, r, 0)
            top, bottom = 0, 20
            chart.paddings = (left, top, right, bottom)

            # add axis as cross_hair
            if cross_hair_x:
                chart.add_axis(cross_hair_x)
            if cross_hair_y:
                chart.add_axis(cross_hair_y)
            wrapper = SubChartWrapper(chart, cross_hair_x, cross_hair_y)
            self.main_layout.addWidget(chart, weight)
            self._sub_wrappers.append(wrapper)

            return wrapper

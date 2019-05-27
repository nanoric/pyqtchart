from abc import ABC, abstractmethod
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, TypeVar, Union

from PyQt5.QtGui import QColor, QFont, QPainter, QPalette
from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from DataSource import DataSource

from typing import Optional

from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QTransform

T = TypeVar("T")

ColorType = Union[
    str,  # "red", "#RGB", "#RRGGBB", "#AARRGGBB", "#RRRGGGBBB", "#RRRRGGGGBBBB"
    int,  # Qt.GlobalColor
    QColor,  # QtCore.QColor
    None,  # Don't draw
]


class DrawingCache:

    def __init__(self):
        # intermediate variables to speed up calculation
        self.drawer_transform: Optional["QTransform"] = None  # 坐标转化矩阵(UI->drawer)
        self.ui_transform: Optional["QTransform"] = None  # 坐标转化矩阵(drawer->UI)
        self.drawer_area: Optional['QRectF'] = None  # drawer坐标的世界大小
        self.plot_area: Optional['QRectF'] = None  # UI坐标中属于绘制区域的部分

    def drawer_to_ui(self, value: T) -> T:
        """
        将drawer坐标系中的值（点或者矩形）转化为UI坐标系
        """
        return self.drawer_transform.map(value)

    def drawer_x_to_ui(self, value: float) -> float:
        """
        将drawer坐标系中的x值转化为UI坐标系中的x值
        """
        return self.drawer_transform.map(QPointF(value, value)).x()

    def drawer_y_to_ui(self, value: float) -> float:
        """
        将drawer坐标系中的y值转化为UI坐标系中的y值
        """
        return self.drawer_transform.map(QPointF(value, value)).y()

    def ui_height_to_drawer(self, value: float) -> float:
        return value / self.plot_area.height() * self.drawer_area.height()


class DrawConfig:

    def __init__(self):
        self.begin: int = 0  # 第一个绘制的元素
        self.end: int = 0  # 最后一个绘制的元素+1：也就是说绘制元素的范围为[begin, end)
        self.y_low: float = 0  # 图表顶端所代表的y值
        self.y_high: float = 1  # 图表底端所代表的y值

        self.drawing_cache: Optional["DrawingCache"] = None


class DrawerBase(ABC):
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

    def __init__(self, data_source: Optional["DataSource"] = None):
        self._data_source: Optional["DataSource"] = None
        self._data_source_lock = Lock()
        self.set_data_source(data_source)

    def set_data_source(self, data_source: "DataSource"):
        with self._data_source_lock:
            if self._data_source is not data_source:
                if self._data_source is not None:
                    self._detach_data_source()
                self._data_source = data_source
                self._attach_data_source()

    def has_data(self):
        return self._data_source is not None and len(self._data_source)

    def on_data_source_data_removed(self, begin: int, end: int):
        pass

    def on_data_source_destroyed(self):
        with self._data_source_lock:
            self._data_source = None

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
    def draw(self, config: "DrawConfig", painter: QPainter):
        """
        绘制数据，可以在整张图上任意绘制，但是该函数最好每次只绘制坐标属于x的图
        坐标系(以下称为drawer坐标系)使用和数据x-y值一致的坐标系:原点在左下角，x轴向右,y轴向上 => 坐下到右上
        整个图形的坐标范围为: (left, bottom, right, top) = (begin, y_low, end, y_high)
        因为图标并不知道数据的任何细节，所以draw_item函数应该自己检查x值是否越界
        """
        pass

    def _attach_data_source(self):
        self._data_source.data_removed.connect(self.on_data_source_data_removed)
        self._data_source.destroyed.connect(self.on_data_source_destroyed)

    def _detach_data_source(self):
        raise RuntimeError("Rest of DataSource is currently not implemented.")


class Orientation(Enum):
    HORIZONTAL = 1
    VERTICAL = 2


class AxisBase:

    def __init__(self, orientation: Orientation):
        palette = QPalette()
        self.axis_visible: bool = True
        self.orientation = orientation

        self.grid_visible: bool = True
        self.grid_color: "ColorType" = palette.color(QPalette.Dark)

        self.label_visible = True
        self.label_color: "ColorType" = palette.color(QPalette.Foreground)
        self.label_font: QFont = QFont()
        # spacing to plot_area, right for Vertical AxisBase, top for Horizontal
        self.label_spacing_to_plot_area: int = 2

    # @virtual
    def prepare_draw(self, config: "DrawConfig"):
        pass

    @abstractmethod
    def draw_grid(self, config: "DrawConfig", painter: QPainter):
        pass

    @abstractmethod
    def draw_labels(self, config: "DrawConfig", painter: QPainter):
        pass

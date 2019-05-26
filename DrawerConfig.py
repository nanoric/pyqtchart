from typing import Optional

from PyQt5.QtCore import QRectF, QPoint, QPointF
from PyQt5.QtGui import QColor, QTransform


class DrawingCache:
    def __init__(self):
        # intermediate variables to speed up calculation
        self.drawer_transform: Optional["QTransform"] = None  # 坐标转化矩阵(UI->drawer)
        self.drawer_area: Optional['QRectF'] = None  # drawer坐标的世界大小
        self.plot_area: Optional['QRectF'] = None  # UI坐标中属于绘制区域的部分

    def drawer_to_ui(self, value):
        """
        将drawer坐标系中的值（点或者矩形）转化为UI坐标系
        """
        return self.drawer_transform.map(value)

    def drawer_x_to_ui(self, value: float):
        """
        将drawer坐标系中的x值转化为UI坐标系中的x值
        """
        return self.drawer_transform.map(QPointF(value, 0)).x()

    def drawer_y_to_ui(self, value: float):
        """
        将drawer坐标系中的x值转化为UI坐标系中的x值
        """
        return self.drawer_transform.map(QPointF(0, value)).y()


class DrawConfig:

    def __init__(self):
        self.begin: int = 0  # 第一个绘制的元素
        self.end: int = 0  # 最后一个绘制的元素+1：也就是说绘制元素的范围为[begin, end)
        self.y_low: float = 0  # 图表顶端所代表的y值
        self.y_high: float = 1  # 图表底端所代表的y值

        self.drawing_cache: Optional["DrawingCache"] = None



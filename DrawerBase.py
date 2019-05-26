from abc import ABC, abstractmethod
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING, TypeVar

from PyQt5.QtGui import QPainter

if TYPE_CHECKING:
    from DataSource import DataSource
    from DrawerConfig import DrawConfig

T = TypeVar("T")


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
    def draw(self, config: "DrawConfig", painter: QPainter):
        """
        绘制数据，可以在整张图上任意绘制，但是该函数最好每次只绘制坐标属于x的图
        坐标系(以下称为drawer坐标系)使用和数据x-y值一致的坐标系:原点在左下角，x轴向右,y轴向上 => 坐下到右上
        整个图形的坐标范围为: (left, bottom, right, top) = (begin, y_low, end, y_high)
        因为图标并不知道数据的任何细节，所以draw_item函数应该自己检查x值是否越界
        """
        pass

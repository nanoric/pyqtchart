from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import List, TypeVar, Optional, TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPainter

if TYPE_CHECKING:
    from Drawer import DrawConfig

T = TypeVar("T")


class DataSource(QObject):
    """
    DataSource for a Drawer.
    A DataSource is just like a list, but not all the operation is supported in list.
    Supported operations are:
    append(), clear(), __len__(), __getitem__(),
    """
    data_removed = pyqtSignal(int, int)  # (start: int, end: int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_list: List[T] = []

    def append(self, object: T) -> None:
        self.data_list.append(object)

    def clear(self) -> None:
        self.data_removed.emit(0, len(self.data_list))
        self.data_list.clear()

    def __getitem__(self, item):
        return self.data_list[item]

    def __len__(self):
        return len(self.data_list)

    def __str__(self):
        return str(self.data_list)

    def __repr__(self):
        return repr(self.data_list)


# should be DataSource["CandleData"], but QObject makes this impossible
CandleDataSourceType = List["CandleData"]


@dataclass
class CandleData:
    """
    Represent a single record in DataSource for CandleDrawer
    """
    open: float
    low: float
    high: float
    close: float
    datetime: datetime


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
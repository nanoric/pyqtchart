from dataclasses import dataclass
from datetime import datetime
from typing import List, TypeVar

from PyQt5.QtCore import QObject, pyqtSignal

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

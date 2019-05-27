from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, TypeVar

T = TypeVar("T")


class DataSource(List[T]):
    """
    DataSource for a Drawer.
    A DataSource is just like a list, but not all the operation is supported in list.
    Supported operations are:
    append(), clear(), __len__(), __getitem__(),
    """

    def __init__(self, data_list: Iterable[T] = None):
        super().__init__()
        if data_list is None:
            data_list = []
        self.data_list = data_list

    def append(self, object: T) -> None:
        self.data_list.append(object)

    def clear(self) -> None:
        self.data_list.clear()

    def __getitem__(self, item):
        return self.data_list[item]

    def __len__(self):
        return len(self.data_list)

    def __str__(self):
        return str(self.data_list)

    def __repr__(self):
        return repr(self.data_list)


CandleDataSourceType = DataSource["CandleData"]


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

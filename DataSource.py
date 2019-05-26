from typing import Any, List, TYPE_CHECKING, Type, TypeVar, Generic

if TYPE_CHECKING:
    from Base import DrawerBase

T = TypeVar("T")


class DataSource(list, List[T]):

    def __init__(self):
        super().__init__()
        self._drawers: List["DrawerBase"] = []

    # def add_drawer(self, drawer: "DrawerBase"):
    #     if drawer not in self._drawers:
    #         self._drawers.append(drawer)
    #         drawer._data_source = self

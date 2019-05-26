from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from DrawerBase import DrawerBase


class DataSource(list):

    def __init__(self):
        super().__init__()
        self._drawers: List["DrawerBase"] = []

    def add_drawer(self, drawer: "DrawerBase"):
        if drawer not in self._drawers:
            self._drawers.append(drawer)
            drawer._data_source = self

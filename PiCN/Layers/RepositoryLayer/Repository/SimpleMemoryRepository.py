"""A simple in-memory repository"""

from multiprocessing import Manager

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Name, Content
from PiCN.Logger import Logger

from typing import Dict


class SimpleMemoryRepository(BaseRepository):
    """A simple in-memory repository"""

    def __init__(self, prefix: Name, manager: Manager, logger: Logger=None):
        super().__init__(prefix, manager)
        self.logger = logger
        self._storage: Dict[Name, object] = manager.dict()

    def is_content_available(self, icnname: Name) -> bool:
        if icnname is None or not self._prefix.value.is_prefix_of(icnname):
            return False
        return icnname in self._storage

    def get_content(self, icnname: Name) -> Content:
        if icnname not in self._storage:
            return None
        data = self._storage[icnname]
        return Content(icnname, data)

    def add_content(self, icnname: Name, data):
        if icnname is None or not self._prefix.value.is_prefix_of(icnname):
            return None
        self._storage[icnname] = data

    def remove_content(self, icnname: Name):
        if icnname is None or icnname not in self._storage:
            return
        del self._storage[icnname]

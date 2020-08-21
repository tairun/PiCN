"""Base Class for PiCN Repositories"""

import abc
from multiprocessing import Manager

from PiCN.Packets import Content, Name


class BaseRepository(object):
    """Base Class for PiCN Repositories"""

    def __init__(self, prefix: Name, manager: Manager):
        self._prefix: manager.Value = manager.Value(Name, prefix)

    @abc.abstractmethod
    def is_content_available(self, icnname: Name) -> bool:
        """check if a content object is available in the repo"""

    @abc.abstractmethod
    def get_content(self, icnname: Name) -> Content:
        """Get a content object from the repo"""

    def set_prefix(self, prefix: Name) -> None:
        """Set the prefix for the repo"""
        self._prefix.value = prefix

    def get_prefix(self) -> Name:
        return self._prefix.value

    def get_data_size(self, icnname: Name):
        """Returns the size, of a data object
        :returns Size of data object if available
        :returns None if data object is not available
        """
        if not self.is_content_available(icnname):
            return None
        data = self.get_content(icnname)
        size = len(data.content)
        return size

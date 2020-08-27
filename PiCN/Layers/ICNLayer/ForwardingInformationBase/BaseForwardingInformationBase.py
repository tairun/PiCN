"""Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

import abc
import multiprocessing

from PiCN.Layers.ICNLayer import BaseICNDataStruct
from PiCN.Packets import Name
from tabulate import tabulate

from typing import List, Optional


class ForwardingInformationBaseEntry(object):
    """An entry in the Forwarding Information Base"""

    def __init__(self, name: Name, faceid: List[int], static: bool = False, is_session: bool = False):
        self._name: Name = name
        self._is_session = is_session
        self._faceid: List[int] = faceid  # FIXME: Why int assigned to list?
        self._static: bool = static

    def __eq__(self, other):
        if isinstance(other, ForwardingInformationBaseEntry):
            return self._name == other._name and self._faceid == other._faceid
        return False

    def __repr__(self):
        static: str = ' static' if self._static else ''
        return f'<ForwardingInformationBaseEntry {self._name} via {self._faceid}{static} at {id(self)}>'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def faceid(self):
        return self._faceid

    @faceid.setter
    def faceid(self, faceid):
        self._faceid = faceid

    @property
    def static(self):
        return self._static

    @static.setter
    def static(self, static):
        self._static = static


class BaseForwardingInformationBase(BaseICNDataStruct):
    """Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

    def __init__(self):
        super().__init__()
        self._container: List[ForwardingInformationBaseEntry] = []
        self._manager: Optional[multiprocessing.Manager] = None

    @abc.abstractmethod
    def add_fib_entry(self, name: Name, fid: List[int], static: bool, is_session: bool = False):
        """Add an Interest to the FIB"""

    @abc.abstractmethod
    def remove_fib_entry(self, name: Name):
        """Remove an entry from the FIB"""

    @abc.abstractmethod
    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry] = None,
                       incoming_faceids: List[int] = None) -> ForwardingInformationBaseEntry:
        """Find an entry in the FIB"""

    @abc.abstractmethod
    def add_faceid_to_entry(self, name, fid):
        """adds a face id to an entry"""

    @abc.abstractmethod
    def clear(self):
        """Remove all non-static entries from the FIB"""

    def __repr__(self):
        headers = ['Name', 'FaceIDs', 'Static']
        data = [[entry.name, entry.faceid, entry.static]
                for entry in self._container]
        return f"Fowarding Information Base:\n{tabulate(data, headers=headers, showindex=True, tablefmt='fancy_grid')}"

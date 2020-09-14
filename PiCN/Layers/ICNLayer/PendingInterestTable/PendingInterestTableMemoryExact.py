"""In-memory Pending Interest Table using exact prefix matching"""

import time

from PiCN.Layers.ICNLayer.PendingInterestTable.BasePendingInterestTable import BasePendingInterestTable, \
     PendingInterestTableEntry
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry
from PiCN.Packets import Interest, Name

from typing import Optional, Tuple, Union, List


class PendingInterstTableMemoryExact(BasePendingInterestTable):
    """In-memory Pending Interest Table using exact prefix matching"""

    def __init__(self, pit_timeout: int = 4, pit_retransmits: int = 3) -> None:
        super().__init__(pit_timeout=pit_timeout, pit_retransmits=pit_retransmits)

    def add_pit_entry(self, name, faceid: Union[int, List[int]], interest: Interest = None, local_app=False, is_session: bool = False):
        for pit_entry in self.container:
            if pit_entry.name == name:
                if faceid in pit_entry.faceids and local_app in pit_entry.local_app:
                    return
                self.container.remove(pit_entry)
                if isinstance(faceid, int):
                    pit_entry.faceids.append(faceid)
                elif isinstance(faceid, list):
                    pit_entry.faceids.extend(fid for fid in faceid if fid not in pit_entry.faceids)
                pit_entry.local_app.append(local_app)
                self.container.append(pit_entry)
                return

        self.container.append(PendingInterestTableEntry(name, faceid, interest, local_app, is_session=is_session))

    def remove_pit_entry(self, name: Name):
        to_remove = []

        for pit_entry in self.container:
            if pit_entry.name == name and f"{self._session_identifier}/" in pit_entry.name.components_to_string():
                self.add_pit_entry(name=Name('/SID') + [pit_entry.name.components[-1]], faceid=pit_entry.faceids, is_session=True)

            if pit_entry.name == name and not pit_entry.is_session:
                print(f"Removing PIT entry: {pit_entry.name}")
                to_remove.append(pit_entry)

        for r in to_remove:
            self.container.remove(r)

        print(self)

    def remove_pit_entry_by_fid(self, faceid: int):
        for pit_entry in self.container:
            if faceid in pit_entry.faceids:
                self.container.remove(pit_entry)

                new_faceids = pit_entry.faceids.remove(faceid)

                new_entry = PendingInterestTableEntry(pit_entry.name, new_faceids, interest=pit_entry.interest,
                                                      local_app=pit_entry.local_app,
                                                      fib_entries_already_used=pit_entry.fib_entries_already_used,
                                                      faces_already_nacked=pit_entry.faces_already_nacked,
                                                      number_of_forwards=pit_entry.number_of_forwards)
                new_entry.faces_already_nacked = pit_entry.faces_already_nacked
                self.container.append(new_entry)

    def find_pit_entry(self, name: Name) -> Optional[PendingInterestTableEntry]:
        for pit_entry in self.container:
            if pit_entry.name == name:
                return pit_entry
        return None

    def update_timestamp(self, pit_entry: PendingInterestTableEntry):
        self.container.remove(pit_entry)
        new_entry = PendingInterestTableEntry(pit_entry.name, pit_entry.faceids, interest=pit_entry.interest,
                                              local_app=pit_entry.local_app,
                                              fib_entries_already_used=pit_entry.fib_entries_already_used,
                                              faces_already_nacked=pit_entry.faces_already_nacked,
                                              number_of_forwards=pit_entry.number_of_forwards)
        new_entry.faces_already_nacked = pit_entry.faces_already_nacked
        self.container.append(new_entry)

    def add_used_fib_entry(self, name: Name, used_fib_entry: ForwardingInformationBaseEntry):  # FIXME: What is a used_fib_entry?
        pit_entry = self.find_pit_entry(name)
        self.container.remove(pit_entry)
        pit_entry.fib_entries_already_used.append(used_fib_entry)
        self.container.append(pit_entry)

    def get_already_used_pit_entries(self, name: Name):
        pit_entry = self.find_pit_entry(name)
        return pit_entry.fib_entries_already_used

    def append(self, entry):
        self.container.append(entry)

    def ageing(self) -> Tuple[List[PendingInterestTableEntry], List[PendingInterestTableEntry]]:
        cur_time = time.time()
        remove = []
        updated = []
        for pit_entry in self.container:
            if pit_entry.timestamp + self._pit_timeout < cur_time and pit_entry.retransmits > self._pit_retransmits and not pit_entry.is_session:
                remove.append(pit_entry)
            elif not pit_entry.is_session:  # FIXME: Eventually we will have to let session die?
                pit_entry.retransmits = pit_entry.retransmits + 1
                updated.append(pit_entry)
            else:
                pass  # This case means there are still PIT entries the process tries to age
        for pit_entry in remove:
            self.remove_pit_entry(pit_entry.name)
        for pit_entry in updated:
            self.remove_pit_entry(pit_entry.name)
            self.container.append(pit_entry)
        return updated, remove

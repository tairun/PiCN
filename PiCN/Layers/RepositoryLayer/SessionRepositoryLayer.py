"""Basic implementation of the repository layer with session support"""

import secrets
import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Interest, Content, Packet, Nack, NackReason, Name
from PiCN.Processes import LayerProcess

from typing import List


class SessionRepositoryLayer(LayerProcess):
    """Basic implementation of the repository layer with session support"""

    def __init__(self, repository: BaseRepository, propagate_interest: bool = False, logger_name="RepoLayer", log_level=255):
        super().__init__(logger_name, log_level)

        self._session_identifier: str = 'session_connector'
        self._pending_sessions: List = []  # TODO: Implement session initiation procedure (handshake).
        self._running_sessions: List = []  # TODO: Implement better data structure to handle sessions. HashMap?
        self._repository: BaseRepository = repository
        self._propagate_interest: bool = propagate_interest

    def _make_session_id(self, bits: int = 16) -> str:
        """
        Creates a cryptographically-secure, URL-safe string
        """
        return secrets.token_urlsafe(bits)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: List):
        pass  # do not expect this to happen, since repository is highest layer

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: List):
        self.logger.info("Got Data from lower")

        if self._repository is None:
            return

        faceid: int = data[0]
        packet: Packet = data[1]

        self.logger.info(f"--> Last component of name: {packet.name.components[-1].decode()}")  # FIXME: Delete when done.

        if isinstance(packet, Interest):  # TODO: Can I check here for connector interest and return session key? Yes!!
            # self.logger.info(packet)  # FIXME: Delete when done.
            if self._session_identifier in packet.name.components_to_string():
                self.logger.info('--> : Session packet detected.')
                # self.logger.info(type(packet.name.components[-1].decode()))  # FIXME: Delete when done.
                if packet.name.components[-1].decode() == self._session_identifier:  # Detect incoming handshake (if session_connector is the last component of interest name)
                    session_id: str = self._make_session_id()
                    self._pending_sessions.append(session_id)
                    c = Content(packet.name, session_id, None)
                    self.logger.info('--> : Request to initiate session. Sending key down.')
                    self.queue_to_lower.put([faceid, c])  # Sending session id as content packet
                    return
                elif packet.name.components[-1].decode() in self._pending_sessions:  # Detect third part of handshake and store session (if session id is last part of interest name)
                    session_id: str = packet.name.components[-1].decode()
                    self._pending_sessions.remove(session_id)
                    self._running_sessions.append(session_id)
                    self.logger.info(f"--> : Session with id {session_id} established.")
                    c = Content(packet.name, None, None)
                    self.logger.info('--> : Sending empty content to stop retransmit.')  # FIXME: Better solution to not trigger retransmits?
                    self.queue_to_lower.put([faceid, c])  # Sending session id as content packet
                else:
                    self.logger.info('--> : Unknown session packet receveid. Dropping and sending nack.')
                    nack = Nack(packet.name, NackReason.NO_CONTENT, interest=packet)
                    to_lower.put([faceid, nack])

            elif self._repository.is_content_available(packet.name):  # Gets content object from content store.
                c = self._repository.get_content(packet.name)
                self.queue_to_lower.put([faceid, c])
                self.logger.info('--> : Found content object, sending down.')
                return
            elif self._propagate_interest is True:  # TODO: What does this do? --> Used for NDN.
                self.queue_to_lower.put([faceid, packet])
                return
            else:
                self.logger.info("No matching data, dropping interest, sending nack.")
                nack = Nack(packet.name, NackReason.NO_CONTENT, interest=packet)
                to_lower.put([faceid, nack])  # FIXME: queue_to_lower or just to lower? Other instances above?
                return
        elif isinstance(packet, Content):  # FIXME: Better use elif here?
            pass
        else:
            pass

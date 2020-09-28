"""Basic implementation of the repository layer with session support"""

import secrets
import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Interest, Content, Packet, Nack, NackReason, Name
from PiCN.Processes import LayerProcess

from typing import List, Union, Dict


class SessionRepositoryLayer(LayerProcess):
    """Basic implementation of the repository layer with session support"""

    def __init__(self, repository: BaseRepository, propagate_interest: bool = False, logger_name="RepoLayer", log_level=255):
        super().__init__(logger_name, log_level)

        self._repository: BaseRepository = repository
        self._propagate_interest: bool = propagate_interest
        self._session_initiator: str = 'session_connector'
        self._session_identifier = 'sid'
        self._pending_sessions: Dict[Name, int] = dict()  # TODO: Implement session initiation procedure (handshake).
        self._running_sessions: Dict[Name, int] = dict()  # TODO: Implement better data structure to handle sessions. HashMap?

    def _broadcast_reconnect(self, sid: str, max_hops: int = 5) -> None:
        pass

    def send_content(self, content: str):
        self.logger.debug(f"--> : Sending content to all sessions")
        self.logger.debug(self._running_sessions)
        for sid, faceid in self._running_sessions.items():
            c = Content(sid, content, None)
            self.logger.info(f"--> : Sending content ({content}) to session ({sid}) on face id {faceid}")
            self.queue_to_lower.put([faceid, c])

    def _make_session_id(self, bits: int = 16) -> str:
        """
        Creates a unique id for an ICN session
        :param bits: Length of id to create
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

        if isinstance(packet, Interest):
            if self._session_initiator in packet.name.components_to_string():
                self.logger.info('--> : Session packet detected.')
                if packet.name.components[-1].decode() == self._session_initiator:  # Detect incoming handshake (if session_connector is the last component of interest name)
                    session_id: str = self._make_session_id()
                    self._pending_sessions[Name(f"/{self._session_identifier}") + session_id] = faceid
                    c = Content(packet.name, session_id, None)
                    self.logger.info('--> : Request to initiate session. Sending key down.')
                    self.queue_to_lower.put([faceid, c])  # Sending session id as content packet
                    return
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
        elif isinstance(packet, Content):  # FIXME: Better use elif here? We need to handle incoming content for sessions!
            self.logger.info(f"--> : Got content in repository ({packet.content})")
            if self._session_identifier in packet.name.to_string() and packet.name in self._pending_sessions:  # Detect third part of handshake and store session (if session id is last part of interest name)
                session_id: str = packet.name.components[-1].decode()
                self._running_sessions[Name(f"/{self._session_identifier}") + session_id] = faceid
                del self._pending_sessions[Name(f"/{self._session_identifier}") + session_id]
                self.logger.info(f"--> : Session with id {session_id} established.")
                self.logger.info(f"--> : Running sessions for repo: {self._running_sessions}")
            return
        else:
            self.logger('No known packet type.')
            pass

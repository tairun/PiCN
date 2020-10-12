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
        self._pending_sessions: Dict[Name, int] = dict()
        self._running_sessions: Dict[Name, int] = dict()

    def reconnect(self, initial_faces: List[int], sid: Name = None, max_hops: int = 5) -> None:
        """Broadcasts a reconnect interest to all connected faceids to re-establish the session when the repository has
        moved to another forwarder.
        :param initial_faces A list of faces has to be provided, since the repolayer does not know what the new faceids are after moving to a new forwarder.
        :param sid Only reconnect a specific session. If None is provided, all sessions are going to be reconnected.
        :param max_hops Specifies how many forwarders should be contacted to restore the session
        """
        self.logger.info(f"--> : Reconnecting session(s) from repository.")
        self.logger.debug(f"--> : Running sessions are: {self.running_sessions}")
        to_reconnect = [sid] if sid else [k for k, _ in self.running_sessions]

        for session in to_reconnect:
            for fid in initial_faces:
                reconnect_address = Name(f"/{self._session_identifier}" + session + 'reconnect' + max_hops)
                self.logger.debug(f"--> : This is the reconnect address: {reconnect_address}")
                reconnect_interest = Interest(name=reconnect_address, wire_format=None)
                self.queue_to_lower.put([fid, reconnect_interest])

        return None

    def send_content(self, content: str = 'This is just a test! ;-)') -> None:
        """Sends content from this repository to all fetch tools if a session was established.
        :param content Text to send as content
        :return None
        """
        self.logger.info(f"--> : Sending content to all sessions")
        self.logger.debug(f"--> : Running sessions are: {self._running_sessions}")

        for sid, faceid in self._running_sessions.items():
            c = Content(sid, content, None)
            self.logger.info(f"--> : Sending content ({content}) to session ({sid}) on face id {faceid}")
            self.queue_to_lower.put([faceid, c])

        return None

    def _make_session_id(self, bits: int = 8) -> str:
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
                if packet.name.components[-1].decode() == self._session_initiator:
                    session_id: str = self._make_session_id()
                    self._pending_sessions[Name(f"/{self._session_identifier}") + session_id] = faceid
                    c = Content(packet.name, session_id, None)
                    self.logger.info('--> : Request to initiate session. Sending key down.')
                    self.queue_to_lower.put([faceid, c])
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
            if self._session_identifier in packet.name.to_string() and packet.name in self._pending_sessions:
                session_id: str = packet.name.components[-1].decode()
                self._running_sessions[Name(f"/{self._session_identifier}") + session_id] = faceid
                del self._pending_sessions[Name(f"/{self._session_identifier}") + session_id]
                self.logger.info(f"--> : Session with id {session_id} established.")
                self.logger.debug(f"--> : Running sessions for repo: {self._running_sessions}")
            elif packet.content == 'ping':
                self.logger.debug(f"Answering ping packet for session {packet.name} on faceid {faceid}")
                content = Content(packet.name, 'pong')
                to_lower.put([faceid, content])
            elif packet.content == 'terminate':
                self.logger.debug(f"Terminating session {packet.name}")
                del self._pending_sessions[packet.name]
                del self._running_sessions[packet.name]
            return
        else:
            self.logger.info('--> : No known packet type.')
            pass

    @property
    def running_sessions(self) -> Dict[Name, int]:
        return self._running_sessions

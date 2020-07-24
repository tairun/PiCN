"""Basic implementation of the repository layer with session support"""

import secrets
import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Interest, Content, Packet, Nack, NackReason, Name
from PiCN.Processes import LayerProcess


class SessionRepositoryLayer(LayerProcess):
    """Basic implementation of the repository layer with session support"""

    def __init__(self, repository: BaseRepository, propagate_interest: bool = False, logger_name="RepoLayer", log_level=255):
        super().__init__(logger_name, log_level)

        self._connector_identifier = "session_connector"
        self._repository: BaseRepository = repository
        self._propagate_interest: bool = propagate_interest

    def make_session_key(self) -> str:
        """
        Creates a cryptographically-secure, URL-safe string
        """
        return secrets.token_urlsafe(16)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: Packet):
        pass  # do not expect this to happen, since repository is highest layer

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data: Packet):
        self.logger.info("Got Data from lower")

        if self._repository is None:
            return

        faceid = data[0]
        packet = data[1]

        if isinstance(packet, Interest):  # TODO: Can I check here for connector interest and return session key?
            if packet.name == self._connector_identifier:
                c = Content(Name(self._connector_identifier), SessionRepositoryLayer.make_session_key(self), None)
                self.queue_to_lower.put([faceid, c])
                self.logger.info("Request to initiate session. Sending key down")
                return
            elif self._repository.is_content_available(packet.name):
                c = self._repository.get_content(packet.name)
                self.queue_to_lower.put([faceid, c])
                self.logger.info("Found content object, sending down")
                return
            elif self._propagate_interest is True:  # TODO: What does this do? --> Used for NDN.
                self.queue_to_lower.put([faceid, packet])
                return
            else:
                self.logger.info("No matching data, dropping interest, sending nack")
                nack = Nack(packet.name, NackReason.NO_CONTENT, interest=packet)
                to_lower.put([faceid, nack])
                return

        if isinstance(packet, Content):  # FIXME: Better use elif here?
            pass

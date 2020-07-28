"""Fetch Tool for PiCN"""

from typing import Optional
from PiCN.Packets import Packet
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack


class FetchSessions(Fetch):
    """Fetch Tool for PiCN"""

    def __init__(self, ip: str, port: int, log_level=255, encoder: BasicEncoder = None, autoconfig: bool = False,
                 interfaces=None, session_key: Optional[str] = None):
        super().__init__(ip, port, log_level, encoder, autoconfig, interfaces)

        self.session_key: str = session_key  # TODO: Extend this to work with multiple repos (use dict or something).
        self.has_session: bool = True if session_key is not None else False

    def fetch_data_session(self, name: Name, timeout=4.0) -> Optional[str]:
        """Fetch data from the server via a session
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        if not self.has_session:
            return "Initialize session with repository first. Send interest to session_connector content object."
        else:
            interest: Interest = Interest(name)  # create interest

            if self.autoconfig:
                self.lstack.queue_from_higher.put([None, interest])
            else:
                self.lstack.queue_from_higher.put([self.fid, interest])

            if timeout == 0:
                packet = self.lstack.queue_to_higher.get()[1]
            else:
                packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]

            if isinstance(packet, Content):
                return packet.content
            if isinstance(packet, Nack):
                return "Received Nack: " + str(packet.reason.value)

            return None

    def handle_session(self, packet: Packet):
        """
        :param packet Packet with session handshake
        """
        pass

    def fetch_data(self, name: Name, timeout=4.0) -> Optional[str]:
        """Fetch data from the server
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        interest: Interest = Interest(name)  # create interest

        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])

        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]

        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)

        return None

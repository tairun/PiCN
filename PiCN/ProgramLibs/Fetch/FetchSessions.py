"""Fetch Tool for PiCN supporting sessions"""

from PiCN.Packets import Packet
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack

from typing import Optional, Dict


class FetchSessions(Fetch):
    """Fetch Tool for PiCN supporting sessions"""

    def __init__(self, ip: Name, port: Optional[int], log_level=255, encoder: BasicEncoder = None, autoconfig: bool = False,
                 interfaces=None, session_keys: Optional[Dict] = None):
        super().__init__(ip, port, log_level, encoder, autoconfig, interfaces)
        self.ip = ip
        self._session_keys: Dict = dict() if session_keys is None else session_keys  # TODO: Extend this to work with multiple repos (use dict or something).
        self._has_session: bool = True if session_keys is not None else False
        self._session_initiator = 'session_connector'
        self._session_identifier = 'sid'

    def fetch_data_session(self, name: Name, timeout=4.0) -> Optional[str]:  # TODO: Combine method with other fetch method and use bool to ignore session key.
        """Fetch data from the server via a session
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        if not self._has_session:
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

    def handle_new_session(self, name: Name, packet: Packet) -> None:
        """
        :param name Name to be fetched
        :param packet Packet with session handshake
        """
        if isinstance(packet, Content):
            session_confirmation: Content = Content(name + Name(f"{self._session_identifier}/{packet.content}"))

            # Send session ACK
            if self.autoconfig:
                self.lstack.queue_from_higher.put([None, session_confirmation])
            else:
                self.lstack.queue_from_higher.put([self.fid, session_confirmation])

            self._session_keys[packet.name] = packet.content
            self._has_session = True

    def end_session(self, name: Name) -> None:
        """
        param name Name to terminate session with
        """
        # TODO: Implement method. Send interest in the form of Name(/test/t2/session/<id>/remove). Wait for ACK.
        pass

    def fetch_data(self, name: Name, timeout=4.0) -> Optional[str]:
        """Fetch data from the server
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        interest: Interest = Interest(name)  # Create interest

        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])

        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]

        if isinstance(packet, Content):
            if self._session_identifier in packet.name.components_to_string():  # Check for second message of handshake
                self.handle_new_session(name, packet)

            return packet.content
        elif isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)

        return None

    def send_content(self, name: Name, content: str):
        c = Content(name, content, None)
        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, c])
        else:
            self.lstack.queue_from_higher.put([self.fid, c])

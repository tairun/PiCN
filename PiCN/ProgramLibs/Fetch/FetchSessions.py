"""Fetch Tool for PiCN supporting sessions"""

from PiCN.Packets import Packet
from PiCN.Logger import Logger
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack

import time
from tabulate import tabulate
from multiprocessing import Process, Queue, Lock, Manager

from typing import Optional, Dict, List, Tuple, Union


class FetchSessions(Fetch):
    """Fetch Tool for PiCN supporting sessions"""

    def __init__(self, ip: str, port: Optional[int], log_level=255, encoder: BasicEncoder = None,
                 autoconfig: bool = False, interfaces=None, session_keys: Optional[Dict] = None, name: str = None,
                 polling_interval: float = 1.0):
        super().__init__(ip, port, log_level, encoder, autoconfig, interfaces, name)
        self.ip = ip
        self._logger = Logger("FetchSession", log_level)
        self._pending_sessions: List[Name] = []
        self._running_sessions: Dict[Name:Name] = dict() if session_keys is None else session_keys
        self._has_session: bool = True if session_keys is not None else False
        self._session_initiator = 'session_connector'
        self._session_identifier = 'sid'
        self._polling_interval = polling_interval
        self._manager = Manager()
        self._mutex = self._manager.Lock()

        self.receive_process = Process(target=self._receive_session, args=(self.lstack.queue_to_higher,
                                                                           self._polling_interval,
                                                                           self._mutex,))
        self.receive_process.start()

    def handle_session(self, name: Name, packet: Packet) -> None:
        """
        :param name Name to be fetched
        :param packet Packet with session handshake
        """
        if isinstance(packet, Content):
            target_name: Name = Name(f"/{self._session_identifier}/{packet.content}")
            session_confirmation: Content = Content(target_name, packet.content, None)

            self.send_content(content=session_confirmation)

            self._running_sessions[name] = target_name
            self._pending_sessions.remove(name)
            self._has_session = True

        return None

    def get_session_name(self, name: Name) -> Optional[Name]:
        """Fetches the session name from the session store. Returns None otherwise
        param name Name of repository to get session key for
        """
        if name in self._running_sessions:
            return self._running_sessions[name]
        else:
            return None

    def end_session(self, name: Name) -> None:
        """Terminates a session by deleting the associated id from the session store.
        param name Name to terminate session with
        """
        # TODO: Implement method. Send interest in the form of Name(/test/t2/session/<id>/remove). Wait for ACK.
        del self._running_sessions[name]
        self._pending_sessions.remove(name)
        self._has_session = False if not self._running_sessions else True

        return None

    def _receive_session(self, queue: Queue, polling_interval: float, mutex: Lock):
        while True:
            self._logger.debug(f"--> : Waiting for mutex in loop ...")
            mutex.acquire(blocking=True)
            packet = None

            if not queue.empty():
                packet = queue.get()[1]

            mutex.release()

            if isinstance(packet, Content):
                print(f"--> : Receive loop got: {packet.content}")
            elif isinstance(packet, Nack):
                self._logger.debug(f"--> One time receive got Nack: {packet.reason}")
            elif packet is None:
                self._logger.debug(f"--> : No packet in queue")
            else:
                self._logger.debug(f"--> : Whoops, we just cleared a non content object from the queue! {packet}")

            time.sleep(polling_interval)

    def fetch_data(self, name: Name, timeout: float = 4.0, use_session: bool = True) -> Optional[str]:
        """Fetch data from the server
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        :param use_session Set to False if sessions shouldn't be used even if they are available.
        """
        if name in self._running_sessions and use_session:  # Create interest with session
            interest: Interest = Interest(self._running_sessions.get(name))
        else:  # Create normal interest
            interest: Interest = Interest(name)

        self._mutex.acquire(blocking=True)
        self.send_interest(interest)
        packet = self.receive_packet(timeout)
        self._mutex.release()

        if self._session_initiator in interest.name.to_string():  # Check if we need to handle session initiation
            new_name = Name(name.components[:-1])
            self._pending_sessions.append(new_name)
            self.handle_session(new_name, packet)

        if isinstance(packet, Content):
            self._logger.debug(f"--> One time receive got content: {packet.content}")
            return packet.content
        elif isinstance(packet, Nack):
            self._logger.debug(f"--> One time receive got nack: {packet.reason}")
            return f"Received Nack: {str(packet.reason.value)}"

        return None

    def send_interest(self, interest: Interest) -> None:
        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])

        return None

    def receive_packet(self, timeout: float) -> Packet:
        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]

        return packet

    def send_content(self, content: Union[Content, Tuple[Name, str]]) -> None:
        if isinstance(content, Content):
            c = content
        else:
            c = Content(content[0], content[1], None)

        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, c])
        else:
            self.lstack.queue_from_higher.put([self.fid, c])

        return None

    def stop_fetch(self):
        """Close everything"""
        self.receive_process.terminate()
        self.lstack.stop_all()
        self.lstack.close_all()

    def __repr__(self):
        headers = ['Target', 'Session ID']
        data = [[k, v] for k, v in self._running_sessions.items()]
        return f"Running sessions for <<{self.name}>>:\n{tabulate(data, headers=headers, showindex=True, tablefmt='fancy_grid')}"

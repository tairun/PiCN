"""Simulation environment to test long-term sessions.
This is part of the bachelors thesis by Luc Kury@2020."""

from PiCN.ProgramLibs.Fetch import Fetch, FetchSessions
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository, ICNDataRepositorySession
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Content, Interest, Name

import time
import unittest


class ICNSessionSimulation(unittest.TestCase):
    """Simulate a Scenario where timeout prevention is required"""

    def setUp(self):
        self.simulation_bus = SimulationBus(log_level=0)  # Use BasicStringEncoder
        self.icn_repo0 = ICNDataRepository(port=0, prefix=Name('/test/t1'), foldername=None,
                                           interfaces=[self.simulation_bus.add_interface('repo0')],
                                           log_level=255)  # Initialize repository 0
        self.icn_repo1 = ICNDataRepositorySession(port=0, prefix=Name('/test/t2'), foldername=None,
                                                  interfaces=[self.simulation_bus.add_interface('repo1')],
                                                  log_level=0)  # Initialize repository 1 (this one has sessions)

        self.icn_forwarder0 = ICNForwarder(port=0, log_level=255,
                                           interfaces=[self.simulation_bus.add_interface('fw0')])  # Initialize forwarder 0
        self.icn_forwarder1 = ICNForwarder(port=0, log_level=255,
                                           interfaces=[self.simulation_bus.add_interface('fw1')])  # Initialize forwarder 1

        self.mgmt_client0 = MgmtClient(self.icn_repo0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 0
        self.mgmt_client1 = MgmtClient(self.icn_repo1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 1
        self.mgmt_client2 = MgmtClient(self.icn_forwarder0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 0
        self.mgmt_client3 = MgmtClient(self.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 1

        # This is unintuitive. Why does the fetch tool add its own face, but the other components don't?
        self.fetch0 = Fetch('fw0', None, log_level=255,
                            interfaces=[self.simulation_bus.add_interface('fetcht0')])  # Initialize a client (fetch tool)
        self.fetch1 = FetchSessions('fw0', None, log_level=255, interfaces=[self.simulation_bus.add_interface('fetcht1')])

        self.icn_repo0.start_repo()
        self.icn_repo1.start_repo()
        self.icn_forwarder0.start_forwarder()
        self.icn_forwarder1.start_forwarder()
        self.simulation_bus.start_process()

        time.sleep(1)  # Be safe and wait for all processes to start

        self.mgmt_client2.add_face('repo0', None, 0)  # Add new interface to forwarder 0, index has to be 0.
        self.mgmt_client2.add_face('fw1', None, 0)  # # Add new interface to forwarder 0, index has to be 0.
        self.mgmt_client2.add_forwarding_rule(Name('/test/t1'), [0])  # Add a forward-rule this prefix to interface with index 0.
        self.mgmt_client2.add_forwarding_rule(Name('/test/t2'), [1])  # Add a forward-rule this prefix to interface with index 1.
        self.mgmt_client3.add_face('repo1', None, 0)  # Add new interface to forwarder 1, index has to be 0.
        self.mgmt_client3.add_forwarding_rule(Name('/test/t2'), [0])  # Add a forward-rule this prefix to interface with index 0.
        # Repositories do not need a forwarding rule or an interface. All done in constructor.

        self.test_content = 'This is just a test for repo0.'
        self.icn_repo0.repo.add_content(Name('/test/t1/content_object'),
                                        self.test_content)  # TODO: Create add_new_content command for DataRepository in ManagementClient

        print(self.icn_forwarder0.icnlayer.fib)
        print(self.icn_forwarder1.icnlayer.fib)

    def tearDown(self):
        time.sleep(1)  # Be safe and wait for all messages to trickle in before shutting down everything

        self.icn_forwarder0.stop_forwarder()
        self.icn_forwarder1.stop_forwarder()
        self.fetch0.stop_fetch()
        self.fetch1.stop_fetch()
        self.simulation_bus.stop_process()
        self.mgmt_client0.shutdown()
        self.mgmt_client1.shutdown()
        self.mgmt_client2.shutdown()
        self.mgmt_client3.shutdown()

    def test_simple_interest(self):
        interest = Name('/test/t1/content_object')  # Test routing, no new features.
        res = self.fetch0.fetch_data(interest, timeout=20)
        print(f"Return value: {res}")
        self.assertEqual(self.test_content, res, 'The content matches.')

    def test_simple_session_initiation(self):
        interest = Name("/test/t2/session_connector")  # Test session connection string. This should return 16bits
        res = self.fetch1.fetch_data(interest, timeout=20)
        print(f"Return value : {res}")
        self.assertEqual(self.icn_repo1.repolayer._pending_sessions[0], self.fetch1._session_keys[0], 'The session keys match.')

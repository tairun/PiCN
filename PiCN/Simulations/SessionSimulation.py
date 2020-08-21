"""Simulation environment to test long-term sessions.
This is part of the bachelors thesis by Luc Kury@2020."""

from PiCN.ProgramLibs.Fetch import Fetch, FetchSessions
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository, ICNDataRepositorySession
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Content, Interest, Name

import time
import types
import tempfile


def setup(dummy):
    pass


def teardown(dummy):
    pass


if __name__ == "__main__":
    # dummy = types.SimpleNamespace()
    # temp = tempfile.gettempdir()
    # print(temp)
    # setup(dummy)
    # teardown(dummy)

    simulation_bus = SimulationBus(log_level=255)  # Use BasicStringEncoder
    icn_repo0 = ICNDataRepository(port=0, prefix=Name("/test/t1"), foldername=None, interfaces=[simulation_bus.add_interface("repo0")], log_level=255)  # Initialize repository 0
    icn_repo1 = ICNDataRepositorySession(port=0, prefix=Name("/test/t2"), foldername=None, interfaces=[simulation_bus.add_interface("repo1")], log_level=255)  # Initialize repository 1 (this one has sessions)

    icn_forwarder0 = ICNForwarder(port=0, log_level=255, interfaces=[simulation_bus.add_interface("fw0")])  # Initialize forwarder 0
    icn_forwarder1 = ICNForwarder(port=0, log_level=255, interfaces=[simulation_bus.add_interface("fw1")])  # Initialize forwarder 1

    mgmt_client0 = MgmtClient(icn_repo0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 0
    mgmt_client1 = MgmtClient(icn_repo1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 1
    mgmt_client2 = MgmtClient(icn_forwarder0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 0
    mgmt_client3 = MgmtClient(icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 1

    # This is unintuitive. Why does the fetch tool add its own face, but the other components don't?
    fetch0 = Fetch("fw0", None, log_level=255, interfaces=[simulation_bus.add_interface("fetcht0")])  # Initialize a client (fetch tool)
    fetch1 = FetchSessions("fw0", None, log_level=255, interfaces=[simulation_bus.add_interface("fetcht1")])

    icn_repo0.start_repo()
    icn_repo1.start_repo()
    icn_forwarder0.start_forwarder()
    icn_forwarder1.start_forwarder()
    simulation_bus.start_process()

    time.sleep(1)

    mgmt_client2.add_face("repo0", None, 0)  # Add new interface to forwarder 0, index has to be 0.
    mgmt_client2.add_face("fw1", None, 0)  # # Add new interface to forwarder 0, index has to be 0.
    mgmt_client2.add_forwarding_rule(Name("/test/t1"), [0])  # Add a forward-rule this prefix to interface with index 0.
    mgmt_client2.add_forwarding_rule(Name("/test/t2"), [1])  # Add a forward-rule this prefix to interface with index 1.
    mgmt_client3.add_face("repo1", None, 0)  # Add new interface to forwarder 1, index has to be 0.
    mgmt_client3.add_forwarding_rule(Name("/test/t2"), [0])  # Add a forward-rule this prefix to interface with index 0.
    # Repositories do not need a forwarding rule or a interface. All done in constructor.

    icn_repo0.repo.add_content(Name("/test/t1/content_object"), "This is just a test for repo0.")  # TODO: Create add_new_content command for DataRepository in ManagementClient

    interest0 = Name("/test/t1/content_object")  # Test routing, no new features.
    interest1 = Name("/test/t2/session_connector")  # Test session connection string. This should return 16bits

    res0 = fetch0.fetch_data(interest0, timeout=20)
    print(f"Return value of fetch0 is: {res0}")
    time.sleep(1)
    res1 = fetch1.fetch_data(interest1, timeout=20)
    print(f"Return value of fetch1 is: {res1}")
    print(f"All session keys: {fetch1.session_keys}")

    icn_forwarder0.stop_forwarder()
    icn_forwarder1.stop_forwarder()
    fetch0.stop_fetch()
    fetch1.stop_fetch()
    simulation_bus.stop_process()
    mgmt_client0.shutdown()
    mgmt_client1.shutdown()
    mgmt_client2.shutdown()
    mgmt_client3.shutdown()

    exit(0)
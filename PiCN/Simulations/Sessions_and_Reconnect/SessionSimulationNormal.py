"""Simulation environment to test long-term sessions.
This is part of the bachelors thesis by Luc Kury@2020."""

from PiCN.ProgramLibs.Fetch import Fetch, FetchSessions
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository, ICNDataRepositorySession
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name

import time

if __name__ == "__main__":
    ## Loglevel 0 = everything, Loglevel 255 = nothing
    simulation_bus = SimulationBus(log_level=0)  # Use BasicStringEncoder
    repo0 = ICNDataRepository(port=0, prefix=Name('/test/t1'), foldername=None, interfaces=[simulation_bus.add_interface('repo0')], log_level=255)  # Initialize repository 0
    repo1 = ICNDataRepositorySession(port=0, prefix=Name('/test/t2'), foldername=None, interfaces=[simulation_bus.add_interface('repo1')], log_level=0)  # Initialize repository 1 (this one has sessions)

    fw0 = ICNForwarder(port=0, log_level=255, interfaces=[simulation_bus.add_interface('fw0')], node_name='forwarder0')  # Initialize forwarder 0
    fw1 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw1')], node_name='forwarder1')  # Initialize forwarder 1

    mgmt_repo0 = MgmtClient(repo0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 0
    mgmt_repo1 = MgmtClient(repo1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 1
    mgmt_fw0 = MgmtClient(fw0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 0
    mgmt_fw1 = MgmtClient(fw1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 1

    # This is unintuitive. Why does the fetch tool add its own face, but the other components don't?
    fetch0 = Fetch('fw0', None, log_level=255, interfaces=[simulation_bus.add_interface('fetcht0')], name='fetch0')
    fetch1 = FetchSessions('fw1', None, log_level=0, interfaces=[simulation_bus.add_interface('fetcht1')], name='fetch1')

    repo0.start_repo()
    repo1.start_repo()
    fw0.start_forwarder()
    fw1.start_forwarder()
    simulation_bus.start_process()

    # time.sleep(1)  # Be safe and wait for all processes to start

    mgmt_fw0.add_face('repo0', None, 0)  # Add new interface to forwarder 0, index has to be 0.
    mgmt_fw0.add_face('fw1', None, 0)  # Add new interface to forwarder 0, index has to be 0.
    mgmt_fw0.add_forwarding_rule(Name('/test/t1'), [0])  # Add a forward-rule this prefix to interface with index 0.
    mgmt_fw0.add_forwarding_rule(Name('/test/t2'), [1])  # Add a forward-rule this prefix to interface with index 1.
    mgmt_fw1.add_face('repo1', None, 0)  # Add new interface to forwarder 1, index has to be 0.
    mgmt_fw1.add_forwarding_rule(Name('/test/t2'), [0])  # Add a forward-rule this prefix to interface with index 0.
    # Repositories do not need a forwarding rule or an interface. All done in constructor.

    repo0.repo.add_content(Name('/test/t1/content_object'), 'This is just a test for repo0.')  # TODO: Create add_new_content command for DataRepository in ManagementClient

    print(fw0.icnlayer.fib)
    print(fw1.icnlayer.fib)

    interest0 = Name('/test/t1/content_object')  # Test routing, no new features.
    interest1 = Name('/test/t2/session_connector')  # Test session connection string. This should return 16bits

    # res0 = fetch0.fetch_data(interest0, timeout=20)
    # print(icn_forwarder0.icnlayer.pit)
    # print(f"Return value of fetch0 is: {res0}")

    # time.sleep(1)

    # Test session creation. res1 should be a session id
    res1 = fetch1.fetch_data(interest1, timeout=20)

    time.sleep(5)

    # fetch 1 and the FIB table should contain active sessions
    print(fetch1)
    print(fw1.icnlayer.fib)

    # Send content from fetch to repo over session. The repo will print out the content on the logger
    fetch1.send_content((fetch1.get_session_name(Name('/test/t2')), 'Hello, is this repo1?'))
    # Send content from repo over session. The receive loop will print out the content
    repo1.repolayer.send_content(content='Whatever I want, whenever I want it.')

    # Test reconnecting sessions after repository has moved to another forwarder
    faces = repo1.linklayer.faceidtable.get_faceids()  # This is a little cheat, in the future we want to get the connected faceids from the repo itself.
    repo1.repolayer.reconnect(initial_faces=faces, sid=None, max_hops=2)

    # -------------------
    # Stop the simulation
    time.sleep(1)  # Be safe and wait for all messages to trickle in before shutting down everything

    fw0.stop_forwarder()
    fw1.stop_forwarder()
    fetch0.stop_fetch()
    fetch1.stop_fetch()
    simulation_bus.stop_process()
    mgmt_repo0.shutdown()
    mgmt_repo1.shutdown()
    mgmt_fw0.shutdown()
    mgmt_fw1.shutdown()

    exit(0)

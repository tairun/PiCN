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
    simulation_bus = SimulationBus(log_level=0)  # Use BasicStringEncoder
    repo0 = ICNDataRepositorySession(port=0, prefix=Name('/unibas/sim1'), foldername=None, interfaces=[simulation_bus.add_interface('repo0')], log_level=0)

    fw0 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw0')], node_name='forwarder0')

    mgmt_repo0 = MgmtClient(repo0.mgmt.mgmt_sock.getsockname()[1])
    mgmt_fw0 = MgmtClient(fw0.mgmt.mgmt_sock.getsockname()[1])

    fetch0 = FetchSessions('fw0', None, log_level=0, interfaces=[simulation_bus.add_interface('fetcht0')], name='fetch0')

    repo0.start_repo()
    fw0.start_forwarder()
    simulation_bus.start_process()

    mgmt_fw0.add_face('repo0', None, 0)
    mgmt_fw0.add_face('fw0', None, 0)
    mgmt_fw0.add_forwarding_rule(Name('/unibas/sim1'), [0])

    content: str = 'Enjoy the awesome trailer for this incredible ICN feature.'
    repo0.repo.add_content(Name('/unibas/sim1/trailer.mp4'), content)

    print(fw0.icnlayer.fib)

    simple_interest = Name('/unibas/sim1/trailer.mp4')
    session_interest = Name('/unibas/sim1/session_connector')

    simple_response = fetch0.fetch_data(simple_interest, timeout=20)
    assert simple_response == content, f"The response should be: '{content}'. Got: '{simple_response}' instead."

    session_response = fetch0.fetch_data(session_interest, timeout=20)
    assert len(session_response) == 11, f"The response should be of length 11. Got length {len(session_response)} instead."

    # Send content from fetch to repo over session. The repo will print out the content on the logger
    fetch0.send_content((fetch0.get_session_name(Name('/unibas/sim1')), 'Hello, please store my thesis. Thank you.'))
    # Send content from repo over session. The receive loop will print out the content
    repo0.repolayer.send_content(content='Test. Test. Test. 1-2-3')

    # -------------------
    # Stop the simulation
    time.sleep(1)  # Be safe and wait for all messages to trickle in before shutting down everything

    fw0.stop_forwarder()
    fetch0.stop_fetch()
    simulation_bus.stop_process()
    mgmt_repo0.shutdown()
    mgmt_fw0.shutdown()

    exit(0)

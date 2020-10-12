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
    fetch0 = FetchSessions('fw0', None, log_level=0, interfaces=[simulation_bus.add_interface('fetcht0')], name='fetch0')
    repo0 = ICNDataRepositorySession(port=0, prefix=Name('/unibas/sim1'), foldername=None, interfaces=[simulation_bus.add_interface('repo0')], log_level=0)

    fw0 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw0')], node_name='forwarder0')
    fw1 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw1')], node_name='forwarder1')
    fw2 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw2')], node_name='forwarder2')
    fw3 = ICNForwarder(port=0, log_level=0, interfaces=[simulation_bus.add_interface('fw3')], node_name='forwarder3')

    mgmt_repo0 = MgmtClient(repo0.mgmt.mgmt_sock.getsockname()[1])
    mgmt_fw0 = MgmtClient(fw0.mgmt.mgmt_sock.getsockname()[1])
    mgmt_fw1 = MgmtClient(fw1.mgmt.mgmt_sock.getsockname()[1])
    mgmt_fw2 = MgmtClient(fw2.mgmt.mgmt_sock.getsockname()[1])
    mgmt_fw3 = MgmtClient(fw3.mgmt.mgmt_sock.getsockname()[1])

    repo0.start_repo()
    fw0.start_forwarder()
    fw1.start_forwarder()
    fw2.start_forwarder()
    fw3.start_forwarder()

    simulation_bus.start_process()

    mgmt_fw0.add_face('fw3', None, 0)
    mgmt_fw0.add_forwarding_rule(Name('/unibas/sim1'), [0])
    mgmt_fw2.add_forwarding_rule(Name('/unibas/sim1'), [0])

    mgmt_fw0.add_face('fw0', None, 0)

    content: str = 'Enjoy the awesome trailer for this incredible ICN feature.'
    repo0.repo.add_content(Name('/unibas/sim1/trailer.mp4'), content)

    session_interest = Name('/unibas/sim1/session_connector')
    session_response = fetch0.fetch_data(session_interest, timeout=20)

    # -------------------
    # Stop the simulation
    time.sleep(1)  # Be safe and wait for all messages to trickle in before shutting down everything

    fw0.stop_forwarder()
    fetch0.stop_fetch()
    simulation_bus.stop_process()
    mgmt_repo0.shutdown()
    mgmt_fw0.shutdown()

    exit(0)

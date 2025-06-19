import math
import sys
from pathlib import Path

import pytest

# Allow importing the VERSION_3 package from the repository root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from VERSION_3.launcher.channel import Channel
from VERSION_3.launcher.simulator import Simulator
from VERSION_3.launcher.node import Node
from VERSION_3.launcher.gateway import Gateway
from VERSION_3.launcher.server import NetworkServer
from VERSION_3.launcher.lorawan import (
    LinkADRAns,
    LinkCheckReq,
    LinkCheckAns,
    DeviceTimeReq,
)


def test_channel_compute_rssi_and_airtime():
    ch = Channel(shadowing_std=0)
    rssi, snr = ch.compute_rssi(14.0, 100.0)
    expected_rssi = 14.0 - ch.path_loss(100.0) - ch.cable_loss_dB
    expected_snr = expected_rssi - ch.noise_floor_dBm()
    assert rssi == pytest.approx(expected_rssi, rel=1e-6)
    assert snr == pytest.approx(expected_snr, rel=1e-6)

    at = ch.airtime(sf=7, payload_size=20)
    rs = ch.bandwidth / (2 ** 7)
    ts = 1.0 / rs
    de = 0
    cr_denom = ch.coding_rate + 4
    numerator = 8 * 20 - 4 * 7 + 28 + 16 - 20 * 0
    denominator = 4 * (7 - 2 * de)
    n_payload = max(math.ceil(numerator / denominator), 0) * cr_denom + 8
    expected_at = (ch.preamble_symbols + 4.25) * ts + n_payload * ts
    assert at == pytest.approx(expected_at, rel=1e-6)


def _make_sim(num_nodes: int, same_start: bool) -> Simulator:
    ch = Channel(shadowing_std=0)
    sim = Simulator(
        num_nodes=num_nodes,
        num_gateways=1,
        area_size=10.0,
        transmission_mode="Periodic",
        packet_interval=10.0,
        packets_to_send=num_nodes,
        mobility=False,
        duty_cycle=None,
        channels=[ch],
        fixed_sf=7,
        fixed_tx_power=14.0,
    )
    gw = sim.gateways[0]
    for n in sim.nodes:
        n.x = gw.x
        n.y = gw.y
    sim.event_queue.clear()
    sim.event_id_counter = 0
    if same_start:
        for node in sim.nodes:
            sim.schedule_event(node, 0.0)
    else:
        for idx, node in enumerate(sim.nodes):
            sim.schedule_event(node, idx * 1.0)
    return sim


def test_simulator_step_success():
    sim = _make_sim(num_nodes=1, same_start=False)
    while sim.step():
        pass
    node = sim.nodes[0]
    assert sim.packets_delivered == 1
    assert sim.network_server.packets_received == 1
    assert node.packets_success == 1


def test_simulator_step_collision():
    sim = _make_sim(num_nodes=2, same_start=True)
    while sim.step():
        pass
    assert sim.packets_delivered == 0
    assert sim.packets_lost_collision == 2
    for node in sim.nodes:
        assert node.packets_collision == 1


def test_lorawan_frame_handling():
    node = Node(1, 0.0, 0.0, 7, 14.0, channel=Channel())
    up = node.prepare_uplink(b"ping", confirmed=True)
    assert up.confirmed
    assert node.fcnt_up == 1
    assert node.awaiting_ack is True

    gw = Gateway(1, 0.0, 0.0)
    server = NetworkServer()
    server.gateways = [gw]
    server.nodes = [node]
    server.send_downlink(node, b"", confirmed=True, adr_command=(9, 5.0))

    down = gw.pop_downlink(node.id)
    assert down is not None
    node.handle_downlink(down)
    assert node.sf == 9
    assert node.tx_power == 5.0
    assert node.pending_mac_cmd == LinkADRAns().to_bytes()
    assert node.awaiting_ack is False

    up2 = node.prepare_uplink(b"data")
    assert up2.payload.startswith(LinkADRAns().to_bytes())
    assert node.pending_mac_cmd is None


def test_downlink_ack_bit_and_mac_commands():
    node = Node(2, 0.0, 0.0, 7, 14.0, channel=Channel())
    gw = Gateway(1, 0.0, 0.0)
    server = NetworkServer()
    server.gateways = [gw]
    server.nodes = [node]

    server.send_downlink(node, LinkCheckReq().to_bytes(), request_ack=True)
    frame = gw.pop_downlink(node.id)
    assert frame.fctrl & 0x20
    node.handle_downlink(frame)
    assert node.need_downlink_ack
    assert node.pending_mac_cmd == LinkCheckAns(margin=255, gw_cnt=1).to_bytes()

    up = node.prepare_uplink(b"hello")
    assert up.fctrl & 0x20
    assert up.payload.startswith(LinkCheckAns(margin=255, gw_cnt=1).to_bytes())
    assert not node.need_downlink_ack

    # DeviceTimeReq
    server.send_downlink(node, DeviceTimeReq().to_bytes())
    frame2 = gw.pop_downlink(node.id)
    node.handle_downlink(frame2)
    assert node.pending_mac_cmd is not None

from dataclasses import dataclass

@dataclass
class LoRaWANFrame:
    """Minimal representation of a LoRaWAN MAC frame."""
    mhdr: int
    fctrl: int
    fcnt: int
    payload: bytes
    confirmed: bool = False


def compute_rx1(end_time: float) -> float:
    """Return the opening time of RX1 window after an uplink."""
    return end_time + 1.0


def compute_rx2(end_time: float) -> float:
    """Return the opening time of RX2 window after an uplink."""
    return end_time + 2.0

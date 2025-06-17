import random
from typing import List, Sequence

from .channel import Channel


class MultiChannel:
    """Manage several Channel objects and assign them to nodes."""

    def __init__(self, channels: Sequence[Channel | float], method: str = "round-robin"):
        if not channels:
            raise ValueError("channels list must not be empty")
        self.channels: List[Channel] = []
        for ch in channels:
            if isinstance(ch, Channel):
                self.channels.append(ch)
            else:
                self.channels.append(Channel(frequency_hz=float(ch)))
        self.method = method.lower()
        self._rr_index = 0

    def select(self) -> Channel:
        """Return a channel according to the distribution method."""
        if self.method == "random":
            return random.choice(self.channels)
        # default round robin
        ch = self.channels[self._rr_index % len(self.channels)]
        self._rr_index += 1
        return ch

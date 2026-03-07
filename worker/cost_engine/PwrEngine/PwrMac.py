from __future__ import annotations

from worker.cost_engine.PwrEngine.ReadPowerMac import MacPowerReader, PowerReading


class PwrMac:
    def __init__(self, timeout_sec: float = 15.0):
        self.reader = MacPowerReader(timeout_sec=timeout_sec)

    def read(self, interval_sec: float = 1.0) -> PowerReading:
        return self.reader.read(interval_sec=interval_sec)

    def get_power_watts(self) -> float:
        return float(self.read().total_watts)

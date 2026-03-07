from __future__ import annotations

from worker.cost_engine.PwrEngine.ReadPowerLnx import LinuxPowerReader, PowerReading

class PwrLnx:
    def __init__(self):
        self.reader = LinuxPowerReader()

    def read(self) -> PowerReading:
        return self.reader.read()

    def get_power_watts(self) -> float:
        return float(self.read().total_watts)

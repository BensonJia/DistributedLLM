from __future__ import annotations

from worker.cost_engine.PwrEngine.ReadPowerWin import PowerReading, WindowsPowerReader


class PwrWin:
    def __init__(self, base_url: str = "http://localhost:8085", timeout_sec: float = 3.0):
        self.reader = WindowsPowerReader(base_url=base_url, timeout_sec=timeout_sec)

    def read(self) -> PowerReading:
        return self.reader.read()

    def get_power_watts(self) -> float:
        return float(self.read().total_watts)

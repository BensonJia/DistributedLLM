from __future__ import annotations


class ConstantPowerMeter:
    def __init__(self, watts: float):
        self.watts = float(watts)

    async def get_power_watts(self) -> float:
        return self.watts

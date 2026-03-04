from __future__ import annotations
from shared.config import WorkerSettings
from .electricity_api import ConstantElectricityPrice
from .power_api import ConstantPowerMeter

class CostCalculator:
    def __init__(
        self,
        settings: WorkerSettings,
        price_provider: ConstantElectricityPrice,
        power_meter: ConstantPowerMeter,
    ):
        self.settings = settings
        self.price_provider = price_provider
        self.power_meter = power_meter
        self._model_speed_tps: dict[str, float] = {}

    def record_inference_speed(self, model_name: str, total_tokens: int, elapsed_sec: float) -> float | None:
        if total_tokens <= 0 or elapsed_sec <= 0:
            return None
        speed = float(total_tokens) / float(elapsed_sec)
        if speed <= 0:
            return None
        self._model_speed_tps[model_name] = speed
        return speed

    def get_model_speed_tps(self, model_name: str) -> float | None:
        return self._model_speed_tps.get(model_name)

    async def cost_per_token(self, model_name: str) -> float:
        speed = self._model_speed_tps.get(model_name)
        if not speed:
            return float(self.settings.base_cost_per_token)

        power_watts = await self.power_meter.get_power_watts()
        price_per_kwh = await self.price_provider.get_price_per_kwh()
        return float(self.settings.base_cost_per_token) * float(power_watts) * float(price_per_kwh) / float(speed)

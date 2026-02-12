from __future__ import annotations
from shared.config import WorkerSettings
from .electricity_api import HttpElectricityPrice
from .model_cost_policy import model_size_factor

class CostCalculator:
    def __init__(self, settings: WorkerSettings, price_provider: HttpElectricityPrice):
        self.settings = settings
        self.price_provider = price_provider

    async def cost_per_token(self, model_name: str) -> float:
        price = await self.price_provider.get_price_per_kwh()
        factor = model_size_factor(model_name) * float(self.settings.model_size_multiplier)
        return float(self.settings.base_cost_per_token) * float(price) * float(factor)

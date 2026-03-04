from __future__ import annotations
import httpx


class ConstantElectricityPrice:
    def __init__(self, price_per_kwh: float):
        self.price_per_kwh = float(price_per_kwh)

    async def get_price_per_kwh(self) -> float:
        return self.price_per_kwh


class HttpElectricityPrice:
    def __init__(self, url: str, fallback: float):
        self.url = url
        self.fallback = float(fallback)

    async def get_price_per_kwh(self) -> float:
        if not self.url:
            return self.fallback
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(self.url)
                r.raise_for_status()
                data = r.json()
                v = float(data.get("price_per_kwh"))
                return v if v > 0 else self.fallback
        except Exception:
            return self.fallback

from __future__ import annotations
from dataclasses import dataclass
from worker.ollama_adapter.client import OllamaClient
from worker.cost_engine.calculator import CostCalculator

@dataclass
class WorkerState:
    status: str
    current_job_id: str | None
    models: list[tuple[str, float]]
    model_speeds_tps: dict[str, float]
    loaded_model: str | None

class StateCollector:
    def __init__(self, ollama: OllamaClient, cost_calc: CostCalculator):
        self.ollama = ollama
        self.cost_calc = cost_calc
        self._current_job_id: str | None = None
        self._loaded_model: str | None = None

    def set_job(self, job_id: str | None, loaded_model: str | None):
        self._current_job_id = job_id
        self._loaded_model = loaded_model

    async def collect(self) -> WorkerState:
        tags = await self.ollama.list_models()
        names = [m.get("name") for m in tags if m.get("name")]
        models = []
        model_speeds_tps: dict[str, float] = {}
        for name in names:
            c = await self.cost_calc.cost_per_token(name)
            models.append((name, c))
            speed = self.cost_calc.get_model_speed_tps(name)
            if speed:
                model_speeds_tps[name] = float(speed)
        status = "busy" if self._current_job_id else "idle"
        return WorkerState(
            status=status,
            current_job_id=self._current_job_id,
            models=models,
            model_speeds_tps=model_speeds_tps,
            loaded_model=self._loaded_model,
        )

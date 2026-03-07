from __future__ import annotations
from dataclasses import dataclass
from worker.ollama_adapter.client import OllamaClient
from worker.cost_engine.calculator import CostCalculator

@dataclass
class WorkerState:
    status: str
    current_job_id: str | None
    models: list[tuple[str, float, float | None]]
    model_speeds_tps: dict[str, float]
    model_avg_power_watts: dict[str, float]
    loaded_model: str | None

class StateCollector:
    def __init__(self, ollama: OllamaClient, cost_calc: CostCalculator):
        self.ollama = ollama
        self.cost_calc = cost_calc
        self._active_jobs: set[str] = set()
        self._loaded_model: str | None = None

    def set_job(self, job_id: str | None, loaded_model: str | None):
        if job_id:
            self._active_jobs.add(job_id)
            self._loaded_model = loaded_model
            return
        self._active_jobs.clear()
        self._loaded_model = loaded_model

    def start_job(self, job_id: str, loaded_model: str | None):
        self._active_jobs.add(job_id)
        self._loaded_model = loaded_model

    def finish_job(self, job_id: str):
        self._active_jobs.discard(job_id)
        if not self._active_jobs:
            self._loaded_model = None

    async def collect(self) -> WorkerState:
        tags = await self.ollama.list_models()
        names = [m.get("name") for m in tags if m.get("name")]
        models = []
        model_speeds_tps: dict[str, float] = {}
        model_avg_power_watts: dict[str, float] = {}
        for name in names:
            c = await self.cost_calc.cost_per_token(name)
            avg_power = self.cost_calc.get_model_avg_power_watts(name)
            models.append((name, c, avg_power))
            speed = self.cost_calc.get_model_speed_tps(name)
            if speed:
                model_speeds_tps[name] = float(speed)
            if avg_power:
                model_avg_power_watts[name] = float(avg_power)
        current_job_id = next(iter(self._active_jobs), None)
        status = "busy" if current_job_id else "idle"
        return WorkerState(
            status=status,
            current_job_id=current_job_id,
            models=models,
            model_speeds_tps=model_speeds_tps,
            model_avg_power_watts=model_avg_power_watts,
            loaded_model=self._loaded_model,
        )

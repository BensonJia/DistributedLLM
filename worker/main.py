from __future__ import annotations
import asyncio
from fastapi import FastAPI
from shared.config import WorkerSettings
from worker.worker_core.local_storage import LocalStorage
from worker.worker_core.registration import register as register_worker
from worker.ollama_adapter.client import OllamaClient
from worker.ollama_adapter.inference import OllamaInference
from worker.cost_engine.electricity_api import ConstantElectricityPrice
from worker.cost_engine.power_api import ConstantPowerMeter
from worker.cost_engine.calculator import CostCalculator
from worker.heartbeat.state_collector import StateCollector
from worker.heartbeat.reporter import HeartbeatReporter, build_heartbeat
from worker.job_puller.client import JobPullClient
from worker.job_puller.runner import JobRunner
from worker.worker_api.health import router as health_router

app = FastAPI(title="Distributed LLM Worker (Pull)", version="0.2.0")

settings = WorkerSettings()
storage = LocalStorage(settings.worker_data_dir)

ollama = OllamaClient(settings.ollama_url)
price_provider = ConstantElectricityPrice(settings.electricity_fallback_price_per_kwh)
power_meter = ConstantPowerMeter(settings.host_power_watts)
cost_calc = CostCalculator(settings, price_provider, power_meter)
collector = StateCollector(ollama, cost_calc)
infer = OllamaInference(ollama)

_worker_id: str | None = None
_hb_task: asyncio.Task | None = None
_job_task: asyncio.Task | None = None

async def ensure_worker_id() -> str:
    global _worker_id
    wid = storage.load_worker_id()
    if wid:
        _worker_id = wid
        return wid
    wid = await register_worker(settings.server_url, settings.internal_token)
    storage.save_worker_id(wid)
    _worker_id = wid
    return wid

async def heartbeat_loop():
    assert _worker_id is not None
    reporter = HeartbeatReporter(settings.server_url, settings.internal_token)
    while True:
        try:
            state = await collector.collect()
            hb = build_heartbeat(
                _worker_id,
                state,
                meta={
                    "ollama_url": settings.ollama_url,
                    "model_speeds_tps": state.model_speeds_tps,
                },
            )
            await reporter.send(hb)
        except Exception:
            pass
        await asyncio.sleep(settings.heartbeat_interval_sec)

@app.on_event("startup")
async def startup():
    global _hb_task, _job_task
    wid = await ensure_worker_id()
    _hb_task = asyncio.create_task(heartbeat_loop())
    job_client = JobPullClient(settings.server_url, settings.internal_token)
    runner = JobRunner(settings, job_client, infer, collector, cost_calc)
    _job_task = asyncio.create_task(runner.loop(wid))

@app.on_event("shutdown")
async def shutdown():
    global _hb_task, _job_task
    for t in (_hb_task, _job_task):
        if t:
            t.cancel()
            try:
                await t
            except Exception:
                pass

app.include_router(health_router)

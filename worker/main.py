from __future__ import annotations
import asyncio
import logging
import os
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
logger = logging.getLogger(__name__)

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


def _enable_debug_logging() -> None:
    if not settings.debug:
        return
    logging.getLogger("worker").setLevel(logging.DEBUG)
    logging.getLogger("shared").setLevel(logging.DEBUG)
    logger.info("Worker debug logging enabled")


def _log_startup_env() -> None:
    raw = (settings.startup_env_keys or "").strip()
    if not raw:
        return
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    for key in keys:
        value = os.environ.get(key, "<unset>")
        if "TOKEN" in key.upper() and value != "<unset>":
            value = "***"
        logger.info("startup env %s=%s", key, value)


async def ensure_worker_id() -> str:
    global _worker_id
    wid = storage.load_worker_id()
    if wid:
        if settings.debug:
            logger.debug("Login status=ok (reused local worker_id)")
        _worker_id = wid
        return wid
    if settings.debug:
        logger.debug("Login status=need_register (no local worker_id)")
    wid = await register_worker(settings.server_url, settings.internal_token, debug=settings.debug)
    storage.save_worker_id(wid)
    _worker_id = wid
    return wid

async def heartbeat_loop():
    assert _worker_id is not None
    reporter = HeartbeatReporter(settings.server_url, settings.internal_token, debug=settings.debug)
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
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e, exc_info=settings.debug)
        await asyncio.sleep(settings.heartbeat_interval_sec)

@app.on_event("startup")
async def startup():
    global _hb_task, _job_task
    _enable_debug_logging()
    logger.info("Worker startup: server_url=%s ollama_url=%s", settings.server_url, settings.ollama_url)
    _log_startup_env()
    wid = await ensure_worker_id()
    logger.info("Worker id=%s", wid)
    _hb_task = asyncio.create_task(heartbeat_loop())
    job_client = JobPullClient(settings.server_url, settings.internal_token, debug=settings.debug)
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

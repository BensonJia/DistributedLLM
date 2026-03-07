from __future__ import annotations
import asyncio
import logging
import time
from shared.config import WorkerSettings
from shared.schemas import WorkerJobCompleteRequest
from worker.cost_engine.calculator import CostCalculator
from worker.cost_engine.power_api import TaskPowerAttributor, TaskPowerReport
from worker.job_puller.client import JobPullClient
from worker.ollama_adapter.inference import OllamaInference

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(
        self,
        settings: WorkerSettings,
        client: JobPullClient,
        infer: OllamaInference,
        collector,
        cost_calc: CostCalculator,
        power_attributor: TaskPowerAttributor | None = None,
    ):
        self.settings = settings
        self.client = client
        self.infer = infer
        self.collector = collector
        self.cost_calc = cost_calc
        self.power_attributor = power_attributor

    async def _finish_power_track(self, tracker_task: asyncio.Task[TaskPowerReport] | None, stop_event: asyncio.Event) -> TaskPowerReport | None:
        stop_event.set()
        if not tracker_task:
            return None
        try:
            return await tracker_task
        except Exception as exc:
            logger.warning("Power tracking task failed: %s", exc)
            return None

    async def loop(self, worker_id: str):
        while True:
            try:
                if self.settings.debug:
                    logger.debug("Comm[pull] start: worker_id=%s", worker_id)
                job = await self.client.pull(worker_id)
            except Exception as e:
                if self.settings.debug:
                    logger.debug("Comm[pull] failed: worker_id=%s error=%s", worker_id, e)
                job = None

            if not job:
                await asyncio.sleep(self.settings.job_pull_interval_sec)
                continue

            if self.settings.debug:
                logger.debug("Comm[job] received: job_id=%s model=%s", job.job_id, job.model)
            self.collector.start_job(job.job_id, loaded_model=job.model)
            power_stop = asyncio.Event()
            power_task: asyncio.Task[TaskPowerReport] | None = None
            if self.power_attributor is not None:
                power_task = asyncio.create_task(
                    self.power_attributor.track(job.job_id, power_stop),
                    name=f"power-track-{job.job_id}",
                )
            try:
                started = time.perf_counter()
                if self.settings.debug:
                    logger.debug("Comm[infer] start: job_id=%s", job.job_id)
                text, pt, ct, tt = await self.infer.chat(
                    model=job.model,
                    messages=job.messages,
                    temperature=job.temperature,
                    top_p=job.top_p,
                    max_tokens=job.max_tokens,
                )
                elapsed = time.perf_counter() - started
                if self.settings.debug:
                    logger.debug("Comm[infer] done: job_id=%s total_tokens=%s elapsed=%.3fs", job.job_id, tt, elapsed)
                self.cost_calc.record_inference_speed(job.model, tt, elapsed)
                power_report = await self._finish_power_track(power_task, power_stop)
                avg_power_watts = float(power_report.avg_power_watts) if power_report else None
                if avg_power_watts:
                    self.cost_calc.record_model_avg_power(job.model, avg_power_watts)
                comp = WorkerJobCompleteRequest(
                    worker_id=worker_id,
                    job_id=job.job_id,
                    model=job.model,
                    output_text=text,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=tt,
                    avg_power_watts=avg_power_watts,
                    error=None,
                )
                if self.settings.debug:
                    logger.debug("Comm[complete] submit success payload: job_id=%s", job.job_id)
                await self.client.complete(comp)
            except Exception as e:
                power_report = await self._finish_power_track(power_task, power_stop)
                avg_power_watts = float(power_report.avg_power_watts) if power_report else None
                if self.settings.debug:
                    logger.debug("Comm[job] failed: job_id=%s error=%s", job.job_id, e)
                comp = WorkerJobCompleteRequest(
                    worker_id=worker_id,
                    job_id=job.job_id,
                    model=job.model,
                    output_text="",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    avg_power_watts=avg_power_watts,
                    error=str(e),
                )
                try:
                    await self.client.complete(comp)
                except Exception as ce:
                    if self.settings.debug:
                        logger.debug("Comm[complete] failure-report failed: job_id=%s error=%s", job.job_id, ce)
            finally:
                power_stop.set()
                self.collector.finish_job(job.job_id)

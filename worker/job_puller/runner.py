from __future__ import annotations
import asyncio
import logging
import time
from shared.config import WorkerSettings
from shared.schemas import WorkerJobCompleteRequest
from worker.cost_engine.calculator import CostCalculator
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
    ):
        self.settings = settings
        self.client = client
        self.infer = infer
        self.collector = collector
        self.cost_calc = cost_calc

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
            self.collector.set_job(job.job_id, loaded_model=job.model)
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
                comp = WorkerJobCompleteRequest(
                    worker_id=worker_id,
                    job_id=job.job_id,
                    model=job.model,
                    output_text=text,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=tt,
                    error=None,
                )
                if self.settings.debug:
                    logger.debug("Comm[complete] submit success payload: job_id=%s", job.job_id)
                await self.client.complete(comp)
            except Exception as e:
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
                    error=str(e),
                )
                try:
                    await self.client.complete(comp)
                except Exception as ce:
                    if self.settings.debug:
                        logger.debug("Comm[complete] failure-report failed: job_id=%s error=%s", job.job_id, ce)
            finally:
                self.collector.set_job(None, loaded_model=None)

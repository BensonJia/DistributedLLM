from __future__ import annotations
import asyncio
from shared.config import WorkerSettings
from shared.schemas import WorkerJobCompleteRequest
from worker.job_puller.client import JobPullClient
from worker.ollama_adapter.inference import OllamaInference

class JobRunner:
    def __init__(self, settings: WorkerSettings, client: JobPullClient, infer: OllamaInference, collector):
        self.settings = settings
        self.client = client
        self.infer = infer
        self.collector = collector

    async def loop(self, worker_id: str):
        while True:
            try:
                job = await self.client.pull(worker_id)
            except Exception:
                job = None

            if not job:
                await asyncio.sleep(self.settings.job_pull_interval_sec)
                continue

            self.collector.set_job(job.job_id, loaded_model=job.model)
            try:
                text, pt, ct, tt = await self.infer.chat(
                    model=job.model,
                    messages=job.messages,
                    temperature=job.temperature,
                    top_p=job.top_p,
                    max_tokens=job.max_tokens,
                )
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
                await self.client.complete(comp)
            except Exception as e:
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
                except Exception:
                    pass
            finally:
                self.collector.set_job(None, loaded_model=None)

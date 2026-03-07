from __future__ import annotations
import asyncio, json, time
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from shared.schemas import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChoice,
    OpenAIUsage,
    OpenAIModelList,
    OpenAIModelCard,
)
from shared.utils import now_ts, new_job_id, new_req_id
from server.deps import get_db, SessionLocal
from server.api.auth_middleware import require_api_key
from server.worker_registry.service import WorkerService
from server.job_queue.service import JobService
from server.request_queue.service import AwaitingRequestService
from server.cluster.service import ClusterService
from server.streaming.job_stream import job_stream_hub
from shared.config import ServerSettings

router = APIRouter()


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_with_role(job_id: str, model: str, created: int) -> str:
    return _sse_event(
        {
            "id": job_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
    )


def _chunk_with_content(job_id: str, model: str, created: int, content: str) -> str:
    return _sse_event(
        {
            "id": job_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
        }
    )


def _chunk_finish(job_id: str, model: str, created: int, finish_reason: str = "stop") -> str:
    return _sse_event(
        {
            "id": job_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
        }
    )


def _chunk_error(message: str) -> str:
    return _sse_event(
        {
            "error": {
                "message": message,
                "type": "server_error",
            }
        }
    )

@router.get("/v1/models", response_model=OpenAIModelList)
def list_models(_: str = Depends(require_api_key), db: Session = Depends(get_db)):
    settings = ServerSettings()
    models = set(WorkerService(db).list_models_union())
    if settings.cluster_enabled:
        models.update(ClusterService(db).list_known_models())
    return OpenAIModelList(data=[OpenAIModelCard(id=m) for m in sorted(models)])

@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
async def chat_completions(
    req: OpenAIChatCompletionRequest,
    token: str = Depends(require_api_key),
    db: Session = Depends(get_db),
    x_dllm_forward_hop: int = Header(default=0, alias="X-DLLM-Forward-Hop"),
    x_dllm_seen_nodes: str = Header(default="", alias="X-DLLM-Seen-Nodes"),
):
    settings = ServerSettings()
    worker_svc = WorkerService(db)
    job_svc = JobService(db)
    req_svc = AwaitingRequestService(db)
    cluster_svc = ClusterService(db)
    req_id = new_req_id()
    job_id = None
    stream_local_cleanup_managed = False

    # Enqueue the request
    req_svc.create(
        req_id=req_id,
        model_name=req.model,
        payload=req.model_dump()
    )

    # Poll for assignment
    assignment_timeout_sec = float(settings.request_timeout_sec)
    poll = max(0.05, float(settings.job_poll_interval_ms) / 1000.0)
    assigned_worker_id = None

    try:
        local_has_model = worker_svc.has_online_model(req.model)
        can_forward = bool(settings.cluster_enabled) and int(x_dllm_forward_hop) < int(settings.cluster_request_max_hops)
        local_wait_budget = assignment_timeout_sec
        if can_forward:
            wait_before_forward = max(0.0, float(settings.cluster_request_forward_after_sec))
            if not local_has_model:
                local_wait_budget = 0.0
            else:
                local_wait_budget = min(local_wait_budget, wait_before_forward)
        deadline = time.time() + local_wait_budget

        while time.time() < deadline:
            await asyncio.sleep(poll)
            db2 = SessionLocal()
            try:
                awaiting_req = AwaitingRequestService(db2).get(req_id)
                if awaiting_req and awaiting_req.assigned_worker_id:
                    assigned_worker_id = awaiting_req.assigned_worker_id
                    break
            finally:
                db2.close()

        if not assigned_worker_id:
            if can_forward:
                seen = {s.strip() for s in x_dllm_seen_nodes.split(",") if s.strip()}
                seen.add(settings.cluster_node_id)
                candidates = cluster_svc.choose_forward_candidates(
                    model_name=req.model,
                    max_candidates=int(settings.cluster_request_max_candidates),
                    exclude_node_ids=seen,
                )
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-DLLM-Forward-Hop": str(int(x_dllm_forward_hop) + 1),
                    "X-DLLM-Seen-Nodes": ",".join(sorted(seen)),
                }
                forward_timeout = float(settings.cluster_request_forward_timeout_sec)
                async with httpx.AsyncClient(timeout=forward_timeout) as client:
                    for target in candidates:
                        base_url = str(target.get("base_url") or "").rstrip("/")
                        if not base_url:
                            continue
                        try:
                            if req.stream:
                                timeout = httpx.Timeout(connect=forward_timeout, read=None, write=forward_timeout, pool=forward_timeout)
                                stream_client = httpx.AsyncClient(timeout=timeout)
                                try:
                                    request = stream_client.build_request(
                                        "POST",
                                        f"{base_url}/v1/chat/completions",
                                        json=req.model_dump(),
                                        headers=headers,
                                    )
                                    resp = await stream_client.send(request, stream=True)
                                except Exception:
                                    await stream_client.aclose()
                                    continue

                                if resp.status_code == 200:
                                    async def forward_iter():
                                        try:
                                            async for chunk in resp.aiter_bytes():
                                                if chunk:
                                                    yield chunk
                                        finally:
                                            await resp.aclose()
                                            await stream_client.aclose()

                                    return StreamingResponse(
                                        forward_iter(),
                                        media_type="text/event-stream",
                                        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                                    )
                                await resp.aread()
                                await resp.aclose()
                                await stream_client.aclose()
                                continue
                            resp = await client.post(f"{base_url}/v1/chat/completions", json=req.model_dump(), headers=headers)
                        except Exception:
                            continue
                        if resp.status_code == 200:
                            return OpenAIChatCompletionResponse.model_validate(resp.json())

            raise HTTPException(status_code=503, detail=f"No available worker for model={req.model}")

        job_id = new_job_id()
        worker_svc.set_job(assigned_worker_id, job_id)

        payload = {
            "job_id": job_id,
            "model": req.model,
            "messages": [m.model_dump() for m in req.messages],
            "temperature": req.temperature,
            "top_p": req.top_p,
            "max_tokens": req.max_tokens,
            "stream": req.stream,
        }
        if req.stream:
            await job_stream_hub.ensure(job_id)
        job_svc.create(job_id=job_id, model=req.model, assigned_worker_id=assigned_worker_id, payload=payload)

        if req.stream:
            stream_local_cleanup_managed = True

            async def stream_iter():
                created = now_ts()
                q = await job_stream_hub.subscribe(job_id)
                try:
                    yield _chunk_with_role(job_id=job_id, model=req.model, created=created)
                    job_deadline = time.time() + float(settings.job_max_wait_sec)
                    while time.time() < job_deadline:
                        try:
                            evt = await asyncio.wait_for(q.get(), timeout=poll)
                        except asyncio.TimeoutError:
                            continue
                        et = str(evt.get("type") or "")
                        if et == "delta":
                            content = str(evt.get("delta") or "")
                            if content:
                                yield _chunk_with_content(job_id=job_id, model=req.model, created=created, content=content)
                            continue
                        if et == "done":
                            yield _chunk_finish(job_id=job_id, model=req.model, created=created, finish_reason="stop")
                            yield "data: [DONE]\n\n"
                            return
                        if et == "error":
                            err_msg = str(evt.get("message") or "Worker job failed: unknown error")
                            yield _chunk_error(err_msg)
                            yield "data: [DONE]\n\n"
                            return

                    # Timeout path
                    db2 = SessionLocal()
                    try:
                        job = JobService(db2).get(job_id)
                        if job and job.status == "done":
                            data = json.loads(job.result_json or "{}")
                            output_text = str(data.get("output_text") or "")
                            if output_text:
                                yield _chunk_with_content(job_id=job_id, model=req.model, created=created, content=output_text)
                            yield _chunk_finish(job_id=job_id, model=req.model, created=created, finish_reason="stop")
                            yield "data: [DONE]\n\n"
                            return
                        if job and job.status == "failed":
                            err_msg = f"Worker job failed: {job.error or 'unknown error'}"
                            yield _chunk_error(err_msg)
                            yield "data: [DONE]\n\n"
                            return
                    finally:
                        db2.close()

                    yield _chunk_error("Job timed out waiting for worker")
                    yield "data: [DONE]\n\n"
                finally:
                    await job_stream_hub.close(job_id)
                    db3 = SessionLocal()
                    try:
                        AwaitingRequestService(db3).delete(req_id)
                        if assigned_worker_id and job_id:
                            WorkerService(db3).clear_job_if_matches(assigned_worker_id, job_id)
                    finally:
                        db3.close()

            return StreamingResponse(
                stream_iter(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        # Poll for job completion
        job_deadline = time.time() + float(settings.job_max_wait_sec)
        while time.time() < job_deadline:
            await asyncio.sleep(poll)
            db2 = SessionLocal()
            try:
                job = JobService(db2).get(job_id)
                if not job:
                    continue
                if job.status == "done":
                    data = json.loads(job.result_json or "{}")
                    usage = OpenAIUsage(
                        prompt_tokens=int(data.get("prompt_tokens") or 0),
                        completion_tokens=int(data.get("completion_tokens") or 0),
                        total_tokens=int(data.get("total_tokens") or 0),
                    )
                    choice = OpenAIChoice(index=0, message={"role": "assistant", "content": data.get("output_text","")}, finish_reason="stop")
                    return OpenAIChatCompletionResponse(
                        id=job_id,
                        created=now_ts(),
                        model=req.model,
                        choices=[choice],
                        usage=usage,
                    )
                if job.status == "failed":
                    raise HTTPException(status_code=502, detail=f"Worker job failed: {job.error or 'unknown error'}")
            finally:
                db2.close()

        raise HTTPException(status_code=504, detail="Job timed out waiting for worker")

    finally:
        # Clean up the awaiting request and the worker's job assignment
        if not stream_local_cleanup_managed:
            req_svc.delete(req_id)
            if assigned_worker_id and job_id:
                worker_svc.clear_job_if_matches(assigned_worker_id, job_id)

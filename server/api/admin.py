from __future__ import annotations

import json
import datetime
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from server.deps import get_db
from server.api.auth_middleware import require_api_key
from server.worker_registry.models import Worker, WorkerModel
from server.job_queue.models import Job
from server.cluster.models import ClusterNode

router = APIRouter(prefix="/admin", tags=["admin"])

def _iso(dt: Optional[datetime.datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def _work_state(worker: Worker) -> Literal["idle", "busy"]:
    return "busy" if worker.current_job_id else "idle"

@router.get("/workers")
def list_workers(_: str = Depends(require_api_key), db: Session = Depends(get_db)) -> List[dict]:
    rows = db.execute(select(Worker).order_by(Worker.worker_id.asc())).scalars().all()
    return [{
        "worker_id": w.worker_id,
        "status": "online" if w.status == "online" else "offline",
        "work_state": _work_state(w),
        "current_job_id": w.current_job_id,
        "last_heartbeat": _iso(w.last_heartbeat),
    } for w in rows]

@router.get("/workers/{worker_id}")
def get_worker(worker_id: str, _: str = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    wobj = db.get(Worker, worker_id)
    if not wobj:
        raise HTTPException(status_code=404, detail="worker not found")

    models = db.execute(
        select(WorkerModel.model_name, WorkerModel.cost_per_token)
        .where(WorkerModel.worker_id == worker_id)
        .order_by(WorkerModel.model_name.asc())
    ).all()

    return {
        "worker_id": wobj.worker_id,
        "status": "online" if wobj.status == "online" else "offline",
        "work_state": _work_state(wobj),
        "current_job_id": wobj.current_job_id,
        "last_heartbeat": _iso(wobj.last_heartbeat),
        "models": [{"name": n, "cost_per_token": float(c)} for n, c in models],
    }

@router.get("/jobs")
def list_jobs(_: str = Depends(require_api_key), db: Session = Depends(get_db)) -> List[dict]:
    rows = db.execute(select(Job).order_by(Job.created_at.desc())).scalars().all()
    return [{
        "job_id": j.job_id,
        "status": j.status,
        "model": j.model,
        "assigned_worker_id": j.assigned_worker_id,
        "created_at": _iso(j.created_at),
        "updated_at": _iso(j.updated_at),
    } for j in rows]

@router.get("/jobs/{job_id}")
def get_job(job_id: str, _: str = Depends(require_api_key), db: Session = Depends(get_db)) -> dict:
    job = db.execute(select(Job).where(Job.job_id == job_id)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    result = None
    if job.result_json:
        try:
            raw = json.loads(job.result_json)
            result = {
                "output_text": raw.get("output_text", ""),
                "prompt_tokens": int(raw.get("prompt_tokens") or 0),
                "completion_tokens": int(raw.get("completion_tokens") or 0),
                "total_tokens": int(raw.get("total_tokens") or 0),
            }
        except Exception:
            result = None

    return {
        "job_id": job.job_id,
        "status": job.status,
        "model": job.model,
        "assigned_worker_id": job.assigned_worker_id,
        "created_at": _iso(job.created_at),
        "updated_at": _iso(job.updated_at),
        "result": result,
        "error": job.error,
    }


@router.get("/cluster/nodes")
def list_cluster_nodes(_: str = Depends(require_api_key), db: Session = Depends(get_db)) -> List[dict]:
    rows = db.execute(select(ClusterNode).order_by(ClusterNode.is_self.desc(), ClusterNode.node_id.asc())).scalars().all()
    out: List[dict] = []
    for n in rows:
        try:
            models = json.loads(n.models_json or "[]")
        except Exception:
            models = []
        out.append(
            {
                "node_id": n.node_id,
                "base_url": n.base_url,
                "revision": int(n.revision),
                "is_self": bool(n.is_self),
                "is_alive": bool(n.is_alive),
                "models": models if isinstance(models, list) else [],
                "idle_workers": int(n.idle_workers),
                "busy_workers": int(n.busy_workers),
                "latency_ms": float(n.latency_ms) if n.latency_ms is not None else None,
                "last_probe_at": _iso(n.last_probe_at),
                "last_seen_at": _iso(n.last_seen_at),
                "state_version": int(n.state_version),
                "updated_at": _iso(n.updated_at),
            }
        )
    return out

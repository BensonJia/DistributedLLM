from __future__ import annotations

import datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.worker_registry.models import Worker, WorkerModel

from .repository import ClusterRepository


def normalize_base_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


class ClusterService:
    def __init__(self, db: Session):
        self.repo = ClusterRepository(db)
        self.db = db

    def summarize_local_workers(self) -> tuple[list[str], int, int]:
        models = self.db.execute(
            select(WorkerModel.model_name)
            .join(Worker, Worker.worker_id == WorkerModel.worker_id)
            .where(Worker.status == "online")
            .distinct()
        ).all()
        model_names = sorted({row[0] for row in models if row[0]})
        idle_count = self.db.execute(
            select(func.count()).select_from(Worker).where(Worker.status == "online", Worker.current_job_id.is_(None))
        ).scalar_one()
        busy_count = self.db.execute(
            select(func.count()).select_from(Worker).where(Worker.status == "online", Worker.current_job_id.is_not(None))
        ).scalar_one()
        return model_names, int(idle_count or 0), int(busy_count or 0)

    def ensure_self_node(self, *, node_id: str, base_url: str):
        base = normalize_base_url(base_url)
        existing = self.repo.get_node(node_id)
        revision = int(existing.revision + 1) if existing else 1
        models, idle_workers, busy_workers = self.summarize_local_workers()
        return self.repo.upsert_node(
            node_id=node_id,
            base_url=base,
            revision=revision,
            is_self=True,
            is_alive=True,
            models=models,
            idle_workers=idle_workers,
            busy_workers=busy_workers,
            tombstone=False,
            last_seen_at=datetime.datetime.utcnow(),
        )

    def apply_remote_entry(self, entry: dict[str, Any]) -> bool:
        node_id = str(entry.get("node_id") or "").strip()
        base_url = normalize_base_url(str(entry.get("base_url") or ""))
        if not node_id or not base_url:
            return False
        incoming_rev = int(entry.get("revision") or 0)
        current = self.repo.get_node(node_id)
        if current and incoming_rev < int(current.revision):
            return False
        models = entry.get("models") if isinstance(entry.get("models"), list) else []
        self.repo.upsert_node(
            node_id=node_id,
            base_url=base_url,
            revision=incoming_rev,
            is_self=bool(current.is_self) if current else False,
            is_alive=bool(entry.get("is_alive", True)),
            models=[str(m) for m in models],
            idle_workers=int(entry.get("idle_workers") or 0),
            busy_workers=int(entry.get("busy_workers") or 0),
            tombstone=bool(entry.get("tombstone", False)),
            last_seen_at=datetime.datetime.utcnow(),
        )
        return True

    def apply_remote_entries(self, entries: list[dict[str, Any]]) -> int:
        changed = 0
        for entry in entries:
            if self.apply_remote_entry(entry):
                changed += 1
        return changed

    def export_deltas(self, since_state_version: int, limit: int) -> tuple[int, list[dict[str, Any]]]:
        rows = self.repo.list_deltas_after(since_state_version, limit)
        max_sv = since_state_version
        out: list[dict[str, Any]] = []
        for node in rows:
            out.append(self.repo.node_to_wire(node))
            max_sv = max(max_sv, int(node.state_version))
        return max_sv, out

    def choose_gossip_neighbors(self, fanout: int) -> list[dict[str, Any]]:
        rows = self.repo.list_alive_remote_nodes()
        selected = rows[: max(0, int(fanout))]
        return [self.repo.node_to_wire(n) for n in selected]

    def choose_forward_candidates(self, *, model_name: str, max_candidates: int, exclude_node_ids: set[str]) -> list[dict[str, Any]]:
        rows = self.repo.list_alive_remote_nodes()
        filtered: list[dict[str, Any]] = []
        for node in rows:
            if node.node_id in exclude_node_ids:
                continue
            data = self.repo.node_to_wire(node)
            models = data.get("models") or []
            if model_name and model_name not in models:
                continue
            filtered.append(data)
        filtered.sort(key=lambda x: (x.get("latency_ms") is None, x.get("latency_ms") or 10**9, -(x.get("idle_workers") or 0)))
        return filtered[: max(0, int(max_candidates))]

    def list_known_models(self) -> list[str]:
        models: set[str] = set()
        for node in self.repo.list_alive_remote_nodes():
            data = self.repo.node_to_wire(node)
            for model_name in data.get("models") or []:
                if model_name:
                    models.add(str(model_name))
        return sorted(models)

    async def probe_latency(self, node: dict[str, Any], *, timeout_sec: float, token: str) -> float | None:
        url = normalize_base_url(str(node.get("base_url") or ""))
        if not url:
            return None
        ping_url = urljoin(url + "/", "internal/cluster/ping")
        headers = {}
        if token:
            headers["X-Worker-Token"] = token
        start = datetime.datetime.utcnow()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.get(ping_url, headers=headers)
                if resp.status_code != 200:
                    return None
        except Exception:
            return None
        elapsed = datetime.datetime.utcnow() - start
        return round(elapsed.total_seconds() * 1000.0, 2)

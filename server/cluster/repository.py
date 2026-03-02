from __future__ import annotations

import datetime
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ClusterNeighborSync, ClusterNode


class ClusterRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_node(self, node_id: str) -> ClusterNode | None:
        return self.db.execute(select(ClusterNode).where(ClusterNode.node_id == node_id)).scalar_one_or_none()

    def get_node_by_base_url(self, base_url: str) -> ClusterNode | None:
        return self.db.execute(select(ClusterNode).where(ClusterNode.base_url == base_url)).scalar_one_or_none()

    def get_self_node(self) -> ClusterNode | None:
        return self.db.execute(select(ClusterNode).where(ClusterNode.is_self.is_(True))).scalar_one_or_none()

    def list_alive_remote_nodes(self) -> list[ClusterNode]:
        stmt = (
            select(ClusterNode)
            .where(ClusterNode.is_self.is_(False), ClusterNode.is_alive.is_(True), ClusterNode.tombstone.is_(False))
            .order_by(ClusterNode.last_seen_at.desc())
        )
        rows = self.db.execute(stmt).scalars().all()
        rows.sort(key=lambda n: (n.latency_ms is None, n.latency_ms or 10**9))
        return rows

    def list_all_nodes(self) -> list[ClusterNode]:
        stmt = select(ClusterNode).order_by(ClusterNode.is_self.desc(), ClusterNode.node_id.asc())
        return self.db.execute(stmt).scalars().all()

    def list_deltas_after(self, state_version: int, limit: int) -> list[ClusterNode]:
        stmt = (
            select(ClusterNode)
            .where(ClusterNode.state_version > int(state_version))
            .order_by(ClusterNode.state_version.asc())
            .limit(int(limit))
        )
        return self.db.execute(stmt).scalars().all()

    def max_state_version(self) -> int:
        row = self.db.execute(select(ClusterNode.state_version).order_by(ClusterNode.state_version.desc()).limit(1)).first()
        if not row:
            return 0
        return int(row[0] or 0)

    def get_neighbor_sync(self, neighbor_node_id: str) -> ClusterNeighborSync | None:
        return self.db.execute(
            select(ClusterNeighborSync).where(ClusterNeighborSync.neighbor_node_id == neighbor_node_id)
        ).scalar_one_or_none()

    def upsert_neighbor_sync(self, neighbor_node_id: str, *, last_sent_state_version: int, success_at: datetime.datetime):
        sync = self.get_neighbor_sync(neighbor_node_id)
        if not sync:
            sync = ClusterNeighborSync(neighbor_node_id=neighbor_node_id)
            self.db.add(sync)
        sync.last_sent_state_version = int(last_sent_state_version)
        sync.last_success_at = success_at
        sync.updated_at = success_at
        self.db.commit()
        self.db.refresh(sync)
        return sync

    def _next_state_version(self) -> int:
        return self.max_state_version() + 1

    def upsert_node(
        self,
        *,
        node_id: str,
        base_url: str,
        revision: int,
        is_self: bool,
        is_alive: bool,
        models: list[str],
        idle_workers: int,
        busy_workers: int,
        tombstone: bool,
        last_seen_at: datetime.datetime,
    ) -> ClusterNode:
        node = self.get_node(node_id)
        if not node:
            node = self.get_node_by_base_url(base_url)
        if not node:
            node = ClusterNode(node_id=node_id)
            self.db.add(node)
        else:
            node.node_id = node_id
        node.base_url = base_url
        node.revision = int(revision)
        node.is_self = bool(is_self)
        node.is_alive = bool(is_alive)
        node.models_json = json.dumps(sorted({m for m in models if m}), ensure_ascii=False)
        node.idle_workers = int(idle_workers)
        node.busy_workers = int(busy_workers)
        node.tombstone = bool(tombstone)
        node.last_seen_at = last_seen_at
        node.updated_at = datetime.datetime.utcnow()
        node.state_version = self._next_state_version()
        self.db.commit()
        self.db.refresh(node)
        return node

    def update_latency(self, node_id: str, latency_ms: float | None):
        node = self.get_node(node_id)
        if not node:
            return None
        node.latency_ms = float(latency_ms) if latency_ms is not None else None
        now = datetime.datetime.utcnow()
        node.last_probe_at = now
        node.updated_at = now
        node.state_version = self._next_state_version()
        self.db.commit()
        self.db.refresh(node)
        return node

    def mark_node_offline(self, node_id: str):
        node = self.get_node(node_id)
        if not node:
            return None
        node.is_alive = False
        node.updated_at = datetime.datetime.utcnow()
        node.state_version = self._next_state_version()
        self.db.commit()
        self.db.refresh(node)
        return node

    @staticmethod
    def node_to_wire(node: ClusterNode) -> dict[str, Any]:
        try:
            models = json.loads(node.models_json or "[]")
        except Exception:
            models = []
        return {
            "node_id": node.node_id,
            "base_url": node.base_url,
            "revision": int(node.revision),
            "is_alive": bool(node.is_alive),
            "models": models if isinstance(models, list) else [],
            "idle_workers": int(node.idle_workers),
            "busy_workers": int(node.busy_workers),
            "tombstone": bool(node.tombstone),
            "updated_at_ts": int(node.updated_at.timestamp()),
            "state_version": int(node.state_version),
            "latency_ms": float(node.latency_ms) if node.latency_ms is not None else None,
        }

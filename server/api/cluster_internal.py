from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.api.auth_middleware import require_internal_token
from server.cluster.service import ClusterService
from server.deps import get_db
from shared.config import ServerSettings
from shared.schemas import ClusterGossipRequest, ClusterGossipResponse, ClusterNodeEntry

router = APIRouter()


@router.get("/internal/cluster/ping")
def cluster_ping(_: str = Depends(require_internal_token)):
    return {"ok": True}


@router.post("/internal/cluster/gossip", response_model=ClusterGossipResponse)
def cluster_gossip(payload: ClusterGossipRequest, _: str = Depends(require_internal_token), db: Session = Depends(get_db)):
    settings = ServerSettings()
    svc = ClusterService(db)
    svc.apply_remote_entry(
        {
            "node_id": payload.sender_node_id,
            "base_url": payload.sender_base_url,
            "revision": payload.sender_revision,
            "is_alive": True,
            "models": payload.sender_models,
            "idle_workers": payload.sender_idle_workers,
            "busy_workers": payload.sender_busy_workers,
            "tombstone": payload.sender_tombstone,
        }
    )
    if payload.entries:
        svc.apply_remote_entries([entry.model_dump() for entry in payload.entries])

    max_sv, deltas = svc.export_deltas(
        since_state_version=int(payload.sender_since_state_version or 0),
        limit=int(settings.cluster_delta_batch_size),
    )
    self_node = svc.repo.get_self_node()
    receiver_id = self_node.node_id if self_node else settings.cluster_node_id
    return ClusterGossipResponse(
        ok=True,
        receiver_node_id=receiver_id,
        receiver_state_version=svc.repo.max_state_version(),
        max_state_version_sent=max_sv,
        entries=[ClusterNodeEntry.model_validate(d) for d in deltas],
    )


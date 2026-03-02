from __future__ import annotations

import datetime
import json
import logging
from urllib.parse import urljoin

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from server.cluster.service import ClusterService, normalize_base_url
from server.deps import SessionLocal
from shared.config import ServerSettings
from shared.schemas import ClusterGossipRequest, ClusterGossipResponse, ClusterNodeEntry

logger = logging.getLogger(__name__)


def _seed_nodes(svc: ClusterService, settings: ServerSettings):
    seed_urls = [normalize_base_url(u) for u in (settings.cluster_seed_urls or "").split(",") if u.strip()]
    now = datetime.datetime.utcnow()
    for seed in seed_urls:
        if not seed or seed == normalize_base_url(settings.cluster_self_url):
            continue
        node_id = f"seed:{seed}"
        if svc.repo.get_node(node_id):
            continue
        svc.repo.upsert_node(
            node_id=node_id,
            base_url=seed,
            revision=1,
            is_self=False,
            is_alive=True,
            models=[],
            idle_workers=0,
            busy_workers=0,
            tombstone=False,
            last_seen_at=now,
        )


def start_cluster_sync():
    settings = ServerSettings()
    if not settings.cluster_enabled:
        logger.info("Cluster sync is disabled.")
        return None

    sched = BackgroundScheduler(daemon=True)

    def _job():
        settings2 = ServerSettings()
        db = SessionLocal()
        try:
            svc = ClusterService(db)
            self_node = svc.ensure_self_node(node_id=settings2.cluster_node_id, base_url=settings2.cluster_self_url)
            _seed_nodes(svc, settings2)
            neighbors = svc.choose_gossip_neighbors(settings2.cluster_neighbor_count)

            headers = {}
            if settings2.internal_token:
                headers["X-Worker-Token"] = settings2.internal_token

            for neighbor in neighbors:
                node_id = str(neighbor.get("node_id") or "")
                base_url = normalize_base_url(str(neighbor.get("base_url") or ""))
                if not node_id or not base_url:
                    continue

                latency = None
                try:
                    with httpx.Client(timeout=float(settings2.cluster_probe_timeout_sec)) as client:
                        ping_resp = client.get(urljoin(base_url + "/", "internal/cluster/ping"), headers=headers)
                        if ping_resp.status_code == 200:
                            elapsed_ms = ping_resp.elapsed.total_seconds() * 1000.0
                            latency = round(elapsed_ms, 2)
                except Exception:
                    latency = None
                if latency is None:
                    svc.repo.mark_node_offline(node_id)
                    continue
                svc.repo.update_latency(node_id, latency)

            fanout_targets = svc.choose_gossip_neighbors(settings2.cluster_gossip_fanout)
            for neighbor in fanout_targets:
                neighbor_id = str(neighbor.get("node_id") or "")
                base_url = normalize_base_url(str(neighbor.get("base_url") or ""))
                if not neighbor_id or not base_url:
                    continue
                sync = svc.repo.get_neighbor_sync(neighbor_id)
                since = int(sync.last_sent_state_version if sync else 0)
                max_sv, deltas = svc.export_deltas(since, int(settings2.cluster_delta_batch_size))
                payload = ClusterGossipRequest(
                    sender_node_id=self_node.node_id,
                    sender_base_url=self_node.base_url,
                    sender_revision=int(self_node.revision),
                    sender_models=(json.loads(self_node.models_json or "[]")),
                    sender_idle_workers=int(self_node.idle_workers),
                    sender_busy_workers=int(self_node.busy_workers),
                    sender_tombstone=bool(self_node.tombstone),
                    sender_since_state_version=since,
                    entries=[ClusterNodeEntry.model_validate(d) for d in deltas],
                )
                try:
                    with httpx.Client(timeout=float(settings2.cluster_gossip_timeout_sec)) as client:
                        resp = client.post(
                            urljoin(base_url + "/", "internal/cluster/gossip"),
                            headers=headers,
                            json=payload.model_dump(),
                        )
                    if resp.status_code != 200:
                        svc.repo.mark_node_offline(neighbor_id)
                        continue
                    parsed = ClusterGossipResponse.model_validate(resp.json())
                    svc.apply_remote_entries([e.model_dump() for e in parsed.entries])
                    svc.repo.upsert_neighbor_sync(
                        neighbor_id,
                        last_sent_state_version=int(max_sv),
                        success_at=datetime.datetime.utcnow(),
                    )
                except Exception:
                    svc.repo.mark_node_offline(neighbor_id)
        except Exception:
            logger.exception("Cluster sync job failed")
        finally:
            db.close()

    sched.add_job(
        _job,
        "interval",
        seconds=float(settings.cluster_gossip_interval_sec),
        id="cluster_sync",
        replace_existing=True,
    )
    sched.start()
    logger.info("Cluster sync background job started.")
    return sched

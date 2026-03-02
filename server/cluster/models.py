from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from server.db import Base


class ClusterNode(Base):
    __tablename__ = "cluster_nodes"
    __table_args__ = (
        UniqueConstraint("base_url", name="uq_cluster_nodes_base_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    is_self: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    models_json: Mapped[str] = mapped_column(Text, default="[]")
    idle_workers: Mapped[int] = mapped_column(Integer, default=0)
    busy_workers: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_probe_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)
    tombstone: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    state_version: Mapped[int] = mapped_column(Integer, default=0, index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)


class ClusterNeighborSync(Base):
    __tablename__ = "cluster_neighbor_sync"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    neighbor_node_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    last_sent_state_version: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)


Index("ix_cluster_nodes_alive_latency", ClusterNode.is_alive, ClusterNode.latency_ms)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, UniqueConstraint, Index
from server.db import Base
import datetime

class Worker(Base):
    __tablename__ = "workers"
    worker_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_heartbeat: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String, default="online")
    current_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    models = relationship("WorkerModel", back_populates="worker", cascade="all, delete-orphan")

Index("ix_workers_status", Worker.status)

class WorkerModel(Base):
    __tablename__ = "worker_models"
    __table_args__ = (UniqueConstraint("worker_id", "model_name", name="uq_worker_model"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.worker_id"), index=True)
    model_name: Mapped[str] = mapped_column(String, index=True)
    cost_per_token: Mapped[float] = mapped_column(Float, default=0.0)
    worker = relationship("Worker", back_populates="models")

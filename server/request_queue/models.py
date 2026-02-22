from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text, Index
from server.db import Base
import datetime

class AwaitingRequest(Base):
    __tablename__ = "awaiting_reqs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    req_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending/assigned
    model_name: Mapped[str] = mapped_column(String, index=True)
    assigned_worker_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)

Index("ix_awaiting_reqs_status", AwaitingRequest.status)

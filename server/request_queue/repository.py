from __future__ import annotations
import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import AwaitingRequest

class AwaitingRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_request(self, *, req_id: str, model_name: str, payload: dict) -> AwaitingRequest:
        obj = AwaitingRequest(
            req_id=req_id,
            status="pending",
            model_name=model_name,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_request(self, req_id: str) -> AwaitingRequest | None:
        return self.db.execute(select(AwaitingRequest).where(AwaitingRequest.req_id == req_id)).scalar_one_or_none()

    def get_pending_requests(self) -> list[AwaitingRequest]:
        stmt = select(AwaitingRequest).where(AwaitingRequest.status == "pending").order_by(AwaitingRequest.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def assign_worker_to_request(self, req_id: str, worker_id: str) -> AwaitingRequest | None:
        # Use with_for_update to lock the row for update
        stmt = select(AwaitingRequest).where(AwaitingRequest.req_id == req_id).with_for_update()
        req = self.db.execute(stmt).scalar_one_or_none()
        
        if not req or req.status != 'pending':
            # Already assigned by another process
            return None
            
        req.status = "assigned"
        req.assigned_worker_id = worker_id
        self.db.commit()
        self.db.refresh(req)
        return req

    def delete_request(self, req_id: str):
        obj = self.db.execute(select(AwaitingRequest).where(AwaitingRequest.req_id == req_id)).scalar_one_or_none()
        if obj:
            self.db.delete(obj)
            self.db.commit()
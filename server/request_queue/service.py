from __future__ import annotations
from sqlalchemy.orm import Session
from .repository import AwaitingRequestRepository
from .models import AwaitingRequest

class AwaitingRequestService:
    def __init__(self, db: Session):
        self.repo = AwaitingRequestRepository(db)

    def create(self, req_id: str, model_name: str, payload: dict) -> AwaitingRequest:
        return self.repo.create_request(req_id=req_id, model_name=model_name, payload=payload)

    def get(self, req_id: str) -> AwaitingRequest | None:
        return self.repo.get_request(req_id)

    def get_pending(self) -> list[AwaitingRequest]:
        return self.repo.get_pending_requests()

    def assign_worker(self, req_id: str, worker_id: str) -> AwaitingRequest | None:
        return self.repo.assign_worker_to_request(req_id, worker_id)

    def delete(self, req_id: str):
        self.repo.delete_request(req_id)

    def release_assigned_requests(self, worker_ids: list[str]) -> int:
        return self.repo.release_assigned_requests(worker_ids)

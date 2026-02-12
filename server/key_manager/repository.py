from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import ApiKey

class ApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, key: str):
        return self.db.execute(select(ApiKey).where(ApiKey.key == key)).scalar_one_or_none()

    def create_if_missing(self, key: str):
        existing = self.get_by_key(key)
        if existing:
            return existing
        obj = ApiKey(key=key, status="active")
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

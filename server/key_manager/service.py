from sqlalchemy.orm import Session
from .repository import ApiKeyRepository

class ApiKeyService:
    def __init__(self, db: Session):
        self.repo = ApiKeyRepository(db)

    def verify(self, key: str) -> bool:
        obj = self.repo.get_by_key(key)
        return bool(obj and obj.status == "active")

    def bootstrap(self, keys_csv: str):
        keys = [k.strip() for k in (keys_csv or "").split(",") if k.strip()]
        for k in keys:
            self.repo.create_if_missing(k)

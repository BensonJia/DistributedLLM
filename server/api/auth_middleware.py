from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from server.deps import get_db
from server.key_manager.service import ApiKeyService

def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1]

def require_api_key(token: str = Depends(get_bearer_token), db: Session = Depends(get_db)):
    if not ApiKeyService(db).verify(token):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token

from __future__ import annotations
import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database.session import get_db
from app.database.repositories.robot_repository import RobotRepository

bearer_scheme = HTTPBearer(auto_error=False)


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"pb_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using HMAC-SHA256."""
    return hmac.new(
        settings.api_secret.encode(),
        api_key.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """Constant-time compare of API key hash."""
    expected = hash_api_key(api_key)
    return hmac.compare_digest(expected, api_key_hash)


def create_robot_token(robot_id: str) -> str:
    """Issue a short-lived JWT for a registered robot."""
    payload = {
        "sub": robot_id,
        "type": "robot",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_robot_token(token: str) -> dict:
    """Decode and verify a robot JWT."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_robot(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """FastAPI dependency that validates robot JWT."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    payload = decode_robot_token(credentials.credentials)
    robot_id = payload.get("sub")
    if not robot_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    repo = RobotRepository(db)
    robot = await repo.get_by_robot_id(robot_id)
    if not robot:
        raise HTTPException(status_code=401, detail="Robot not found")
    return {"robot_id": robot_id, "robot": robot}

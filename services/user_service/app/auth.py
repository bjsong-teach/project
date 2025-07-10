import secrets
from typing import Optional
from passlib.context import CryptContext
from redis.asyncio import Redis

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_TTL_SECONDS = 3600

def get_password_hash(password:str) -> str:
    return pwd_context.hash(password)
async def create_session(redis: Redis, user_id:int) -> str:
    session_id = secrets.token_hex(16)
    await redis.setex(f"session:{session_id}", SESSION_TTL_SECONDS, user_id)
    return session_id


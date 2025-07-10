import os
from typing import Annotated
from fastapi import FastAPI, status, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from redis.asyncio import Redis

from models import User, UserCreate, UserPublic
from database import init_db, get_session
from redis_client import get_redis
from auth import get_password_hash, create_session
app = FastAPI(title="User Service")

STATIC_DIR = "/app/static"
PROFILE_IMAGE_DIR = f"{STATIC_DIR}/profiles"
os.makedirs(PROFILE_IMAGE_DIR, exist_ok =True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def create_user_public(user: User) -> UserPublic:
    image_url = f"/static/profiles/{user.profile_image_filename}" if user.profile_image_filename else "https://www.w3schools.com/w3images/avatar_g.jpg"
    user_dict = user.model_dump()
    user_dict["profile_image_url"] = image_url
    return UserPublic.model_validate(user_dict)
    '''
    if user.profile_image_filename:
        image_url = f"/static/profiles/{user.profile_image_filename}" 
    else:
         image_url = "https://www.w3schools.com/w3images/avatar_g.jpg"
    '''

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/")
def health_check():
    return {"status":"User service running"}

@app.post('/api/auth/register', response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    response: Response,
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    #username='111' email='3R#SDAF@DSAF.COM' password='111' bio='FDSDFSA '
    print(user_data)
    statement = select(User).where(User.email==user_data.email)
    exist_user_result = await session.exec(statement)
    print(user_data)
    if exist_user_result.one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일 입니다.")
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User.model_validate(user_data, update={"hashed_password": hashed_password})

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    session_id = await create_session(redis, new_user.id)
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax", max_age=3600, path="/")

    return create_user_public(new_user)
    
'''
    new_user = User(
        username = user_data.username,
        email =  user_data.email,
        bio = user_data.bio,
        hashed_password = hashed_password
    )
'''
import os
import math
import asyncio
import uuid
import httpx

from typing import Annotated, List, Set
from fastapi import FastAPI, Depends, HTTPException, Header, Query, status, UploadFile, File
from fastapi.staticfiles import StaticFiles
from sqlmodel import select, func, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from models import BlogArticle, ArticleCreate, ArticleUpdate, ArticleImage
from database import init_db, get_session

app = FastAPI(title="Blog Service")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")

STATIC_DIR = "/app/static"
IMAGE_DIR = f"{STATIC_DIR}/images"
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def on_startup():
    await init_db()
    
@app.post("/api/blog/articles", response_model=BlogArticle, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate, 
    session: Annotated[AsyncSession, Depends(get_session)],
    x_user_id: Annotated[int, Header(alias="X-User-Id")],
):
    """새로운 블로그 게시글을 생성합니다."""
    new_article = BlogArticle.model_validate(article_data, update={"owner_id": x_user_id})
    session.add(new_article)
    await session.commit()
    await session.refresh(new_article)
    return new_article

@app.post("/api/blog/articles/{article_id}/upload-images", response_model=List[str])
async def upload_article_images(
    article_id: int,
    files: List[UploadFile],
    session: Annotated[AsyncSession, Depends(get_session)],
    x_user_id: Annotated[int, Header(alias="X-User-Id")],
):
    """게시글에 여러 이미지를 업로드하고 파일명을 DB에 저장합니다."""
    db_article = await session.get(BlogArticle, article_id)
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    if db_article.owner_id != x_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    saved_filenames = []
    for file in files:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(IMAGE_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        new_image = ArticleImage(image_filename=unique_filename, article_id=article_id)
        session.add(new_image)
        saved_filenames.append(unique_filename)
    
    await session.commit()
    return saved_filenames

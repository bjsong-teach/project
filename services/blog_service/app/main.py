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

class PaginatedResponse(SQLModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[dict] = []


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

@app.get("/api/blog/articles/{article_id}")
async def get_article(article_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    """특정 블로그 게시글의 상세 정보를 반환합니다."""
    # 1. 먼저 게시글 정보만 가져옵니다.
    article = await session.get(BlogArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    author_info = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{USER_SERVICE_URL}/api/users/{article.owner_id}")
            if resp.status_code == 200:
                author_info = resp.json()
    except Exception:
        author_info = {"username": "Unknown"}

    # 2. 별도의 쿼리를 실행하여 이 게시글에 속한 이미지 파일명들을 가져옵니다.
    image_query = select(ArticleImage.image_filename).where(ArticleImage.article_id == article_id)
    image_results = await session.exec(image_query)
    image_filenames = image_results.all()
    
    # 3. 가져온 파일명들로 전체 이미지 URL 목록을 생성합니다.
    image_urls = [f"/static/images/{filename}" for filename in image_filenames]
    
    return {"article": article, "author": author_info, "image_urls": image_urls}
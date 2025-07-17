from typing import Optional, List
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from sqlalchemy import Column, Integer

class Post(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  title: str = Field(index=True)
  content: str
  created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  owner_id: int
  views: int = Field(default=0)
  #views: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))

class PaginatedResponse(SQLModel):
  total: int
  page: int
  size: int
  pages: int
  items: List[dict] = []
  
class PostCreate(SQLModel):
  title: str
  content: str

class PostUpdate(SQLModel):
  title: Optional[str] = None
  content: Optional[str] = None    
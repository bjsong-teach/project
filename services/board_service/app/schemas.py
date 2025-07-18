from typing import List
from sqlmodel import SQLModel

class PaginatedResponse(SQLModel):
  total: int
  page: int
  size: int
  pages: int
  items: List[dict] = []
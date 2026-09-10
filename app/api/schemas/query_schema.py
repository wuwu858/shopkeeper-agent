# app/api/schemas/query_schema.py

from typing import List, Dict, Optional
from pydantic import BaseModel


class QuerySchema(BaseModel):
    query: str
    history: Optional[List[Dict]] = []  # ✅ 添加历史字段
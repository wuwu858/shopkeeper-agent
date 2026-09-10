from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ColumnInfo:
    id: str
    name: str
    type: str
    role: str
    examples: list[Any]
    description: Optional[str] = None
    alias: Optional[list[str]] = None
    table_id: Optional[str] = None
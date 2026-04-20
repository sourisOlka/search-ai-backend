from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_name: str
    mime_type: str
    size: int
    status: str | None
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str


class FilesPagination(BaseModel):
    files: list[FileItem]
    total_count: int
